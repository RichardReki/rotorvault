"""Baselines are XRP-centric: HODL BTC/ETH/XRP + a no-overlay XRP ablation."""
from rotoredge import data
from rotoredge.config import load_config
from rotoredge.baselines import build_baselines


def test_baselines_are_xrp_centric():
    cfg = load_config("configs/rotorvault.yaml")
    snap = data.load_snapshot(cfg["snapshot_dir"])
    b = build_baselines(snap, cfg, start=cfg["backtest"]["start"], end=None)
    assert "HODL XRP" in b and "HODL BTC" in b and "HODL ETH" in b
    assert "XRP full-exposure (no overlay)" in b
    assert "EqualWeight Universe" not in b
    for name, s in b.items():
        assert len(s) > 0            # every baseline is a non-empty daily-return series
