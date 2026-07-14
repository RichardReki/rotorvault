"""Config loading + validation. The single frozen config lives at configs/submission.yaml."""
from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = {
    "seed": 7,
    "snapshot_dir": "data/snapshot",
    "regime_asset": "BTC",
    "universe_n": 15,          # top-N by trailing $-volume forms the point-in-time universe
    "min_history_days": 120,   # a token needs this much prior history to be eligible
    "rebalance_days": 21,      # composition refresh cadence (~monthly)
    "deadband": 2.0,           # high -> monthly only. A reactive daily kill-switch whipsawed OOS (see docs).
    "long_only_positive": False,  # hold the relatively strongest top-K (not only positive momentum)
    "vol_window": 30,          # for trailing $-volume screen and realized vol
    "momentum": {"lookback": 90, "skip": 5},
    "weighting": "equal",      # "equal" | "inverse_vol"
    "top_k": 5,
    "regime": {"enabled": True, "ma": 100, "risk_off_to": "cash"},   # "cash" | regime_asset
    "vol_target": {"enabled": True, "target_vol": 0.35, "max_leverage": 1.0},  # portfolio vol targeting
    "fng": {"floor": 0.5, "greed_lo": 55, "greed_hi": 90, "shift": 1},
    "costs": {
        "fee_bps": 25.0,          # PancakeSwap V3 volatile tier 0.25%
        "buffer_bps": 10.0,       # adverse-fill / MEV buffer
        "gas_usd": 0.20,          # per swap on BSC
        "pool_depth_usd": 3_000_000.0,  # per-name liquidity for AMM impact proxy
        "notional_usd": 100_000.0,      # assumed AUM (scales gas + impact)
    },
    "walkforward": {
        "train_days": 730,
        "test_days": 180,
        "param_grid": {"lookback": [60, 90, 120], "top_k": [3, 5, 8]},
    },
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


def load_config(path: str | Path = "configs/submission.yaml") -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    user = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    cfg = _deep_merge(DEFAULTS, user or {})
    cfg["_root"] = str(ROOT)
    return cfg
