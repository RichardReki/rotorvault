"""Survivorship handling: a delisting (price -> NaN) is liquidated to cash gracefully;
the run stays finite (no NaN/inf leaking into P&L). This is what lets dead coins like
FTT/WAVES stay in the historical universe without breaking the backtest."""
import copy
import numpy as np

import _synth
from rotoredge.backtest import Engine


def test_delisting_is_handled_and_returns_stay_finite():
    snap, cfg = _synth.make()
    snap2 = copy.deepcopy(snap)
    # 'AAA' delists from day 350 onward (price becomes NaN, as on data.binance.vision)
    snap2.close.iloc[350:, snap2.close.columns.get_loc("AAA")] = np.nan
    snap2.open.iloc[350:, snap2.open.columns.get_loc("AAA")] = np.nan
    r = Engine(snap2, cfg).run(start=cfg["backtest"]["start"]).daily_returns
    assert np.isfinite(r.values).all(), "delisting leaked NaN/inf into P&L"
    assert len(r) > 100


if __name__ == "__main__":
    test_delisting_is_handled_and_returns_stay_finite()
    print("test_survivorship: OK")
