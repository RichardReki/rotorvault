import json
from rotoredge.spec import build_vault_spec, SIGNAL_LABELS

def test_labels_mark_venue_apys_live_only():
    live = [s for s in SIGNAL_LABELS if s["status"] == "LIVE-ONLY"]
    assert any("apy" in s["signal"].lower() or "venue" in s["signal"].lower() for s in live)
    assert any("ftso" in s["source"].lower() for s in SIGNAL_LABELS)

def test_build_vault_spec_shape():
    spec = build_vault_spec(
        as_of="2026-05-31", cfg={"regime_asset": "BTC", "regime": {"ma": 100},
            "momentum": {"lookback": 90, "skip": 5}, "vol_target": {"target_vol": 0.35, "max_leverage": 1.0},
            "fng": {"floor": 0.5, "greed_lo": 55, "greed_hi": 90}, "rebalance_days": 21,
            "costs": {}, "hold_symbol": "XRP"},
        exposure=0.6, regime_on=True,
        vault_overlay={"fxrp_exposure": 0.6, "venue_allocation": {"firelight": 0.3, "upshift": 0.3, "idle": 0.4}},
        oos_metrics={"sharpe": 0.4, "max_drawdown": -0.3}, snapshot_sha256="deadbeef")
    assert spec["strategy"] == "RotorVault"
    assert spec["held_asset"] == "FXRP (XRP)"
    assert spec["vault_overlay"]["venue_allocation"]["idle"] == 0.4
    assert spec["vault_overlay"]["status"] == "LIVE-ONLY"
    json.dumps(spec)  # must be serializable
