"""hold_symbol forces the held book to a single name, bypassing momentum ranking."""
import pytest
from tests._synth import make
from rotoredge.backtest import Engine


def _params(cfg):
    return {"universe_n": cfg["universe_n"], "top_k": cfg["top_k"],
            "weighting": cfg["weighting"], "lookback": cfg["momentum"]["lookback"],
            "skip": cfg["momentum"]["skip"]}


def test_hold_symbol_forces_single_name():
    snap, cfg = make(n_days=200, seed=1)
    cfg["hold_symbol"] = "ETH"          # ETH exists in the synthetic universe
    eng = Engine(snap, cfg)
    p = _params(cfg)
    w = eng._composition(120, p, eng._factor(p["lookback"], p["skip"]))
    eth = eng.symbols.index("ETH")
    assert w[eth] == 1.0
    assert (w > 0).sum() == 1           # ONLY ETH held
    assert w.sum() == pytest.approx(1.0)


def test_hold_symbol_none_uses_ranking():
    snap, cfg = make(n_days=200, seed=1)   # make() must set hold_symbol=None
    assert cfg["hold_symbol"] is None
    eng = Engine(snap, cfg)
    p = _params(cfg)
    w = eng._composition(120, p, eng._factor(p["lookback"], p["skip"]))
    assert (w > 0).sum() >= 1              # ranking path still selects names
    assert w.sum() == pytest.approx(1.0)


def test_hold_symbol_absent_symbol_returns_empty():
    snap, cfg = make(n_days=200, seed=1)
    cfg["hold_symbol"] = "NOTREAL"      # not in the universe
    eng = Engine(snap, cfg)
    p = _params(cfg)
    w = eng._composition(120, p, eng._factor(p["lookback"], p["skip"]))
    assert w.sum() == 0.0
