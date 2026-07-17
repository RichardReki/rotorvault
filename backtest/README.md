# RotorVault — Backtest (signal proof)

This subtree proves the **signal** behind RotorVault, a risk-managed FXRP yield vault: sizing FXRP
exposure by a regime + volatility + sentiment overlay materially reduces drawdown versus holding XRP
outright. It is the keyless, reproducible core of the RotorVault submission for **Flare Summer Signal —
Bounty 1 (Interoperable Asset Products)**.

## What it is

RotorVault reuses the **RotorEdge** causal backtest engine (built earlier for the BNB Hack — *pre-existing
work*, see attribution below) and adapts it to a 3-asset (BTC / ETH / XRP) universe whose **held book is
XRP** (the FXRP proxy). Exposure to that book each day is gated by:

- a **regime switch** — BTC vs its 100-day moving average (risk-off ⇒ 0 exposure),
- a **volatility target** (35% annualized) on the XRP book,
- a **Fear & Greed** exposure scalar (trim in extreme greed).

The engine's daily gross-exposure output is exactly the FXRP exposure the live vault applies; a separate
**LIVE-ONLY** overlay (`rotoredge/vault.py`) then routes the deployed portion across yield venues
(Firelight / Upshift / idle) by live APY. That overlay is *not* backtested (see the honesty split).

## What is proven (out-of-sample, 2021-06-30 → 2026-05-31)

The out-of-sample window deliberately starts at the 2021 alt-market top — the hardest possible entry, not
a cherry-picked one. Same period and same cost model for every row.

| Strategy | Sharpe | CAGR | max drawdown | Calmar |
|---|---|---|---|---|
| **RotorVault (regime + vol-target + F&G)** | 0.474 | **13.1%** | **−44.4%** | **0.295** |
| XRP HODL | 0.553 | 13.7% | −77.9% | 0.176 |
| XRP full-exposure (no overlay) — ablation | 0.537 | 12.1% | −77.9% | — |
| BTC HODL | 0.549 | 16.2% | −76.6% | — |
| ETH HODL | 0.316 | −2.6% | −79.3% | — |

**Headline:** the risk overlay cuts XRP's max drawdown from **−77.9% to −44.4%** (a 43% reduction) while
keeping **~94% of the buy-and-hold total return** (CAGR 13.1% vs 13.7%) — improving Calmar 0.176→0.295
(~1.7×). The "no-overlay" ablation (XRP held at full exposure) shows the improvement comes from the risk
overlay, not from selection. Honestly: raw Sharpe is a hair lower than HODL — this is a
drawdown/risk-management win, not a higher-return claim. Because the held book is forced to XRP, the walk-forward's momentum-parameter grid does not change the result (all trials are identical), so there is no search-overfitting surface to deflate here — the risk-overlay parameters (vol target, Fear & Greed thresholds, regime MA) are frozen, not tuned on the out-of-sample window. (Deflated Sharpe Ratio 0.891 here reduces to the probability the Sharpe exceeds zero.)

## The honesty split (BACKTESTED vs LIVE-ONLY)

Every signal is labelled in the emitted spec (`results/rotorvault_spec.json`, `signal_labels`).

- **BACKTESTED** — regime gate, vol-adjusted momentum, vol-target, and Fear & Greed, computed on keyless
  historical daily OHLCV (Binance `data.binance.vision` as the reproducible **proxy** for the FTSOv2-priced
  assets XRP/BTC/ETH) + `alternative.me` Fear & Greed. The backtest reads only `data/snapshot/`.
- **LIVE-ONLY** — FTSOv2 spot prices (live NAV + on-chain regime sampling) and venue APYs (Upshift via
  FDC Web2Json; Firelight derived on-chain). These have no free history and are **never** mixed into the
  backtested numbers; they populate the spec's `vault_overlay` at runtime (Plan 3, the agent).

FTSOv2 is the live oracle; Binance daily OHLCV is only the historical *proxy* for the same assets, and
single-venue prices differ slightly from FTSOv2's cross-source aggregation. We disclose this rather than
present the proxy as the oracle.

## Reproduce (keyless, no API key)

```bash
cd backtest
python -m pip install -r requirements.txt
bash reproduce.sh
```

`reproduce.sh` runs the full test suite, re-runs the walk-forward from the committed snapshot and asserts
the OOS metrics + results-hash match `results/REFERENCE.json` byte-for-byte, then emits the StrategySpec.
To regenerate the full metrics/plots: `python scripts/run_backtest.py --config configs/rotorvault.yaml`.

## Attribution / new-vs-pre-existing

- **Pre-existing (RotorEdge, BNB Hack):** the causal backtest engine — `data.py`, `signals.py`,
  `backtest.py`, `metrics.py`, `walkforward.py`, `costs.py`, `report.py`, and the no-look-ahead /
  survivorship / cost / metrics tests. Ported here unchanged except where noted.
- **New for RotorVault (this hackathon):** the `hold_symbol` engine change (held book = XRP), the
  3-asset config + trimmed snapshot, the XRP-centric baselines, the **LIVE-ONLY venue-allocation overlay**
  (`rotoredge/vault.py`), and the RotorVault StrategySpec + emitter (`build_vault_spec`,
  `scripts/make_vault_spec.py`).

## Layout

```
backtest/
├── rotoredge/            ported engine + vault.py (new LIVE-ONLY overlay) + spec.py (new build_vault_spec)
├── configs/rotorvault.yaml   frozen 3-asset config (hold_symbol=XRP)
├── data/snapshot/        committed BTC/ETH/XRP + F&G + SHA-256 manifest
├── scripts/             run_backtest.py, make_vault_spec.py, build_snapshot.py, verify.py
├── tests/               engine tests (ported) + hold_symbol / baselines / vault_overlay / spec (new)
├── results/            committed metrics, REFERENCE.json, rotorvault_spec.json, plots
└── reproduce.sh        keyless PASS/FAIL gate
```

*Not financial advice. A backtestable research spec; the backtest does not place trades or custody funds.*
