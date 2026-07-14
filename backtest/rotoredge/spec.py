"""StrategySpec emitter.

A machine-readable strategy specification (NOT a live order). Every signal is labelled
BACKTESTED (reproducible on keyless data) or LIVE-ONLY (FTSOv2 prices + venue APYs, with
no free history). `build_vault_spec` is the RotorVault emitter; `build_spec` is the legacy
RotorEdge emitter retained only for the run_backtest dashboard preview. Carries full
backtest provenance so the numbers are independently verifiable.
"""
from __future__ import annotations

import pandas as pd

from . import universe

SIGNAL_LABELS = [
    {"signal": "btc_100d_ma_regime", "role": "master risk-on/off (trend) gate", "status": "BACKTESTED", "source": "Binance OHLCV proxy for FTSOv2 BTC/USD"},
    {"signal": "vol_adjusted_momentum", "role": "surfaced strength signal", "status": "BACKTESTED", "source": "Binance OHLCV proxy for FTSOv2 XRP/BTC/ETH"},
    {"signal": "portfolio_vol_target", "role": "FXRP exposure scalar", "status": "BACKTESTED", "source": "derived from OHLCV"},
    {"signal": "fear_greed", "role": "FXRP exposure scalar", "status": "BACKTESTED", "source": "alternative.me (history to 2018)"},
    {"signal": "ftsov2_spot_price", "role": "live NAV + on-chain regime sampling", "status": "LIVE-ONLY", "source": "FTSOv2 getFeedById (Coston2)"},
    {"signal": "venue_apy (firelight, upshift)", "role": "yield tilt across venues", "status": "LIVE-ONLY", "source": "Upshift API via FDC Web2Json; Firelight on-chain exchange-rate derivation"},
]


def build_spec(snap, cfg: dict, run, oos_metrics: dict, snapshot_sha256: str, live_overlay: dict | None = None) -> dict:
    last_date = max(run.weights) if run.weights else snap.close.index[-1]
    tw = run.weights.get(last_date, {})
    gross = float(sum(tw.values()))

    # recompute the point-in-time universe members at the last decision date
    tdv = universe.trailing_dollar_volume(snap.dollar_volume, cfg["vol_window"])
    elig = universe.eligibility(snap.close, cfg["min_history_days"])
    dpos = snap.close.index.get_loc(last_date)
    dec_date = snap.close.index[max(0, dpos - 1)]
    members = universe.pit_universe(dec_date, tdv, elig, cfg["universe_n"], cfg.get("exclude"))

    return {
        "schema_version": "rotoredge.strategy_spec.v1",
        "strategy": "RotorEdge",
        "as_of": str(pd.Timestamp(last_date).date()),
        "objective": "Survivorship-bias-free cross-sectional momentum rotation across BNB-eligible tokens, vol-targeted, regime-gated. Emits a backtestable allocation; does NOT place trades.",
        "universe": {
            "method": "point-in-time top-N by trailing 30d dollar-volume (survivorship-bias-free; includes since-delisted tokens up to delisting)",
            "n": cfg["universe_n"],
            "members": members,
        },
        "rebalance": {"frequency_days": cfg["rebalance_days"]},
        "ranking_factor": {
            "name": "vol_adjusted_momentum",
            "lookback_days": cfg["momentum"]["lookback"],
            "skip_days": cfg["momentum"]["skip"],
            "vol_adjusted": True,
        },
        "selection": {"top_k": cfg["top_k"], "weighting": cfg["weighting"]},
        "regime": {
            "state": "risk_on" if gross > 0 else "risk_off",
            "gate": {"source": f"BTC close vs {cfg['regime']['ma']}d MA", "live_only": False},
        },
        "exposure": {
            "gross": round(gross, 4),
            "drivers": {
                "vol_target": cfg["vol_target"],
                "fear_greed_scalar": {"floor": cfg["fng"]["floor"], "greed_lo": cfg["fng"]["greed_lo"], "greed_hi": cfg["fng"]["greed_hi"]},
            },
        },
        "target_weights": {k: round(v, 4) for k, v in sorted(tw.items(), key=lambda kv: -kv[1])},
        "risk_limits": {"long_only": True, "no_leverage": True, "max_leverage": cfg["vol_target"]["max_leverage"]},
        "cost_model": cfg["costs"],
        "signal_labels": SIGNAL_LABELS,
        "backtest_provenance": {
            "keyless_sources": [
                "https://data.binance.vision/data/spot/monthly/klines/<SYM>USDT/1d/",
                "https://api.alternative.me/fng/?limit=0&format=json",
            ],
            "universe_pool_size": len(snap.symbols),
            "date_range": [str(snap.close.index.min().date()), str(snap.close.index.max().date())],
            "snapshot_sha256": snapshot_sha256,
            "out_of_sample": oos_metrics,
        },
        "live_overlay": live_overlay or {
            "note": "Populated at runtime by skills/rotoredge/SKILL.md via the CoinMarketCap Agent Hub MCP. NOT part of the backtest.",
            "signals": [s for s in SIGNAL_LABELS if s["status"] == "LIVE-ONLY"],
        },
        "disclaimer": "Not financial advice. Backtestable research spec; does not place trades or custody funds.",
    }


