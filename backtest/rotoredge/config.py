"""Config loading + validation. The single frozen config lives at configs/rotorvault.yaml."""
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = {
    "seed": 7,
    "snapshot_dir": "data/snapshot",
    "regime_asset": "BTC",
    "universe_n": 3,
    "hold_symbol": "XRP",
    "min_history_days": 130,
    "rebalance_days": 21,
    "deadband": 2.0,
    "long_only_positive": False,
    "vol_window": 30,
    "momentum": {"lookback": 90, "skip": 5},
    "weighting": "equal",
    "top_k": 1,
    "regime": {"enabled": True, "ma": 100, "risk_off_to": "cash"},
    "vol_target": {"enabled": True, "target_vol": 0.35, "max_leverage": 1.0},
    "fng": {"floor": 0.5, "greed_lo": 55, "greed_hi": 90, "shift": 1},
    "costs": {"fee_bps": 20.0, "buffer_bps": 10.0, "gas_usd": 0.05,
              "pool_depth_usd": 1_500_000.0, "notional_usd": 100_000.0},
    "walkforward": {"train_days": 730, "test_days": 180,
                    "param_grid": {"lookback": [60, 90, 120], "top_k": [1]}},
    "cost_sensitivity": [0.0, 1.0, 2.0],
    "exclude": [],
}


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path = "configs/rotorvault.yaml") -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    user = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    cfg = _deep_merge(DEFAULTS, user or {})
    cfg["_root"] = str(ROOT)
    return cfg
