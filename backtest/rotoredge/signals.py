"""Signals — ALL causal (computed from closed bars only).

- Vol-adjusted cross-sectional momentum (the ranking factor)        [BACKTESTED]
- BTC-vs-MA master regime switch                                    [BACKTESTED]
- Fear & Greed exposure scalar                                      [BACKTESTED]
- Realized vol (for optional inverse-vol weighting)

The engine always references these at the day BEFORE a rebalance, so a decision
uses only information available at that prior close. No look-ahead here or there.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def log_returns(close: pd.DataFrame) -> pd.DataFrame:
    return np.log(close).diff()


def momentum_factor(close: pd.DataFrame, lookback: int, skip: int) -> pd.DataFrame:
    """Vol-adjusted trailing momentum, skipping the most recent `skip` days.

    factor_t = (log-return over the L-day window ending `skip` days ago)
               / (daily vol over that window * sqrt(L))
    i.e. a per-window Sharpe. Cross-sectional ranking is the only use, so the scale
    is irrelevant; the form keeps it comparable across names with different vol.
    """
    logp = np.log(close)
    lr = logp.diff()
    mom = logp.shift(skip) - logp.shift(skip + lookback)
    dvol = lr.shift(skip).rolling(lookback, min_periods=lookback).std()
    factor = mom / (dvol * np.sqrt(lookback))
    return factor.replace([np.inf, -np.inf], np.nan)


def regime_on(close: pd.DataFrame, regime_asset: str, ma: int) -> pd.Series:
    """True when the regime asset (BTC) closes above its `ma`-day moving average."""
    px = close[regime_asset]
    sma = px.rolling(ma, min_periods=ma).mean()
    on = px > sma
    on[sma.isna()] = False  # undefined warm-up -> treat as risk-off (conservative)
    return on


def realized_vol(close: pd.DataFrame, window: int) -> pd.DataFrame:
    return log_returns(close).rolling(window, min_periods=max(5, window // 2)).std()


def fng_scalar(fng: pd.Series, calendar: pd.DatetimeIndex, cfg: dict) -> pd.Series:
    """Exposure multiplier in [floor, 1]: full in fear/neutral, trimmed in extreme greed.

    scalar = 1                              for fng <= greed_lo
           = linear down to `floor`         for greed_lo < fng < greed_hi
           = floor                          for fng >= greed_hi
    Aligned to the price calendar, forward-filled, and shifted so a decision uses a
    PRIOR reading (no same-bar leakage).
    """
    floor = float(cfg["fng"]["floor"])
    lo, hi = float(cfg["fng"]["greed_lo"]), float(cfg["fng"]["greed_hi"])
    shift = int(cfg["fng"].get("shift", 1))

    f = fng.reindex(calendar.union(fng.index)).sort_index().ffill().reindex(calendar)
    frac = ((f - lo) / (hi - lo)).clip(0.0, 1.0)
    scalar = 1.0 - frac * (1.0 - floor)
    scalar = scalar.clip(floor, 1.0).fillna(1.0)
    return scalar.shift(shift).fillna(1.0)
