"""Emit results/rotorvault_spec.json from the frozen config + committed snapshot."""
from __future__ import annotations
import json
from pathlib import Path
from rotoredge.config import load_config
from rotoredge import data, vault
from rotoredge.backtest import Engine
from rotoredge.spec import build_vault_spec

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    cfg = load_config("configs/rotorvault.yaml")
    snap = data.load_snapshot(cfg["snapshot_dir"])
    sha = json.load(open(ROOT / cfg["snapshot_dir"] / "manifest.json"))["files"]["close.csv"]["sha256"]
    run = Engine(snap, cfg).run(start=cfg["backtest"]["start"], end=cfg["backtest"]["end"])
    last = run.exposure.index[-1]
    exposure = float(run.exposure.loc[last])
    regime_on = bool(run.regime_on.loc[last])
    # LIVE-ONLY placeholder APYs for the emitted spec (real values arrive at runtime in Plan 3)
    apys = {"firelight": 0.0, "upshift": 0.08}
    overlay = vault.allocate(exposure, regime_on, apys, {"max_venue_weight": 0.8})
    oos = {"note": "see results/*metrics*.json for full IS/OOS table"}
    spec = build_vault_spec(str(last.date()), cfg, exposure, regime_on, overlay, oos, sha)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "rotorvault_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print("wrote results/rotorvault_spec.json  exposure=%.3f regime_on=%s" % (exposure, regime_on))

if __name__ == "__main__":
    main()
