"""Derive the RotorVault 3-asset snapshot (BTC/ETH/XRP + Fear&Greed) from RotorEdge's."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import pandas as pd

SRC = Path(r"f:/Hacks/rotoredge/data/snapshot")
DST = Path(__file__).resolve().parents[1] / "data" / "snapshot"
SYMBOLS = ["BTC", "ETH", "XRP"]

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    manifest = {"as_of": None, "symbols": SYMBOLS, "files": {}, "source": "derived from rotoredge/data/snapshot (BTC/ETH/XRP subset)"}
    for name in ("open", "close", "dollar_volume"):
        df = pd.read_csv(SRC / f"{name}.csv", index_col=0)
        missing = [s for s in SYMBOLS if s not in df.columns]
        if missing:
            raise SystemExit(f"snapshot missing symbols {missing} in {name}.csv; have {list(df.columns)[:10]}...")
        out = df[SYMBOLS].dropna(how="all")
        out.to_csv(DST / f"{name}.csv")
        manifest["files"][f"{name}.csv"] = {"sha256": _sha256(DST / f"{name}.csv"), "rows": len(out), "cols": len(SYMBOLS)}
    # Fear & Greed: copy verbatim (crypto-wide sentiment applies to XRP exposure)
    fng = pd.read_csv(SRC / "fng.csv", index_col=0)
    fng.to_csv(DST / "fng.csv")
    manifest["files"]["fng.csv"] = {"sha256": _sha256(DST / "fng.csv"), "rows": len(fng)}
    close = pd.read_csv(DST / "close.csv", index_col=0)
    manifest["as_of"] = str(close.index.max())
    (DST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {DST} — {SYMBOLS}, {len(close)} rows, as_of {manifest['as_of']}")

if __name__ == "__main__":
    main()
