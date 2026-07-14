# RotorVault — Plan 1: Backtest Port & StrategySpec — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port RotorEdge's causal backtest engine into `rotorvault/backtest/` as a 3-asset (BTC/ETH/XRP) FXRP-exposure signal, prove the regime + vol-target + Fear&Greed overlay reduces drawdown vs always-held XRP, and emit a `rotorvault_spec.json` with a LIVE-ONLY venue-allocation overlay — preserving RotorEdge's BACKTESTED-vs-LIVE-ONLY discipline.

**Architecture:** Copy RotorEdge's audited engine (data/signals/backtest/metrics/walkforward/costs/report/verify + no-lookahead tests) unchanged; trim the committed snapshot to BTC/ETH/XRP + Fear&Greed; add a frozen 3-asset config; add a minimal `hold_symbol` selection so the held book is FXRP-proxy XRP sized by the exposure scalar; retune baselines to XRP-centric; add a NEW pure LIVE-ONLY `vault.py` allocation overlay (signal + live APYs → {Firelight, Upshift, idle}); emit a RotorVault StrategySpec. The backtested numbers use only the committed snapshot (keyless, reproducible); FTSOv2 prices and venue APYs are runtime-only and never enter the backtest.

**Tech Stack:** Python 3.13, pandas, numpy, pyyaml, matplotlib, pytest (RotorEdge's existing deps). Source engine: `f:/Hacks/rotoredge`.

---

## Context the engineer needs (read first)

- **Where things are.** The existing RotorEdge project is at `f:/Hacks/rotoredge`. The new project root is `f:/Hacks/rotorvault`. This plan builds the Python subtree `rotorvault/backtest/`. Run all Python commands **from `rotorvault/backtest/`** (that dir is the package root; `rotoredge/config.py` computes `ROOT = parents[1]` = the `backtest/` dir, and reads `data/snapshot/` under it).
- **The engine is causal and audited — do NOT rewrite it.** `rotoredge/backtest.py` `Engine.run` decides using info through the prior close (`j-1`) and executes at day `j`'s open; `tests/test_no_lookahead.py` asserts that perturbing any future price leaves prior P&L byte-identical. Every change in this plan is additive/config; keep the no-lookahead property intact.
- **What the exposure scalar is.** `Engine._gross(j_dec, comp)` (backtest.py:89) returns the daily gross exposure in `[0, max_leverage]` from `regime_on` (BTC vs 100d MA) × Fear&Greed scalar × vol-target. With a single held name (XRP), `target = comp * gross` means "hold XRP at this exposure." That scalar is exactly the FXRP exposure the live vault will apply. The LIVE overlay (Task 7) turns it into a venue split.
- **Honesty rule (non-negotiable, inherited from RotorEdge).** Backtested signals read only `data/snapshot/`. Live-only signals (FTSOv2 spot price, venue APYs) have no free history and are NEVER mixed into backtested numbers — they live in the spec's `live_overlay`/`vault_overlay` and are labelled `LIVE-ONLY`.
- **6-decimal note (for later plans, not this one).** FXRP/FTestXRP/stXRP are 6-decimal on-chain. This Python backtest works in price space (floats), so decimals don't bite here — but do not carry any 18-dp assumption into Plans 2-3.

## File Structure

```
rotorvault/backtest/
├── rotoredge/                     # ported engine (pre-existing RotorEdge — attribution in README)
│   ├── __init__.py                # copy (DIRECT)
│   ├── data.py                    # copy (DIRECT) — snapshot loader + SHA-256
│   ├── universe.py                # copy (DIRECT)
│   ├── signals.py                 # copy (DIRECT) — momentum_factor, regime_on, fng_scalar, realized_vol
│   ├── costs.py                   # copy (DIRECT)
│   ├── backtest.py                # ADAPT (Task 4): add hold_symbol short-circuit in _composition
│   ├── metrics.py                 # copy (DIRECT)
│   ├── walkforward.py             # copy (DIRECT)
│   ├── report.py                  # copy (DIRECT)
│   ├── config.py                  # ADAPT (Task 3): DEFAULTS -> 3-asset; default config path
│   ├── baselines.py               # ADAPT (Task 5): HODL BTC/ETH/XRP + no-overlay XRP ablation
│   ├── spec.py                    # ADAPT (Task 8): RotorVault schema + vault_overlay + labels
│   └── vault.py                   # NEW (Task 7): LIVE-ONLY venue-allocation overlay (pure fn)
├── configs/rotorvault.yaml        # NEW (Task 3): the frozen 3-asset config
├── data/snapshot/                 # NEW (Task 2): trimmed BTC/ETH/XRP + fng + manifest.json
├── scripts/
│   ├── build_snapshot.py          # NEW (Task 2): derive trimmed snapshot from RotorEdge's
│   ├── run_backtest.py            # copy (DIRECT)
│   ├── make_vault_spec.py         # NEW (Task 8): emit results/rotorvault_spec.json
│   └── verify.py                  # copy+ADAPT (Task 9): reproducibility gate
├── tests/
│   ├── _synth.py test_no_lookahead.py test_costs.py test_metrics.py test_survivorship.py  # copy (DIRECT)
│   ├── test_hold_symbol.py        # NEW (Task 4)
│   └── test_vault_overlay.py      # NEW (Task 7)
├── results/                       # generated
├── requirements.txt               # copy (DIRECT)
└── README.md                      # NEW (Task 10): backtest honesty + how-to-repro
```

---

### Task 1: Scaffold `backtest/` by copying the RotorEdge engine

**Files:**
- Create: `rotorvault/backtest/rotoredge/*.py` (copied), `rotorvault/backtest/tests/*` (copied), `rotorvault/backtest/scripts/{run_backtest.py}` (copied), `rotorvault/backtest/requirements.txt` (copied)

- [ ] **Step 1: Copy the engine, tests, scripts, and requirements**

Run (from `f:/Hacks`, Git Bash):
```bash
mkdir -p rotorvault/backtest/rotoredge rotorvault/backtest/tests rotorvault/backtest/scripts rotorvault/backtest/results
cp rotoredge/rotoredge/{__init__,data,universe,signals,costs,backtest,metrics,walkforward,report,config,baselines,spec}.py rotorvault/backtest/rotoredge/
cp rotoredge/tests/{_synth,test_no_lookahead,test_costs,test_metrics,test_survivorship,run_all}.py rotorvault/backtest/tests/
cp rotoredge/scripts/run_backtest.py rotorvault/backtest/scripts/
cp rotoredge/requirements.txt rotorvault/backtest/requirements.txt
```
Do NOT copy `__pycache__`, `data/`, `configs/`, `results/`, `.git`, `skills/`, `dashboard/`, `docs/`.

- [ ] **Step 2: Install deps and run the copied unit tests to verify the copy is intact**

The unit tests use synthetic data (`tests/_synth.py`), so they are config-independent and must pass immediately.

Run (from `rotorvault/backtest/`):
```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_no_lookahead.py tests/test_costs.py tests/test_metrics.py tests/test_survivorship.py -q
```
Expected: all tests PASS (the engine is unchanged; these validate the engine, not any snapshot).

- [ ] **Step 3: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest && git commit -m "chore(backtest): vendor RotorEdge engine + tests into rotorvault/backtest"
```

---

### Task 2: Build the trimmed 3-asset snapshot (BTC/ETH/XRP + Fear&Greed)

**Files:**
- Create: `rotorvault/backtest/scripts/build_snapshot.py`
- Create (generated): `rotorvault/backtest/data/snapshot/{open,close,dollar_volume}.csv`, `fng.csv`, `manifest.json`

RotorEdge's snapshot CSVs are date-indexed with one column per symbol. We select BTC/ETH/XRP, copy Fear&Greed as-is, and regenerate the SHA-256 manifest (RotorEdge's `data.py` loader + `manifest.json` format is reused; only the symbol set changes).

- [ ] **Step 1: Write `scripts/build_snapshot.py`**

```python
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
```

- [ ] **Step 2: Run it and verify the snapshot loads through the engine's loader**

Run (from `rotorvault/backtest/`):
```bash
python scripts/build_snapshot.py
python -c "from rotoredge import data; s=data.load_snapshot('data/snapshot'); print(sorted(s.close.columns), len(s.close), s.close.index.min(), s.close.index.max())"
```
Expected: prints `['BTC', 'ETH', 'XRP']`, a row count (~2700), and a date range starting 2019. If `load_snapshot`'s signature differs, check `rotoredge/data.py` for the exact loader name and args and adjust the one-liner.

- [ ] **Step 3: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/scripts/build_snapshot.py backtest/data/snapshot && git commit -m "feat(backtest): trimmed BTC/ETH/XRP + F&G snapshot with SHA-256 manifest"
```

---

### Task 3: Frozen 3-asset config + adapt `config.py` DEFAULTS

**Files:**
- Create: `rotorvault/backtest/configs/rotorvault.yaml`
- Modify: `rotorvault/backtest/rotoredge/config.py` (DEFAULTS + default path)

- [ ] **Step 1: Write `configs/rotorvault.yaml`**

```yaml
# RotorVault — FROZEN config. Backtest is KEYLESS (reads only data/snapshot/).
# Held book = XRP (FXRP proxy) sized by regime + vol-target + Fear&Greed exposure scalar.
seed: 7
snapshot_dir: data/snapshot
regime_asset: BTC          # BTC vs 100d MA is the master risk-on/off (trend) gate

# Universe: the 3 FTSO-priced majors. hold_symbol forces the held book to XRP (only live-holdable = FXRP).
universe_n: 3
hold_symbol: XRP
min_history_days: 130
vol_window: 30

momentum: {lookback: 90, skip: 5}   # surfaced for the spec/live overlay; regime is the exposure driver
top_k: 1
weighting: equal
rebalance_days: 21
deadband: 2.0              # monthly composition; daily risk. (Daily kill-switch whipsawed OOS in RotorEdge.)
long_only_positive: false
regime: {enabled: true, ma: 100, risk_off_to: cash}
vol_target: {enabled: true, target_vol: 0.35, max_leverage: 1.0}
fng: {floor: 0.5, greed_lo: 55, greed_hi: 90, shift: 1}

# Flare DEX / venue cost proxy (retuned from PancakeSwap; Flare gas is cheap, Upshift instant-redeem ~1%).
costs:
  fee_bps: 20.0
  buffer_bps: 10.0
  gas_usd: 0.05
  pool_depth_usd: 1500000.0
  notional_usd: 100000.0

backtest: {start: "2019-07-01", end: null}

walkforward:
  train_days: 730
  test_days: 180
  param_grid:
    lookback: [60, 90, 120]
    top_k: [1]
cost_sensitivity: [0.0, 1.0, 2.0]
exclude: []
```

- [ ] **Step 2: Update `rotoredge/config.py` DEFAULTS to the 3-asset values and default path**

In `rotoredge/config.py`, change these `DEFAULTS` keys (leave the rest as-is): `universe_n: 3`, add `"hold_symbol": "XRP"`, `top_k: 1`, `weighting: "equal"`, and set `walkforward.param_grid` to `{"lookback": [60, 90, 120], "top_k": [1]}`. Also change the default path in `load_config` from `"configs/submission.yaml"` to `"configs/rotorvault.yaml"`.

```python
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
```
And:
```python
def load_config(path: str | Path = "configs/rotorvault.yaml") -> dict:
```

- [ ] **Step 3: Verify the config loads and merges**

Run (from `rotorvault/backtest/`):
```bash
python -c "from rotoredge.config import load_config; c=load_config(); print(c['hold_symbol'], c['universe_n'], c['top_k'], c['regime_asset'])"
```
Expected: `XRP 3 1 BTC`

- [ ] **Step 4: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/configs/rotorvault.yaml backtest/rotoredge/config.py && git commit -m "feat(backtest): frozen 3-asset RotorVault config (hold_symbol=XRP)"
```

---

### Task 4: Add `hold_symbol` support to the engine (TDD)

**Files:**
- Test: `rotorvault/backtest/tests/test_hold_symbol.py`
- Modify: `rotorvault/backtest/rotoredge/backtest.py` (`_composition`, at the top)

When `cfg["hold_symbol"]` is set, `_composition` returns weight 1.0 on that symbol (if eligible & priced at the decision index) and bypasses momentum ranking. `_gross` then scales it to the daily exposure. This is the whole "held book = XRP sized by the signal" change.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hold_symbol.py
import numpy as np
from rotoredge.backtest import Engine
from tests._synth import make_snapshot  # RotorEdge's synthetic snapshot helper

def _cfg(**over):
    base = {"vol_window": 30, "min_history_days": 5, "regime_asset": "BTC",
            "regime": {"enabled": True, "ma": 5}, "momentum": {"lookback": 5, "skip": 1},
            "vol_target": {"enabled": False, "max_leverage": 1.0},
            "fng": {"floor": 1.0, "greed_lo": 55, "greed_hi": 90, "shift": 1},
            "top_k": 1, "universe_n": 3, "weighting": "equal", "long_only_positive": False}
    base.update(over)
    return base

def test_hold_symbol_forces_single_name():
    snap = make_snapshot(["BTC", "ETH", "XRP"], days=60, seed=1)
    eng = Engine(snap, _cfg(hold_symbol="XRP"))
    j = 40
    w = eng._composition(j, {"universe_n": 3, "top_k": 1, "weighting": "equal",
                             "lookback": 5, "skip": 1}, eng._factor(5, 1))
    xrp = eng.symbols.index("XRP")
    assert w[xrp] == 1.0
    assert w.sum() == 1.0  # only XRP held
```
If `tests/_synth.py` exposes a different constructor than `make_snapshot(symbols, days, seed)`, open it and use its real signature (it is the same helper the copied tests import).

- [ ] **Step 2: Run to verify it fails**

Run (from `rotorvault/backtest/`): `python -m pytest tests/test_hold_symbol.py -q`
Expected: FAIL (current `_composition` ignores `hold_symbol` and ranks by momentum).

- [ ] **Step 3: Implement the short-circuit at the top of `_composition`**

In `rotoredge/backtest.py`, insert at the very top of `_composition` (right after `w = np.zeros(n)`):
```python
    def _composition(self, j_dec: int, params: dict, factor: np.ndarray) -> np.ndarray:
        """Relative weights (sum=1) of the selected long-only momentum names at j_dec."""
        n = len(self.symbols)
        w = np.zeros(n)
        hold = self.cfg.get("hold_symbol")
        if hold:
            if hold in self.symbols:
                s = self.symbols.index(hold)
                if self.elig[j_dec, s] and not np.isnan(self.close[j_dec, s]):
                    w[s] = 1.0
            return w
        # ---- original momentum-ranking path below (unchanged) ----
        v, e = self.tdv[j_dec], self.elig[j_dec]
        ...
```
(Keep every existing line after the insert exactly as it was.)

- [ ] **Step 4: Run tests to verify pass (and no-lookahead still holds)**

Run (from `rotorvault/backtest/`):
```bash
python -m pytest tests/test_hold_symbol.py tests/test_no_lookahead.py -q
```
Expected: PASS for both (the new branch is causal — it reads only `j_dec` state).

- [ ] **Step 5: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/rotoredge/backtest.py backtest/tests/test_hold_symbol.py && git commit -m "feat(backtest): hold_symbol short-circuit to force the held book to XRP"
```

---

### Task 5: Retune baselines to XRP-centric (TDD)

**Files:**
- Modify: `rotorvault/backtest/rotoredge/baselines.py`
- Test: extend `rotorvault/backtest/tests/test_metrics.py` is copied; add `tests/test_baselines.py`

The meaningful baselines for a single-held FXRP book are: **HODL BTC/ETH/XRP** (context) and **XRP full-exposure, no overlay** (the ablation that isolates the risk overlay's value). Drop "EqualWeight Universe" (degenerate when `hold_symbol` collapses the book to one name).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_baselines.py
from rotoredge.baselines import build_baselines
from tests._synth import make_snapshot

def _cfg():
    return {"vol_window": 30, "min_history_days": 5, "regime_asset": "BTC",
            "regime": {"enabled": True, "ma": 5}, "momentum": {"lookback": 5, "skip": 1},
            "vol_target": {"enabled": True, "target_vol": 0.35, "max_leverage": 1.0},
            "fng": {"floor": 0.5, "greed_lo": 55, "greed_hi": 90, "shift": 1},
            "top_k": 1, "universe_n": 3, "weighting": "equal", "hold_symbol": "XRP",
            "long_only_positive": False, "rebalance_days": 21, "deadband": 2.0,
            "costs": {"fee_bps": 20.0, "buffer_bps": 10.0, "gas_usd": 0.05,
                      "pool_depth_usd": 1_500_000.0, "notional_usd": 100_000.0}}

def test_baselines_are_xrp_centric():
    snap = make_snapshot(["BTC", "ETH", "XRP"], days=400, seed=2)
    b = build_baselines(snap, _cfg(), start="2000-01-10", end=None)
    assert "HODL XRP" in b and "HODL BTC" in b and "HODL ETH" in b
    assert "XRP full-exposure (no overlay)" in b
    assert "EqualWeight Universe" not in b
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_baselines.py -q` → FAIL (names are `HODL BTC/BNB`, includes `EqualWeight Universe`).

- [ ] **Step 3: Rewrite `build_baselines`**

Replace `build_baselines` in `rotoredge/baselines.py` with:
```python
def build_baselines(snap, cfg: dict, start, end, cost_mult: float = 1.0) -> dict[str, pd.Series]:
    """Return {name: daily_returns} for XRP-centric baselines/ablations, aligned to the period."""
    out: dict[str, pd.Series] = {}
    fee = cfg["costs"]["fee_bps"] + cfg["costs"]["buffer_bps"]
    for sym in ("BTC", "ETH", "XRP"):
        if sym in snap.symbols:
            out[f"HODL {sym}"] = hodl_returns(snap, sym, start, end, fee)
    # Same held book (XRP) but NO risk overlay -> isolates the value of the OVERLAY.
    mo = _cfg_no_overlay(cfg)
    out["XRP full-exposure (no overlay)"] = Engine(snap, mo).run(start=start, end=end, cost_mult=cost_mult).daily_returns
    return out
```
(`_cfg_no_overlay` and `hodl_returns` are unchanged; `hold_symbol` stays set in `mo`, so the no-overlay book is XRP held at gross=1.)

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_baselines.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/rotoredge/baselines.py backtest/tests/test_baselines.py && git commit -m "feat(backtest): XRP-centric baselines + no-overlay ablation"
```

---

### Task 6: Run the full backtest and confirm the headline claim

**Files:**
- Uses: `rotorvault/backtest/scripts/run_backtest.py` (copied); generates `results/`

- [ ] **Step 1: Run the walk-forward backtest on the frozen config**

Run (from `rotorvault/backtest/`):
```bash
python scripts/run_backtest.py --config configs/rotorvault.yaml
```
If `run_backtest.py` uses a different flag, run `python scripts/run_backtest.py --help` and adapt. It should read `configs/rotorvault.yaml`, run the anchored walk-forward, and write metrics + plots into `results/`.

- [ ] **Step 2: Verify the headline: the overlay reduces drawdown vs XRP HODL**

Run (from `rotorvault/backtest/`):
```bash
python -c "import json,glob; m=json.load(open(sorted(glob.glob('results/*metrics*.json'))[-1])); print(json.dumps(m, indent=2))"
```
Expected/observe: the strategy's **max drawdown** is smaller (less negative) than `HODL XRP`'s, and its Sortino/Calmar are higher, over the out-of-sample window. Record the exact numbers. (This is the claim the pitch makes — do NOT proceed if the overlay does not reduce drawdown; if it doesn't, stop and report; a tuning task would be added.)

- [ ] **Step 3: Commit results**

```bash
cd f:/Hacks/rotorvault && git add backtest/results && git commit -m "chore(backtest): committed walk-forward results (3-asset FXRP-exposure signal)"
```

---

### Task 7: NEW LIVE-ONLY venue-allocation overlay `vault.py` (TDD)

**Files:**
- Create: `rotorvault/backtest/rotoredge/vault.py`
- Test: `rotorvault/backtest/tests/test_vault_overlay.py`

Pure function: map `(exposure, regime_on, apys)` → an FXRP venue allocation over `{firelight, upshift, idle}`. This is LIVE-ONLY (venue APYs have no free history) and is emitted into the spec, never backtested. Deterministic and fully unit-tested with mock APYs.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_vault_overlay.py
import pytest
from rotoredge.vault import allocate

CFG = {"max_venue_weight": 0.8}

def _sum(alloc):
    v = alloc["venue_allocation"]
    return round(v["firelight"] + v["upshift"] + v["idle"], 9)

def test_risk_off_goes_fully_idle():
    a = allocate(exposure=0.0, regime_on=False, apys={"firelight": 0.03, "upshift": 0.08}, cfg=CFG)
    assert a["fxrp_exposure"] == 0.0
    assert a["venue_allocation"]["idle"] == 1.0
    assert _sum(a) == 1.0

def test_deployed_portion_tilts_to_higher_apy():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.02, "upshift": 0.08}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["upshift"] > v["firelight"] > 0.0
    assert _sum(a) == 1.0

def test_exposure_leaves_remainder_idle():
    a = allocate(exposure=0.6, regime_on=True, apys={"firelight": 0.04, "upshift": 0.04}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["idle"] == pytest.approx(0.4)
    assert v["firelight"] == pytest.approx(0.3)
    assert v["upshift"] == pytest.approx(0.3)
    assert _sum(a) == 1.0

def test_per_venue_cap_overflow_to_idle():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.0, "upshift": 0.10}, cfg={"max_venue_weight": 0.7})
    v = a["venue_allocation"]
    assert v["upshift"] == pytest.approx(0.7)         # capped
    assert v["idle"] == pytest.approx(0.3)            # overflow parked idle
    assert _sum(a) == 1.0

def test_zero_apy_info_splits_equally():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.0, "upshift": 0.0}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["firelight"] == pytest.approx(0.5)
    assert v["upshift"] == pytest.approx(0.5)
    assert _sum(a) == 1.0
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_vault_overlay.py -q` → FAIL (`rotoredge.vault` does not exist).

- [ ] **Step 3: Implement `rotoredge/vault.py`**

```python
"""LIVE-ONLY venue-allocation overlay. NOT backtested (venue APYs have no free history).

Input:
  exposure : float in [0,1]  -- the engine's daily gross exposure for FXRP (from Engine._gross)
  regime_on: bool            -- master risk-on/off (BTC vs MA)
  apys     : {venue: apy_fraction}  -- LIVE APYs (Upshift via FDC Web2Json; Firelight on-chain-derived)
  cfg      : {max_venue_weight: float}
Output (all fractions of the whole book, summing to 1.0):
  {"fxrp_exposure": float, "venue_allocation": {"firelight": ., "upshift": ., "idle": .}}
"""
from __future__ import annotations


def allocate(exposure: float, regime_on: bool, apys: dict, cfg: dict) -> dict:
    exposure = max(0.0, min(1.0, float(exposure)))
    venues = ["firelight", "upshift"]
    if not regime_on or exposure <= 0.0:
        return {"fxrp_exposure": 0.0,
                "venue_allocation": {"firelight": 0.0, "upshift": 0.0, "idle": 1.0}}

    cap = float(cfg.get("max_venue_weight", 0.8))
    pos = {v: max(0.0, float(apys.get(v, 0.0))) for v in venues}
    total = sum(pos.values())
    if total <= 0.0:
        split = {v: exposure / len(venues) for v in venues}
    else:
        split = {v: exposure * (pos[v] / total) for v in venues}

    # per-venue cap (as a fraction of the whole book); overflow parks idle
    overflow = 0.0
    for v in venues:
        if split[v] > cap:
            overflow += split[v] - cap
            split[v] = cap
    idle = (1.0 - exposure) + overflow
    return {"fxrp_exposure": exposure,
            "venue_allocation": {"firelight": split["firelight"], "upshift": split["upshift"], "idle": idle}}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m pytest tests/test_vault_overlay.py -q` → PASS (all 5).

- [ ] **Step 5: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/rotoredge/vault.py backtest/tests/test_vault_overlay.py && git commit -m "feat(backtest): LIVE-ONLY FXRP venue-allocation overlay (pure fn)"
```

---

### Task 8: RotorVault StrategySpec — labels, `vault_overlay`, emitter (TDD)

**Files:**
- Modify: `rotorvault/backtest/rotoredge/spec.py` (SIGNAL_LABELS + new `build_vault_spec`)
- Create: `rotorvault/backtest/scripts/make_vault_spec.py`
- Test: `rotorvault/backtest/tests/test_spec.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spec.py
import json
from rotoredge.spec import build_vault_spec, SIGNAL_LABELS

def test_labels_mark_venue_apys_live_only():
    live = [s for s in SIGNAL_LABELS if s["status"] == "LIVE-ONLY"]
    assert any("apy" in s["signal"].lower() or "venue" in s["signal"].lower() for s in live)
    assert any("ftso" in s["source"].lower() for s in SIGNAL_LABELS)

def test_build_vault_spec_shape():
    spec = build_vault_spec(
        as_of="2026-05-31", cfg={"regime_asset": "BTC", "regime": {"ma": 100},
            "momentum": {"lookback": 90, "skip": 5}, "vol_target": {"target_vol": 0.35, "max_leverage": 1.0},
            "fng": {"floor": 0.5, "greed_lo": 55, "greed_hi": 90}, "rebalance_days": 21,
            "costs": {}, "hold_symbol": "XRP"},
        exposure=0.6, regime_on=True,
        vault_overlay={"fxrp_exposure": 0.6, "venue_allocation": {"firelight": 0.3, "upshift": 0.3, "idle": 0.4}},
        oos_metrics={"sharpe": 0.4, "max_drawdown": -0.3}, snapshot_sha256="deadbeef")
    assert spec["strategy"] == "RotorVault"
    assert spec["held_asset"] == "FXRP (XRP)"
    assert spec["vault_overlay"]["venue_allocation"]["idle"] == 0.4
    assert spec["vault_overlay"]["status"] == "LIVE-ONLY"
    json.dumps(spec)  # must be serializable
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_spec.py -q` → FAIL (`build_vault_spec` undefined; labels are RotorEdge's CMC set).

- [ ] **Step 3: Replace `SIGNAL_LABELS` and add `build_vault_spec` in `spec.py`**

Replace the `SIGNAL_LABELS` list with:
```python
SIGNAL_LABELS = [
    {"signal": "btc_100d_ma_regime", "role": "master risk-on/off (trend) gate", "status": "BACKTESTED", "source": "Binance OHLCV proxy for FTSOv2 BTC/USD"},
    {"signal": "vol_adjusted_momentum", "role": "surfaced strength signal", "status": "BACKTESTED", "source": "Binance OHLCV proxy for FTSOv2 XRP/BTC/ETH"},
    {"signal": "portfolio_vol_target", "role": "FXRP exposure scalar", "status": "BACKTESTED", "source": "derived from OHLCV"},
    {"signal": "fear_greed", "role": "FXRP exposure scalar", "status": "BACKTESTED", "source": "alternative.me (history to 2018)"},
    {"signal": "ftsov2_spot_price", "role": "live NAV + on-chain regime sampling", "status": "LIVE-ONLY", "source": "FTSOv2 getFeedById (Coston2)"},
    {"signal": "venue_apy (firelight, upshift)", "role": "yield tilt across venues", "status": "LIVE-ONLY", "source": "Upshift API via FDC Web2Json; Firelight on-chain exchange-rate derivation"},
]
```
Then append a new function (keep the existing `build_spec` for reference/backwards use):
```python
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
```

- [ ] **Step 4: Run the spec test to verify pass**

Run: `python -m pytest tests/test_spec.py -q` → PASS.

- [ ] **Step 5: Write `scripts/make_vault_spec.py` and generate the spec**

```python
"""Emit results/rotorvault_spec.json from the frozen config + committed snapshot."""
from __future__ import annotations
import json
from pathlib import Path
from rotoredge.config import load_config
from rotoredge import data, signals, vault
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
```
Run (from `rotorvault/backtest/`): `python scripts/make_vault_spec.py`
Expected: writes `results/rotorvault_spec.json` and prints the exposure. If `data.load_snapshot`'s name/args differ, match `rotoredge/data.py`.

- [ ] **Step 6: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/rotoredge/spec.py backtest/scripts/make_vault_spec.py backtest/tests/test_spec.py backtest/results/rotorvault_spec.json && git commit -m "feat(backtest): RotorVault StrategySpec with LIVE-ONLY vault_overlay"
```

---

### Task 9: Reproducibility gate

**Files:**
- Create: `rotorvault/backtest/scripts/verify.py` (adapt RotorEdge's), `rotorvault/backtest/reproduce.sh`

- [ ] **Step 1: Copy RotorEdge's verify.py and point it at the new config/snapshot**

```bash
cp f:/Hacks/rotoredge/scripts/verify.py f:/Hacks/rotorvault/backtest/scripts/verify.py
```
Open `scripts/verify.py`; change any `configs/submission.yaml` reference to `configs/rotorvault.yaml`. It should: re-run from the committed snapshot, recompute metrics, and assert the snapshot SHA-256 in `manifest.json` matches the files on disk. If it hardcodes RotorEdge reference metric values, relax that assertion to "runs clean + snapshot hash matches" (we are not byte-pinning metrics in Plan 1).

- [ ] **Step 2: Write `reproduce.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pytest tests -q
python scripts/verify.py
python scripts/make_vault_spec.py
echo "OK: tests pass, snapshot verified, spec emitted."
```

- [ ] **Step 3: Run the full gate**

Run (from `rotorvault/backtest/`): `bash reproduce.sh`
Expected: all tests pass, snapshot hash verified, spec emitted, `OK:` printed.

- [ ] **Step 4: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/scripts/verify.py backtest/reproduce.sh && git commit -m "chore(backtest): keyless reproducibility gate (reproduce.sh)"
```

---

### Task 10: Backtest README (honesty + how-to-repro)

**Files:**
- Create: `rotorvault/backtest/README.md`

- [ ] **Step 1: Write the README**

Cover, concisely: (1) what is proven — signal-gated FXRP exposure reduces drawdown vs XRP HODL (quote the numbers from Task 6); (2) the BACKTESTED (regime/momentum/vol-target/F&G on keyless Binance proxy for FTSO-priced XRP/BTC/ETH) vs LIVE-ONLY (FTSOv2 spot, venue APYs) split; (3) that RotorEdge (the engine) is pre-existing work and this subtree is the port; (4) `bash reproduce.sh` to reproduce.

- [ ] **Step 2: Commit**

```bash
cd f:/Hacks/rotorvault && git add backtest/README.md && git commit -m "docs(backtest): honesty split + reproduction guide"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** Plan 1 implements spec §5 (two-level strategy — Level-1 signal + Level-2 allocation overlay), §6 (backtest + `[BACKTESTED]`/`[LIVE-ONLY]` honesty split + StrategySpec + reproducibility). Spec §3/§4/§7-§9 (contracts, FTSO/FDC on-chain, agent, dashboard) are **out of scope for Plan 1** and are covered by Plans 2-5 (see overview note).
- **Placeholder scan:** every code step shows complete code; the only runtime-substituted values are the LIVE-ONLY APYs in `make_vault_spec.py` (explicitly a placeholder for Plan 3, labelled LIVE-ONLY) — this is correct, not a plan gap.
- **Type consistency:** `allocate(...)` returns `{"fxrp_exposure", "venue_allocation": {firelight, upshift, idle}}` in Task 7 and is consumed with those exact keys in Task 8's `make_vault_spec.py` and `build_vault_spec`. `hold_symbol` (config key) is written in Tasks 3/4/5 consistently. `build_vault_spec(as_of, cfg, exposure, regime_on, vault_overlay, oos_metrics, snapshot_sha256)` signature matches its call in `make_vault_spec.py`.
- **Assumptions to confirm during execution (not blockers):** exact loader name in `rotoredge/data.py` (`load_snapshot`), `_synth.py`'s constructor signature, and `run_backtest.py`'s CLI flag — each step notes the fallback ("match the real signature").

---

## Plans 2-5 overview (written after Plan 1 executes)

- **Plan 2 — Contracts (Foundry/Coston2):** `flare-foundry-starter` base; `RotorVault` ERC-4626-style FXRP vault + on-chain FTSO regime gate (ring-buffer price sampling) + `IYieldVenue` adapters for Firelight (delayed `claimWithdraw(period)`), Upshift (`requestRedeem`/`claim(y,m,d)`/`instantRedeem`), Idle, and Mock; FDC `verifyWeb2Json` APY consumer. **Fork-tested against the real Coston2 vaults** (`forge test --fork-url`), deployed + Blockscout-verified. First task = a smoke fork test reading `totalAssets` on the live Firelight vault to confirm the environment. Requires Foundry installed (user action) + Coston2 faucet funds for `--broadcast` (user).
- **Plan 3 — Agent driver (TS/viem):** RotorEdge signal → proposed weights; FDC request→proof→submit pipeline for the Upshift APY; venue/FTSO live client; `rebalance` dry-run plan builder (real signing = user). Depends on Plan 2 ABIs.
- **Plan 4 — Web dashboard (React/viem):** live NAV, allocation, FTSO feed + regime state, FDC-attested APYs, rebalance history, backtest equity vs baselines; LIVE + DEMO modes.
- **Plan 5 — Submission package:** README (architecture, Coston2 addresses, new-vs-preexisting separation, "building on Flare" note, roadmap), demo video script, pitch.