def build_vault_spec(as_of: str, cfg: dict, exposure: float, regime_on: bool,
                     vault_overlay: dict, oos_metrics: dict, snapshot_sha256: str) -> dict:
    """RotorVault StrategySpec: a backtested FXRP-exposure signal + a LIVE-ONLY venue overlay."""
    return {
        "schema_version": "rotorvault.strategy_spec.v1",
        "strategy": "RotorVault",
        "as_of": as_of,
        "held_asset": "FXRP (XRP)",
        "objective": "Risk-managed FXRP yield: size FXRP exposure by a backtested regime/vol/sentiment signal, then route the deployed portion across Flare yield venues by live APY. Emits an allocation; does not custody funds in the backtest.",
        "signal": {
            "regime_gate": {"source": f"BTC close vs {cfg['regime']['ma']}d MA", "live_only": False},
            "momentum": {"lookback_days": cfg["momentum"]["lookback"], "skip_days": cfg["momentum"]["skip"], "vol_adjusted": True},
            "exposure_scalar": {"vol_target": cfg["vol_target"], "fear_greed": {"floor": cfg["fng"]["floor"], "greed_lo": cfg["fng"]["greed_lo"], "greed_hi": cfg["fng"]["greed_hi"]}},
        },
        "regime": {"state": "risk_on" if regime_on else "risk_off"},
        "fxrp_exposure": round(float(exposure), 4),
        "vault_overlay": {
            "status": "LIVE-ONLY",
            "note": "Populated at runtime from FTSOv2 prices + venue APYs (Upshift via FDC Web2Json, Firelight on-chain). NOT part of the backtest.",
            "venues": ["firelight", "upshift", "idle"],
            **vault_overlay,
        },
        "risk_limits": {"long_only": True, "no_leverage": True, "max_leverage": cfg["vol_target"]["max_leverage"]},
        "cost_model": cfg["costs"],
        "signal_labels": SIGNAL_LABELS,
        "backtest_provenance": {
            "keyless_sources": ["https://data.binance.vision/data/spot/monthly/klines/<SYM>USDT/1d/",
                                 "https://api.alternative.me/fng/?limit=0&format=json"],
            "proxy_note": "FTSOv2 is the live oracle; Binance daily OHLCV is the keyless HISTORICAL proxy for the same assets. Single-venue prices differ slightly from FTSOv2 cross-source VWAP.",
            "snapshot_sha256": snapshot_sha256,
            "out_of_sample": oos_metrics,
        },
        "disclaimer": "Not financial advice. Backtestable research spec; the backtest does not place trades or custody funds.",
    }
