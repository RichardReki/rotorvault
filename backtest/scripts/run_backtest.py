"""RotorEdge — full pipeline. KEYLESS: reads only data/snapshot/, writes results/.

    python scripts/run_backtest.py [--config configs/submission.yaml]

Produces walk-forward OOS metrics (headline), IS-vs-OOS degradation, Deflated Sharpe,
baselines/ablations, cost-sensitivity, per-regime stats, plots, the StrategySpec, the
dashboard data, and a reproducibility REFERENCE (results-hash).

compute_all(cfg) holds the deterministic computation and is shared with scripts/verify.py
so the reproducibility hash can never drift between producing and checking.
"""
from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rotoredge.config import load_config
from rotoredge.data import load_snapshot, snapshot_checksum
from rotoredge.backtest import Engine
from rotoredge import metrics as M
from rotoredge import baselines as B
from rotoredge import report as R
from rotoredge.walkforward import walk_forward, stitch_oos
from rotoredge.spec import build_spec

RESULTS = ROOT / "results"


def compute_all(cfg: dict) -> dict:
    """Deterministic core: returns every number + the reproducibility hash."""
    np.random.seed(cfg.get("seed", 7))
    snap = load_snapshot(cfg["snapshot_dir"])
    checksum = snapshot_checksum(cfg["snapshot_dir"])
    eng = Engine(snap, cfg)

    is_run = eng.run(start=cfg["backtest"]["start"])
    is_summary = M.summarize(is_run.daily_returns, is_run.period_returns)

    wf = walk_forward(eng, cfg)
    oos = wf["oos_daily"]
    oos_summary = M.summarize(oos, wf["oos_period"])
    dsr = M.deflated_sharpe_ratio(oos, wf["trial_sharpes"], wf["n_trials"])
    oos_start, oos_end = str(oos.index.min().date()), str(oos.index.max().date())

    base = B.build_baselines(snap, cfg, oos_start, oos_end)
    base_summ = {name: M.summarize(r) for name, r in base.items()}

    cost_table = {}
    for mult in cfg["cost_sensitivity"]:
        s = stitch_oos(eng, cfg, wf["folds"], mult)
        cost_table[f"{mult}x"] = {k: M.summarize(s)[k] for k in ("sharpe", "cagr", "max_drawdown", "total_return")}

    labels = R.regime_labels(snap, oos.index)
    regime_stats = {}
    for reg in ("bull", "bear", "chop"):
        rr = oos[labels == reg]
        if len(rr) > 5:
            regime_stats[reg] = {"days": int(len(rr)), **{k: M.summarize(rr)[k] for k in ("sharpe", "cagr", "max_drawdown", "total_return")}}

    results_hash = R.results_hash({"oos": oos_summary, "is": is_summary, "dsr": dsr, "cost": cost_table, "regime": regime_stats, "checksum": checksum})

    return dict(snap=snap, eng=eng, checksum=checksum, is_run=is_run, is_summary=is_summary,
                wf=wf, oos=oos, oos_summary=oos_summary, dsr=dsr, oos_start=oos_start, oos_end=oos_end,
                base=base, base_summ=base_summ, cost_table=cost_table, labels=labels,
                regime_stats=regime_stats, results_hash=results_hash)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/submission.yaml")
    args = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)

    cfg = load_config(args.config)
    A = compute_all(cfg)
    snap, oos, wf = A["snap"], A["oos"], A["wf"]
    oos_summary, base_summ = A["oos_summary"], A["base_summ"]
    print(f"[data] {len(snap.symbols)} symbols, {snap.close.index.min().date()}..{snap.close.index.max().date()}, sha256={A['checksum'][:16]}")
    print(f"[oos] {A['oos_start']}..{A['oos_end']}  Sharpe={oos_summary['sharpe']:.3f}  CAGR={oos_summary['cagr']:.3f}  maxDD={oos_summary['max_drawdown']:.3f}  DSR={A['dsr']['dsr']:.3f}")

    # plots + spec
    g = cfg["walkforward"]["param_grid"]
    grid_df = pd.DataFrame(np.array(wf["trial_sharpes"]).reshape(len(g["lookback"]), len(g["top_k"])),
                           index=[f"L{x}" for x in g["lookback"]], columns=[f"k{x}" for x in g["top_k"]])
    curves = {"RotorEdge (OOS)": oos, **A["base"]}
    R.equity_plot(curves, RESULTS / "equity_oos.png", f"RotorEdge walk-forward OOS vs baselines ({A['oos_start']}..{A['oos_end']})")
    R.heatmap_plot(grid_df, RESULTS / "heatmap.png", "Parameter sensitivity (full-sample Sharpe)")
    R.regime_ribbon_csv(snap, oos, RESULTS / "regime_ribbon.csv")
    M.to_equity(oos.fillna(0.0)).to_csv(RESULTS / "oos_curve.csv", header=["equity"])

    spec = build_spec(snap, cfg, A["is_run"], oos_summary, A["checksum"])
    (RESULTS / "strategy_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

    headline = {
        "snapshot_sha256": A["checksum"], "oos_window": [A["oos_start"], A["oos_end"]],
        "out_of_sample": oos_summary, "in_sample": A["is_summary"],
        "is_vs_oos_sharpe": {"is": A["is_summary"]["sharpe"], "oos": oos_summary["sharpe"]},
        "deflated_sharpe": A["dsr"], "baselines": base_summ, "cost_sensitivity": A["cost_table"],
        "per_regime": A["regime_stats"], "walk_forward_folds": wf["folds"],
        "config": {k: cfg[k] for k in ("universe_n", "top_k", "momentum", "rebalance_days", "deadband", "regime", "vol_target", "fng", "weighting", "costs", "walkforward")},
        "results_hash": A["results_hash"],
    }
    (RESULTS / "metrics.json").write_text(json.dumps(R.canonical_round(headline, 6), indent=2), encoding="utf-8")
    (RESULTS / "REFERENCE.json").write_text(json.dumps({"snapshot_sha256": A["checksum"], "results_hash": A["results_hash"],
        "oos_sharpe": round(oos_summary["sharpe"], 6), "oos_cagr": round(oos_summary["cagr"], 6),
        "oos_max_drawdown": round(oos_summary["max_drawdown"], 6)}, indent=2), encoding="utf-8")

    dash = {
        "oos_window": [A["oos_start"], A["oos_end"]],
        "equity": {name: {"dates": [str(d.date()) for d in M.to_equity(r.fillna(0.0)).index],
                          "values": [round(float(x), 5) for x in M.to_equity(r.fillna(0.0)).values]} for name, r in curves.items()},
        "regime": [str(x) for x in A["labels"].values],
        "weights_timeline": [{"date": str(pd.Timestamp(d).date()), "weights": w} for d, w in sorted(wf["oos_weights"].items())],
        "metrics": {"RotorEdge (OOS)": oos_summary, **base_summ},
        "deflated_sharpe": A["dsr"], "cost_sensitivity": A["cost_table"], "per_regime": A["regime_stats"],
        "folds": wf["folds"], "spec_preview": {k: spec[k] for k in ("as_of", "regime", "exposure", "target_weights", "universe")},
    }
    (RESULTS / "dashboard_data.json").write_text(json.dumps(R.canonical_round(dash, 5), indent=2), encoding="utf-8")
    (ROOT / "dashboard" / "data.js").write_text("window.ROTOR_DATA = " + json.dumps(R.canonical_round(dash, 5)) + ";", encoding="utf-8")

    print(f"[done] results-hash={A['results_hash'][:16]}")
    print(f"[oos] Sharpe {oos_summary['sharpe']:.3f} | Sortino {oos_summary['sortino']:.3f} | Calmar {oos_summary['calmar']:.3f} | maxDD {oos_summary['max_drawdown']:.3f} | DSR {A['dsr']['dsr']:.3f}")
    for n, s in base_summ.items():
        print(f"   {n:28s} Sharpe {s['sharpe']:.3f}  CAGR {s['cagr']:.3f}  maxDD {s['max_drawdown']:.3f}")


if __name__ == "__main__":
    main()
