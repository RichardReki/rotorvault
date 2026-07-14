"""KEYLESS reproducibility gate.

Re-runs the full walk-forward from the committed snapshot and asserts the headline
numbers + results-hash match results/REFERENCE.json. A judge runs this with no API key
and gets a deterministic PASS/FAIL. Exits non-zero on any mismatch.

    python scripts/verify.py
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rotoredge.config import load_config
from run_backtest import compute_all  # shared deterministic core

TOL = 1e-6


def main() -> int:
    ref_path = ROOT / "results" / "REFERENCE.json"
    if not ref_path.exists():
        print("FAIL: results/REFERENCE.json missing — run `python scripts/run_backtest.py` first.")
        return 2
    ref = json.loads(ref_path.read_text(encoding="utf-8"))

    cfg = load_config("configs/rotorvault.yaml")
    A = compute_all(cfg)

    checks = [
        ("snapshot_sha256", A["checksum"], ref["snapshot_sha256"], "str"),
        ("results_hash", A["results_hash"], ref["results_hash"], "str"),
        ("oos_sharpe", round(A["oos_summary"]["sharpe"], 6), ref["oos_sharpe"], "num"),
        ("oos_cagr", round(A["oos_summary"]["cagr"], 6), ref["oos_cagr"], "num"),
        ("oos_max_drawdown", round(A["oos_summary"]["max_drawdown"], 6), ref["oos_max_drawdown"], "num"),
    ]
    ok = True
    print("RotorVault reproducibility check (keyless):")
    for name, got, exp, kind in checks:
        good = (got == exp) if kind == "str" else (abs(float(got) - float(exp)) <= TOL)
        ok = ok and good
        shown_got = got[:16] + "..." if kind == "str" else got
        shown_exp = exp[:16] + "..." if kind == "str" else exp
        print(f"  [{'OK ' if good else 'XX '}] {name}: got={shown_got} expected={shown_exp}")

    if ok:
        print("\nPASS — results reproduce byte-identically from the committed snapshot, no API key.")
        return 0
    print("\nFAIL — results do not match the committed reference.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
