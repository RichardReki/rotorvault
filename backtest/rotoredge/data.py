"""Load the FROZEN, KEYLESS snapshot. The backtest reads ONLY this — no network."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import ROOT


@dataclass
class Snapshot:
    open: pd.DataFrame        # date x symbol  (open price)
    close: pd.DataFrame       # date x symbol  (close price)
    dollar_volume: pd.DataFrame  # date x symbol (Binance quote_asset_volume, USDT)
    fng: pd.Series            # date -> Fear & Greed (0-100)
    manifest: dict

    @property
    def symbols(self) -> list[str]:
        return list(self.close.columns)

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index


def _read_panel(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.DatetimeIndex(df.index).normalize()
    return df.sort_index()


def load_snapshot(snapshot_dir: str | Path = "data/snapshot") -> Snapshot:
    d = Path(snapshot_dir)
    if not d.is_absolute():
        d = ROOT / d
    open_df = _read_panel(d / "open.csv")
    close_df = _read_panel(d / "close.csv")
    qvol_df = _read_panel(d / "dollar_volume.csv")

    fng_df = pd.read_csv(d / "fng.csv", index_col=0, parse_dates=True)
    fng_df.index = pd.DatetimeIndex(fng_df.index).normalize()
    fng = fng_df["fng"].sort_index()

    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8")) if (d / "manifest.json").exists() else {}

    # Align all price panels to a common, sorted, de-duplicated calendar.
    cal = close_df.index
    open_df = open_df.reindex(cal)
    qvol_df = qvol_df.reindex(cal)
    return Snapshot(open=open_df, close=close_df, dollar_volume=qvol_df, fng=fng, manifest=manifest)


def snapshot_checksum(snapshot_dir: str | Path = "data/snapshot") -> str:
    """SHA-256 over the four committed CSVs -> a single fingerprint of the input data."""
    d = Path(snapshot_dir)
    if not d.is_absolute():
        d = ROOT / d
    h = hashlib.sha256()
    for name in ("open.csv", "close.csv", "dollar_volume.csv", "fng.csv"):
        h.update((d / name).read_bytes())
    return h.hexdigest()
