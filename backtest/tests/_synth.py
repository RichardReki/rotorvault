"""Deterministic synthetic snapshot for tests (no network)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rotoredge.config import load_config
from rotoredge.data import Snapshot

SYMS = ["BTC", "ETH", "BNB", "AAA", "BBB", "CCC", "DDD", "EEE"]


def make(n_days: int = 520, seed: int = 1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n_days, freq="D")
    close = {}
    for i, s in enumerate(SYMS):
        drift = 0.0005 + 0.0003 * (i % 3)
        vol = 0.03 + 0.01 * (i % 4)
        steps = rng.normal(drift, vol, n_days)
        close[s] = 100.0 * np.exp(np.cumsum(steps))
    close_df = pd.DataFrame(close, index=dates)
    open_df = close_df.shift(1).fillna(close_df.iloc[0]) * (1 + rng.normal(0, 0.002, close_df.shape))
    qvol_df = pd.DataFrame(rng.uniform(1e6, 1e8, close_df.shape), index=dates, columns=SYMS)
    fng = pd.Series(rng.integers(10, 90, n_days), index=dates)
    snap = Snapshot(open=open_df, close=close_df, dollar_volume=qvol_df, fng=fng, manifest={})

    cfg = load_config()
    cfg.update({
        "min_history_days": 60, "vol_window": 20, "universe_n": 6, "top_k": 3,
        "rebalance_days": 20, "deadband": 2.0, "weighting": "equal", "long_only_positive": False,
        "backtest": {"start": str(dates[80].date()), "end": None},
    })
    cfg["momentum"] = {"lookback": 30, "skip": 2}
    cfg["regime"] = {"enabled": True, "ma": 40, "risk_off_to": "cash"}
    cfg["vol_target"] = {"enabled": True, "target_vol": 0.5, "max_leverage": 1.0}
    cfg["fng"] = {"floor": 0.5, "greed_lo": 55, "greed_hi": 90, "shift": 1}
    return snap, cfg
