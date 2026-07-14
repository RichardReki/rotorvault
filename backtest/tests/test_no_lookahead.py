"""The decisive rigor test: NO LOOK-AHEAD.

If the engine ever peeked at the future, perturbing a price at day k would change the
backtest's P&L on days BEFORE k. We prove it does not: changing the future leaves the
past byte-identical. Also proves the momentum factor at t is independent of t+1.
"""
import copy
import numpy as np

import _synth
from rotoredge.backtest import Engine
from rotoredge.signals import momentum_factor


def test_future_price_change_does_not_affect_the_past():
    snap, cfg = _synth.make()
    base = Engine(snap, cfg).run(start=cfg["backtest"]["start"]).daily_returns

    k = 300  # perturb one asset's close on day k (a future event for days < k)
    snap2 = copy.deepcopy(snap)
    snap2.close.iloc[k, snap2.close.columns.get_loc("AAA")] *= 1.5
    pert = Engine(snap2, cfg).run(start=cfg["backtest"]["start"]).daily_returns

    cut = snap.close.index[k]
    a = base[base.index < cut]
    b = pert.reindex(a.index)
    assert np.array_equal(a.values, b.values), "look-ahead detected: a future price changed past P&L"


def test_momentum_factor_is_causal():
    snap, cfg = _synth.make()
    f1 = momentum_factor(snap.close, 30, 2)
    snap2 = copy.deepcopy(snap)
    snap2.close.iloc[400, snap2.close.columns.get_loc("BBB")] *= 2.0
    f2 = momentum_factor(snap2.close, 30, 2)
    # factor on/before day 400-? must be unchanged for the perturbed name before day 400
    pre = f1["BBB"].iloc[:400].dropna()
    assert np.allclose(pre.values, f2["BBB"].iloc[:400].reindex(pre.index).values, equal_nan=True)


if __name__ == "__main__":
    test_future_price_change_does_not_affect_the_past()
    test_momentum_factor_is_causal()
    print("test_no_lookahead: OK")
