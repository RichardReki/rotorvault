"""Survivorship-bias-free, POINT-IN-TIME universe construction.

At each date we know ONLY what existed up to that date. A token that delisted before
date t is absent (NaN) -> correctly excluded. A token that listed later only appears
from its listing -> no look-ahead. We screen by trailing dollar-volume (liquidity),
which is the correct screen for a rotation you could actually execute, and needs no
historical market-cap reconstruction.
"""
from __future__ import annotations

import pandas as pd


def trailing_dollar_volume(dollar_volume: pd.DataFrame, window: int) -> pd.DataFrame:
    """Causal trailing mean $-volume as of each date (uses data <= t only)."""
    return dollar_volume.rolling(window, min_periods=max(5, window // 3)).mean()


def eligibility(close: pd.DataFrame, min_history_days: int) -> pd.DataFrame:
    """Boolean (date x symbol): valid price at t AND >= min_history_days of prior data."""
    has_price = close.notna()
    prior_obs = has_price.cumsum()  # number of valid observations up to and incl. t
    return has_price & (prior_obs >= min_history_days)


def pit_universe(
    date: pd.Timestamp,
    tdv: pd.DataFrame,
    elig: pd.DataFrame,
    universe_n: int,
    exclude: list[str] | None = None,
) -> list[str]:
    """Top-N eligible symbols by trailing $-volume as of `date` (point-in-time)."""
    if date not in tdv.index:
        return []
    row_v = tdv.loc[date]
    row_e = elig.loc[date]
    cand = row_v[row_e & row_v.notna()]
    if exclude:
        cand = cand.drop(labels=[s for s in exclude if s in cand.index], errors="ignore")
    cand = cand.sort_values(ascending=False)
    return list(cand.index[:universe_n])
