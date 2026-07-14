"""StrategySpec emitter — the Track-2 deliverable IR.

A machine-readable strategy specification (NOT a live order). Every signal is labelled
BACKTESTED (reproducible on keyless data) or LIVE-ONLY (CMC Agent Hub enrichment with
no free history). Carries full backtest provenance so the numbers are independently
verifiable.
"""
from __future__ import annotations

import pandas as pd

from . import universe

SIGNAL_LABELS = [
    {"signal": "vol_adjusted_momentum", "role": "cross-sectional ranking factor", "status": "BACKTESTED", "source": "Binance OHLCV (data.binance.vision)"},
    {"signal": "btc_100d_ma_regime", "role": "master risk-on/off switch", "status": "BACKTESTED", "source": "Binance OHLCV"},
    {"signal": "portfolio_vol_target", "role": "exposure scalar (risk control)", "status": "BACKTESTED", "source": "derived from OHLCV"},
    {"signal": "fear_greed", "role": "exposure scalar", "status": "BACKTESTED", "source": "alternative.me (history to 2018)"},
    {"signal": "altcoin_season_index + btc_eth_dominance", "role": "regime refinement", "status": "LIVE-ONLY", "source": "CMC get_global_metrics_latest"},
    {"signal": "aggregate_funding_open_interest", "role": "crowding de-risk", "status": "LIVE-ONLY", "source": "CMC get_global_crypto_derivatives_metrics"},
    {"signal": "trending_narratives", "role": "sector tilt", "status": "LIVE-ONLY", "source": "CMC trending_crypto_narratives"},
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
