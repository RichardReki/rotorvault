"""Baselines & ablations — all on the SAME period and SAME cost model as the strategy.

- BTC / BNB HODL: did we beat just holding the majors?
- EqualWeight-Universe: own the whole point-in-time universe (no momentum) -> isolates
  the value of cross-sectional SELECTION.
- Momentum-NoRiskOverlay: pure cross-sectional momentum, full exposure (no regime,
  no vol-target, no F&G) -> isolates the value of the RISK OVERLAY.
Ablations reuse the audited causal engine via config toggles (no duplicate logic).
"""
from __future__ import annotations

import copy
import pandas as pd

from .backtest import Engine


def hodl_returns(snap, symbol: str, start, end, fee_bps: float) -> pd.Series:
    """Buy-and-hold one asset (close-to-close), entry cost charged on day 1."""
    px = snap.close[symbol]
    end_ts = px.index.max() if end is None else pd.Timestamp(end)
    px = px[(px.index >= pd.Timestamp(start)) & (px.index <= end_ts)].dropna()
    r = px.pct_change().fillna(0.0)
    if len(r):
        r.iloc[0] -= fee_bps / 1e4
    r.name = f"HODL_{symbol}"
    return r


def _cfg_no_overlay(cfg: dict, top_k: int | None = None, weighting: str | None = None) -> dict:
    c = copy.deepcopy(cfg)
    c["regime"]["enabled"] = False
    c["vol_target"]["enabled"] = False
    c["fng"]["floor"] = 1.0  # disables the F&G scalar (scalar == 1 always)
    if top_k is not None:
        c["top_k"] = top_k
    if weighting is not None:
        c["weighting"] = weighting
    return c


def build_baselines(snap, cfg: dict, start, end, cost_mult: float = 1.0) -> dict[str, pd.Series]:
    """Return {name: daily_returns} for XRP-centric baselines/ablations, aligned to the period."""
    out: dict[str, pd.Series] = {}
    fee = cfg["costs"]["fee_bps"] + cfg["costs"]["buffer_bps"]
    for sym in ("BTC", "ETH", "XRP"):
        if sym in snap.symbols:
            out[f"HODL {sym}"] = hodl_returns(snap, sym, start, end, fee)
    # Same held book (XRP) but NO risk overlay -> isolates the value of the OVERLAY.
    mo = _cfg_no_overlay(cfg)
    out["XRP full-exposure (no overlay)"] = Engine(snap, mo).run(start=start, end=end, cost_mult=cost_mult).daily_returns
    return out
