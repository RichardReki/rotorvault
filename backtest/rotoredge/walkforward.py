"""Anchored walk-forward validation.

For each fold: optimise {lookback, top_k} on an expanding in-sample window (anchored
at the global start), FREEZE the best, evaluate the immediately-following out-of-sample
block, roll forward by the test length. The stitched OOS curve is the headline metric;
in-sample is reported only for the IS-vs-OOS degradation comparison.

Each OOS block starts from cash (independent evaluation) — a conservative choice that
pays an extra entry cost at each boundary rather than inflating returns.
"""
from __future__ import annotations

import itertools
import pandas as pd

from .backtest import Engine
from . import metrics as M


def param_grid(cfg: dict) -> list[dict]:
    g = cfg["walkforward"]["param_grid"]
    combos = []
    for lb, tk in itertools.product(g["lookback"], g["top_k"]):
        combos.append({
            "lookback": lb,
            "skip": cfg["momentum"]["skip"],
            "top_k": tk,
            "universe_n": cfg["universe_n"],
            "weighting": cfg["weighting"],
        })
    return combos


def walk_forward(eng: Engine, cfg: dict) -> dict:
    grid = param_grid(cfg)
    start = pd.Timestamp(cfg["backtest"]["start"])
    end = eng.idx[-1] if cfg["backtest"]["end"] in (None, "null") else pd.Timestamp(cfg["backtest"]["end"])
    train_days = int(cfg["walkforward"]["train_days"])
    test_days = int(cfg["walkforward"]["test_days"])

    folds = []
    oos_daily, oos_period = [], []
    oos_weights: dict = {}

    test_start = start + pd.Timedelta(days=train_days)
    while test_start < end:
        test_end = min(test_start + pd.Timedelta(days=test_days), end)
        # 1) optimise on the anchored in-sample window [start, test_start)
        best, best_sr = None, -1e9
        for p in grid:
            tr = eng.run(p, start=start, end=test_start)
            sr = M.sharpe(tr.daily_returns)
            if sr > best_sr:
                best_sr, best = sr, p
        # 2) freeze, evaluate OOS [test_start, test_end)
        te = eng.run(best, start=test_start, end=test_end)
        oos_daily.append(te.daily_returns)
        if len(te.period_returns):
            oos_period.append(te.period_returns)
        oos_weights.update(te.weights)
        folds.append({
            "train": [str(start.date()), str(test_start.date())],
            "test": [str(test_start.date()), str(test_end.date())],
            "chosen_params": {"lookback": best["lookback"], "top_k": best["top_k"]},
            "train_sharpe": round(best_sr, 4),
            "oos_sharpe": round(M.sharpe(te.daily_returns), 4),
            "oos_return": round(float((1 + te.daily_returns).prod() - 1), 4),
        })
        test_start = test_end

    stitched = pd.concat(oos_daily).sort_index() if oos_daily else pd.Series(dtype=float)
    stitched = stitched[~stitched.index.duplicated(keep="first")]
    stitched_period = pd.concat(oos_period).sort_index() if oos_period else pd.Series(dtype=float)

    # DSR trials: each grid config's annualised Sharpe over the FULL sample.
    trial_sharpes = [M.sharpe(eng.run(p, start=start, end=end).daily_returns) for p in grid]

    return {
        "oos_daily": stitched,
        "oos_period": stitched_period,
        "oos_weights": oos_weights,
        "folds": folds,
        "n_trials": len(grid),
        "trial_sharpes": trial_sharpes,
    }


def stitch_oos(eng: Engine, cfg: dict, folds: list[dict], cost_mult: float) -> pd.Series:
    """Re-evaluate the SAME frozen per-fold params at a given cost multiplier (for the
    cost-sensitivity table) — no re-selection, so it isolates the cost effect."""
    parts = []
    for f in folds:
        p = {
            "lookback": f["chosen_params"]["lookback"],
            "skip": cfg["momentum"]["skip"],
            "top_k": f["chosen_params"]["top_k"],
            "universe_n": cfg["universe_n"],
            "weighting": cfg["weighting"],
        }
        parts.append(eng.run(p, start=f["test"][0], end=f["test"][1], cost_mult=cost_mult).daily_returns)
    s = pd.concat(parts).sort_index() if parts else pd.Series(dtype=float)
    return s[~s.index.duplicated(keep="first")]
