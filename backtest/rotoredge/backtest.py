"""Causal cross-sectional rotation engine.

Design: COMPOSITION is chosen monthly (which top-K names + relative weights), but RISK
is managed DAILY (regime kill-switch + vol-target + F&G scale gross exposure every day,
with a turnover deadband so we don't churn on small wiggles). This mirrors how a desk
actually runs a book: pick the basket monthly, but cut risk the day the regime breaks.

No look-ahead (auditable):
  - Every decision on execution day d uses ONLY information through the prior close (d-1):
    momentum factor, regime, F&G, the point-in-time universe, and the book's realized vol.
  - Execution is at day d's OPEN with the full BSC cost model on turnover.
  - Per-asset value is tracked so weights drift between trades. Each day splits into an
    overnight leg (close[d-1]->open[d], old book) and an intraday leg (open[d]->close[d],
    post-trade book). Missing/delisted prices force liquidation to cash at the last value
    (we eat collapses like FTT/WAVES; no survivorship escape).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import signals, universe
from .costs import compute_cost


@dataclass
class Result:
    daily_returns: pd.Series
    equity: pd.Series
    period_returns: pd.Series
    weights: dict                      # composition-rebalance date -> {symbol: target weight}
    turnover: pd.Series
    costs: pd.Series
    regime_on: pd.Series
    exposure: pd.Series
    meta: dict = field(default_factory=dict)


class Engine:
    def __init__(self, snap, cfg: dict):
        self.snap = snap
        self.cfg = cfg
        self.symbols = list(snap.close.columns)
        self.idx = snap.close.index
        self.close = snap.close.to_numpy(float)
        self.open = snap.open.to_numpy(float)
        self.tdv = universe.trailing_dollar_volume(snap.dollar_volume, cfg["vol_window"]).to_numpy(float)
        self.elig = universe.eligibility(snap.close, cfg["min_history_days"]).to_numpy(bool)
        self.regime = signals.regime_on(snap.close, cfg["regime_asset"], cfg["regime"]["ma"]).to_numpy(bool)
        self.fng = signals.fng_scalar(snap.fng, self.idx, cfg).to_numpy(float)
        self.rvol = signals.realized_vol(snap.close, cfg["vol_window"]).to_numpy(float)
        self._factor_cache: dict[tuple, np.ndarray] = {}

    def _factor(self, lookback: int, skip: int) -> np.ndarray:
        key = (lookback, skip)
        if key not in self._factor_cache:
            self._factor_cache[key] = signals.momentum_factor(self.snap.close, lookback, skip).to_numpy(float)
        return self._factor_cache[key]

    def _composition(self, j_dec: int, params: dict, factor: np.ndarray) -> np.ndarray:
        """Relative weights (sum=1) of the selected long-only momentum names at j_dec."""
        n = len(self.symbols)
        w = np.zeros(n)
        hold = self.cfg.get("hold_symbol")
        if hold:
            if hold in self.symbols:
                s = self.symbols.index(hold)
                if self.elig[j_dec, s] and not np.isnan(self.close[j_dec, s]):
                    w[s] = 1.0
            return w
        v, e = self.tdv[j_dec], self.elig[j_dec]
        valid = e & ~np.isnan(v)
        if not valid.any():
            return w
        cand = np.where(valid)[0]
        cand = cand[np.argsort(-v[cand])][: params["universe_n"]]      # point-in-time universe
        f = factor[j_dec]
        if self.cfg.get("long_only_positive", True):
            cand = [c for c in cand if not np.isnan(f[c]) and f[c] > 0]  # don't hold downtrending names
        else:
            cand = [c for c in cand if not np.isnan(f[c])]
        if not cand:
            return w
        cand = sorted(cand, key=lambda c: -f[c])[: params["top_k"]]
        if params["weighting"] == "inverse_vol":
            iv = np.array([1.0 / self.rvol[j_dec, c] if (self.rvol[j_dec, c] and not np.isnan(self.rvol[j_dec, c])) else 0.0 for c in cand])
            ww = iv / iv.sum() if iv.sum() > 0 else np.ones(len(cand)) / len(cand)
        else:
            ww = np.ones(len(cand)) / len(cand)
        for c, x in zip(cand, ww):
            w[c] = x
        return w

    def _gross(self, j_dec: int, comp: np.ndarray) -> float:
        """Daily target gross exposure in [0, max_leverage] from regime + vol-target + F&G."""
        if self.cfg["regime"].get("enabled", True) and not self.regime[j_dec]:
            return 0.0
        exposure = float(self.fng[j_dec]) if not np.isnan(self.fng[j_dec]) else 1.0
        vt = self.cfg.get("vol_target", {})
        maxlev = float(vt.get("max_leverage", 1.0))
        if vt.get("enabled", False):
            names = np.nonzero(comp)[0]
            w0 = j_dec - self.cfg["vol_window"]
            vol_scalar = maxlev
            if w0 >= 1 and names.size > 0:
                sub = self.close[w0 : j_dec + 1][:, names]
                with np.errstate(divide="ignore", invalid="ignore"):
                    lr = np.diff(np.log(sub), axis=0)
                port = np.nansum(lr * comp[names], axis=1) / max(comp[names].sum(), 1e-9)
                bv = float(np.nanstd(port, ddof=1) * np.sqrt(365)) if port.size > 2 else 0.0
                if bv > 0 and not np.isnan(bv):
                    vol_scalar = min(maxlev, float(vt["target_vol"]) / bv)
            exposure *= vol_scalar
        return float(min(maxlev, max(0.0, exposure)))

    def run(self, params: dict | None = None, start=None, end=None, cost_mult: float = 1.0) -> Result:
        cfg = self.cfg
        p = {"lookback": cfg["momentum"]["lookback"], "skip": cfg["momentum"]["skip"],
             "top_k": cfg["top_k"], "universe_n": cfg["universe_n"], "weighting": cfg["weighting"]}
        if params:
            p.update(params)
        factor = self._factor(p["lookback"], p["skip"])
        reb_days = int(cfg["rebalance_days"])
        deadband = float(cfg.get("deadband", 0.08))

        idx = self.idx
        start_pos = 1 if start is None else max(1, idx.searchsorted(pd.Timestamp(start)))
        end_pos = len(idx) - 1 if end is None else min(len(idx) - 1, idx.searchsorted(pd.Timestamp(end)))
        reb_positions = set(range(start_pos, end_pos + 1, reb_days))

        n = len(self.symbols)
        holdings = np.zeros(n)
        cash = 1.0
        V_prev = 1.0
        comp = np.zeros(n)  # current monthly composition (sum<=1)

        dates, rets, exposures, regimes = [], [], [], []
        weights_log, turn_log, cost_log = {}, {}, {}
        period_dates, period_V = [], []

        for j in range(start_pos, end_pos + 1):
            d = idx[j]
            is_reb = j in reb_positions

            # 1) overnight: close[j-1] -> open[j] on the OLD book
            for s in np.nonzero(holdings)[0]:
                c0, o1 = self.close[j - 1, s], self.open[j, s]
                if np.isnan(c0) or np.isnan(o1) or c0 <= 0:
                    cash += holdings[s]; holdings[s] = 0.0
                else:
                    holdings[s] *= o1 / c0
            V_open = cash + holdings.sum()

            # 2) decide target (info <= j-1). Composition refreshed monthly; gross daily.
            if is_reb:
                new_comp = self._composition(j - 1, p, factor)
                if new_comp.sum() > 0:
                    comp = new_comp
            gross = self._gross(j - 1, comp)
            target = comp * gross
            # only buy names tradable at execution; freed weight -> cash (conservative)
            for s in np.nonzero(target)[0]:
                if np.isnan(self.open[j, s]) or np.isnan(self.close[j, s]):
                    target[s] = 0.0

            # 3) trade at open[j] if monthly rebalance OR turnover breaches the deadband
            cur_w = holdings / V_open if V_open > 0 else holdings * 0.0
            turnover = float(np.abs(target - cur_w).sum())
            if is_reb or turnover > deadband:
                cb = compute_cost(cur_w, target, cfg, cost_mult)
                V_after = V_open * (1.0 - cb["total"])
                holdings = target * V_after
                cash = V_after - holdings.sum()
                if is_reb:
                    weights_log[d] = {self.symbols[s]: float(target[s]) for s in np.nonzero(target)[0]}
                    turn_log[d] = cb["turnover"]
                    cost_log[d] = cb["total"]

            # 4) intraday: open[j] -> close[j] on the (possibly new) book
            for s in np.nonzero(holdings)[0]:
                o1, c1 = self.open[j, s], self.close[j, s]
                if np.isnan(o1) or np.isnan(c1) or o1 <= 0:
                    cash += holdings[s]; holdings[s] = 0.0
                else:
                    holdings[s] *= c1 / o1

            if is_reb:
                period_dates.append(d); period_V.append(cash + holdings.sum())

            V_d = cash + holdings.sum()
            dates.append(d)
            rets.append(V_d / V_prev - 1.0 if V_prev > 0 else 0.0)
            exposures.append(float(holdings.sum() / V_d) if V_d > 0 else 0.0)
            regimes.append(bool(self.regime[j - 1]))
            V_prev = V_d

        daily = pd.Series(rets, index=pd.DatetimeIndex(dates), name="strategy")
        equity = (1.0 + daily.fillna(0.0)).cumprod()
        pv = pd.Series(period_V, index=pd.DatetimeIndex(period_dates))
        period_returns = (pv / pv.shift(1) - 1.0).dropna()
        return Result(
            daily_returns=daily, equity=equity, period_returns=period_returns,
            weights=weights_log, turnover=pd.Series(turn_log), costs=pd.Series(cost_log),
            regime_on=pd.Series(regimes, index=pd.DatetimeIndex(dates)),
            exposure=pd.Series(exposures, index=pd.DatetimeIndex(dates)),
            meta={"params": p, "cost_mult": cost_mult, "start": str(daily.index[0].date()), "end": str(daily.index[-1].date())},
        )
