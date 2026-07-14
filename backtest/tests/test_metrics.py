"""Metric sanity: no divide-by-zero, drawdown/Sharpe behave as expected."""
import numpy as np
import pandas as pd

from rotoredge import metrics as M


def test_zero_vol_sharpe_is_safe():
    r = pd.Series([0.0] * 50)
    assert M.sharpe(r) == 0.0 and M.sortino(r) == 0.0  # no exception, no inf


def test_monotonic_equity_has_no_drawdown():
    r = pd.Series([0.01] * 100)
    eq = M.to_equity(r)
    assert M.max_drawdown(eq) == 0.0


def test_drawdown_is_negative_after_a_fall():
    r = pd.Series([0.1, 0.1, -0.5, 0.0])
    assert M.max_drawdown(M.to_equity(r)) < 0


def test_deflated_sharpe_penalises_more_trials():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.02, 800))
    few = M.deflated_sharpe_ratio(r, [0.3, 0.4, 0.5], 3)["dsr"]
    many = M.deflated_sharpe_ratio(r, [0.3, 0.4, 0.5] * 20, 60)["dsr"]
    assert many <= few  # more trials -> higher benchmark -> lower DSR


if __name__ == "__main__":
    test_zero_vol_sharpe_is_safe(); test_monotonic_equity_has_no_drawdown()
    test_drawdown_is_negative_after_a_fall(); test_deflated_sharpe_penalises_more_trials()
    print("test_metrics: OK")
