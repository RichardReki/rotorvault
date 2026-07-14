"""Plots, per-regime labelling, and a deterministic results-hash for reproducibility."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import metrics as M


def regime_labels(snap, dates: pd.DatetimeIndex, ma: int = 100) -> pd.Series:
    """Label each date bull / bear / chop from BTC vs its MA and the MA slope."""
    px = snap.close["BTC"]
    sma = px.rolling(ma, min_periods=ma).mean()
    slope = sma.diff(20)
    lab = pd.Series("chop", index=px.index)
    lab[(px > sma) & (slope > 0)] = "bull"
    lab[(px < sma) & (slope < 0)] = "bear"
    return lab.reindex(dates).fillna("chop")


def equity_plot(curves: dict[str, pd.Series], path: Path, title: str):
    plt.figure(figsize=(10, 5.5))
    for name, daily in curves.items():
        eq = M.to_equity(daily.fillna(0.0))
        lw = 2.4 if name.startswith("RotorEdge") else 1.2
        alpha = 1.0 if name.startswith("RotorEdge") else 0.7
        plt.plot(eq.index, eq.values, label=name, linewidth=lw, alpha=alpha)
    plt.yscale("log")
    plt.title(title)
    plt.ylabel("Growth of $1 (log)")
    plt.legend(fontsize=8, loc="upper left")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=130)
    plt.close()


def heatmap_plot(grid_sharpe: pd.DataFrame, path: Path, title: str):
    plt.figure(figsize=(6.5, 4.8))
    data = grid_sharpe.values.astype(float)
    plt.imshow(data, aspect="auto", cmap="viridis")
    plt.colorbar(label="Sharpe (full sample)")
    plt.xticks(range(len(grid_sharpe.columns)), grid_sharpe.columns)
    plt.yticks(range(len(grid_sharpe.index)), grid_sharpe.index)
    plt.xlabel("top_k")
    plt.ylabel("momentum lookback")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            plt.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center",
                     color="white" if data[i, j] < np.nanmax(data) * 0.6 else "black", fontsize=9)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=130)
    plt.close()


def regime_ribbon_csv(snap, daily: pd.Series, path: Path):
    lab = regime_labels(snap, daily.index)
    df = pd.DataFrame({"equity": M.to_equity(daily.fillna(0.0)), "regime": lab})
    df.to_csv(path)


def canonical_round(obj, nd: int = 6):
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, dict):
        return {k: canonical_round(v, nd) for k, v in obj.items()}
    if isinstance(obj, list):
        return [canonical_round(v, nd) for v in obj]
    return obj


def results_hash(metrics: dict) -> str:
    """Stable SHA-256 over the rounded headline metrics — the reproducibility fingerprint."""
    payload = canonical_round(metrics, 6)
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
