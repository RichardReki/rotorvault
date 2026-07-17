# RotorVault — a self-driving, risk-managed FXRP yield vault on Flare

**Flare Summer Signal · Bounty 1 — Interoperable Asset Products**

**[▶ Live dashboard](https://richardreki.github.io/rotorvault/web/)** · **RotorVault on Coston2:**
[`0x8C7F…4831`](https://coston2.testnet.flarescan.com/address/0x8C7FF254D4723186f660DdFB0EaF084cb7654831)
· 68 tests green · keyless-reproducible backtest

An XRP holder wants on-chain yield but doesn't want to sit fully exposed through a crash and can't babysit
positions. Today's FXRP venues (Firelight, Upshift/earnXRP, MXRPY) are all *static, single-strategy*
products with **no market-aware risk management**. **RotorVault** sits on top of them: deposit FXRP once,
and an off-chain agent proposes how to route it across those venues for yield — but every allocation must
clear an on-chain **FTSOv2** gate, and the moment the regime turns that gate **forces capital out of yield
and back to idle**. That de-risk veto is the trustless part: it's enforced in the contract, not promised.

> An agent proposes the allocation and a keeper submits it; the on-chain FTSO gate decides whether it's
> allowed. Healthy market → the gate lets FXRP flow to the highest-yielding venue. FTSO regime breaks → the
> gate vetoes the allocation and forces everything to idle, and no operator can override it.

## Why it's different

Not another yield vault — a **risk overlay** on the whole FXRP ecosystem, with the enshrined Flare
protocols as **load-bearing on-chain logic** (judges downgrade superficial usage; every protocol here does
real work):

| Protocol | What it does in RotorVault |
|---|---|
| **FTSOv2** | The `RegimeGate` samples the XRP/USD feed into an on-chain ring buffer, derives an SMA, and **vetoes** the allocation whenever price is below trend — forcing FXRP to idle regardless of what the off-chain agent proposes. FTSO *drives contract logic*, it isn't just displayed. |
| **FAssets / FXRP** | FXRP is a first-class asset here: **deposited live on Coston2**, with the full deposit→deploy→redeem lifecycle into the real Firelight & Upshift vaults **fork-verified against live vault state**. The live v1 deposit currently sits **idle by design** — the on-chain FTSO gate is risk-off (buffer still warming), so no FXRP is deployed until the regime permits it. |
| **FDC (Web2Json)** | The live Upshift APY is brought on-chain **trustlessly** (`ApyOracle.submitApy` runs `verifyWeb2Json` + a source-URL binding before storing it) **and consumed on-chain**: `RotorVault.rebalance()` reads `apy()`/`updatedAt()`, and a zero or stale attested APY forces the Upshift venue to idle. The FDC value *gates capital*, it isn't just stored. **Live on Coston2** — `ApyOracle.apy()` = **800 bips (8.00%)**. Proof txs below. |

## The proof — the thesis, validated (out-of-sample 2021-06-30 → 2026-05-31)

A keyless, reproducible backtest validates the *thesis* behind the vault: gating FXRP exposure by a
market-regime signal roughly halves XRP's worst drawdown for about the same return. **It cuts XRP's
drawdown from −77.9% to −44.4% while keeping ~94% of the buy-and-hold return** — improving Calmar from
0.18 to 0.29 (~1.6× vs HODL, ~1.8× vs the no-overlay ablation).

| Strategy | Sharpe | CAGR | max drawdown | Calmar |
|---|---|---|---|---|
| **RotorVault (regime overlay)** | 0.47 | 13.1% | **−44.4%** | **0.29** |
| XRP buy & hold | 0.55 | 13.7% | −77.9% | 0.18 |
| XRP, no overlay (ablation) | 0.54 | 12.1% | −77.9% | 0.16 |

**Backtest vs on-chain — read this.** The table validates the overlay on RotorEdge's multi-factor signal
(BTC-vs-100d-MA regime + volatility targeting + Fear & Greed, on keyless daily data): it proves the
*thesis* — a risk-management win, not a higher-return claim (raw Sharpe a hair below HODL; Deflated Sharpe
0.89). The **deployed v1 contract** ships a deliberately *minimal, fully-trustless* version of that
thesis — an FTSOv2 SMA gate computed entirely on-chain — so the −44.4% figure describes the **research
signal, not the v1 gate's own path**. Concretely, the deployed gate is a short-horizon ~100-minute SMA
(20 samples × 5-min floor): an intraday trend filter, a deliberately different timescale from the
multi-day research regime. The roadmap brings the full multi-factor signal on-chain
(agent-proposed, FTSO-verified). We flag this rather than let the number imply the contract runs it.
Reproduce with zero API keys: `cd backtest && bash reproduce.sh`.

## Architecture

```
FTSOv2 XRP/USD ──▶ RegimeGate (on-chain SMA gate, can veto)
                              │
Agent (TS/viem): signal ──▶ RotorVault.rebalance(wFirelight, wUpshift)
   │  reads on-chain state          │  (gate forces idle risk-off; stale/zero APY idles Upshift)
   │  computes allocation           ├─▶ FirelightAdapter ─▶ Firelight (live Coston2 vault)
   │  FDC Web2Json ─▶ ApyOracle     └─▶ UpshiftAdapter   ─▶ Upshift  (live Coston2 vault)
   └─ dry-run by default; real signing is the user's        (remainder stays idle)
```

- `backtest/` — the strategy proof (Python). Ports the **RotorEdge** engine; keyless & reproducible.
- `contracts/` — Foundry / Coston2. `RotorVault`, `RegimeGate`, `FirelightAdapter`, `UpshiftAdapter`,
  `ApyOracle`, `MockVenue`/`IdleVenue`, `Deploy.s.sol`. **Fork-tested against the real live vaults.**
- `agent/` — TS/viem driver: signal → rebalance plan (dry-run) + FDC Web2Json APY pipeline.
- `web/` — a self-contained dashboard (product face + backtest proof).

## What's new vs pre-existing (required disclosure)

- **Pre-existing** (RotorEdge, our BNB Hack entry): the causal backtest engine — momentum/regime signals,
  walk-forward, metrics, no-look-ahead tests. Ported into `backtest/` and clearly attributed.
- **Newly built for this hackathon (everything Flare):** all of `contracts/` (the vault, the FTSO regime
  gate, the Firelight/Upshift adapters over the real vaults, the FDC ApyOracle), all of `agent/` (signal →
  gated rebalance + FDC Web2Json pipeline), the `web/` dashboard, and the backtest's FXRP/venue overlay
  (`vault.py`, `build_vault_spec`).

## Run it

```bash
# 1) strategy proof — keyless, deterministic
cd backtest && python -m pip install -r requirements.txt && bash reproduce.sh

# 2) contracts — unit tests + fork tests against the REAL Coston2 vaults (no secrets; public RPC is the default)
cd contracts && forge soldeer install && forge test
#   (deploy: forge script script/Deploy.s.sol --rpc-url coston2 --broadcast --private-key <key>)

# 3) agent — signal/allocation/FDC unit tests + offline FDC request
cd agent && npm install && npm test && npx tsx src/index.ts apy-request

# 4) dashboard — open web/index.html (DEMO), or paste deploy addresses for LIVE
```

**Tests: 68 green** (25 backtest · 28 contracts incl. live-fork · 15 agent).

## Hardening & rigor

Weaknesses we found and *fixed* rather than hid — the on-chain-trustless thesis taken seriously (v2):
- **FDC source-binding:** `ApyOracle.submitApy` rejects a valid Web2Json proof of any URL other than the
  bound Upshift API — permissionless but source-bound (closes an "anyone can set any APY" hole).
- **FDC is load-bearing, not decorative:** `RotorVault.rebalance()` reads `ApyOracle.apy()`/`updatedAt()`
  on-chain; a zero or >30-day-stale attested APY forces the Upshift venue idle (`test_staleApyForcesUpshiftIdle`).
- **Continuous NAV:** `totalAssets()` counts in-flight (requested-but-unclaimed) redemptions, so a deposit
  mid-rebalance can't be mispriced or dilute holders (`test_inflightKeepsNavContinuous`).
- **Regime hysteresis:** the FTSO gate uses a deadband + sticky state, so it won't thrash multi-day async
  redemptions on price noise.
- **Net-of-fee valuation:** Upshift positions are valued after the withdrawal fee.

Operational: a keeper (`.github/workflows/keeper.yml`) samples the gate to accrue real on-chain regime
history; `contracts/scripts/live-cycle.sh` drives a real deposit + rebalance; `contracts/verify.sh`
source-verifies all five contracts on the explorer.

## Deployed contracts (Coston2, chainId 114)

Live + **source-verified** on Coston2 ([Blockscout](https://coston2-explorer.flare.network/address/0x8C7FF254D4723186f660DdFB0EaF084cb7654831?tab=contract)):

| Contract | Address |
|---|---|
| **RotorVault** | [`0x8C7FF254D4723186f660DdFB0EaF084cb7654831`](https://coston2.testnet.flarescan.com/address/0x8C7FF254D4723186f660DdFB0EaF084cb7654831) |
| RegimeGate | [`0xc3762daB9AB246771a91B764d0E45f03619A61ea`](https://coston2.testnet.flarescan.com/address/0xc3762daB9AB246771a91B764d0E45f03619A61ea) |
| FirelightAdapter | [`0x256b037EEF65aAb98C9CBc4b39866fc643E523b7`](https://coston2.testnet.flarescan.com/address/0x256b037EEF65aAb98C9CBc4b39866fc643E523b7) |
| UpshiftAdapter | [`0xb31a17B2B8B17f9bb8b8494B1BcC59a4b8CAe446`](https://coston2.testnet.flarescan.com/address/0xb31a17B2B8B17f9bb8b8494B1BcC59a4b8CAe446) |
| ApyOracle | [`0xD3103fb1189a6f21C72387efab1c77aaF79803cF`](https://coston2.testnet.flarescan.com/address/0xD3103fb1189a6f21C72387efab1c77aaF79803cF) |

FXRP resolved at runtime via `FlareContractRegistry` (`0xaD67…6019`) → `AssetManagerFXRP.fAsset()` =
`0x0b6A3645…dc7`. Deployed from `0x66F9Bd73c4847584f158c8D19EEd179F21adC169`.

**FTSOv2 veto — live on-chain proof.** With the gate risk-off, the agent proposed `rebalance(4000, 4000)`
(40% Firelight / 40% Upshift) and the on-chain gate forced everything to idle — the emitted
`Rebalanced(0, 0, false, 5000000)` (input `4000/4000` → output `0/0`, all 5 FXRP still idle) proves the
veto is enforced in the contract, not promised:

| Step | Tx |
|---|---|
| `deposit` 5 FXRP | [`0x07996cba…29cdcef40`](https://coston2.testnet.flarescan.com/tx/0x07996cbabc697e82ac7cdbfffa636e53ef48d6da6cbe3a386f6457129cdcef40) |
| `setAgent` | [`0x671549ec…ffe03bd7`](https://coston2.testnet.flarescan.com/tx/0x671549eca58ed1e78f04a0c750cfc8f44ab73c13e6346e1e03efdcf5ffe03bd7) |
| `rebalance(4000,4000)` → `Rebalanced(0,0,false)` | [`0x6cb9c76a…a4ee8e7f`](https://coston2.testnet.flarescan.com/tx/0x6cb9c76a5f34918d07ee48893b8f358870aa5e4ac5a41e187b1ec3e7a4ee8e7f) |

**FDC Web2Json — live on-chain proof.** The Upshift APY is attested end-to-end, stored trustlessly in
`ApyOracle` (`apy()` = **800 bips / 8.00%**), and read on-chain by `RotorVault.rebalance()` — verify the round-trip on Coston2:

| Step | Tx |
|---|---|
| `requestAttestation` (FdcHub · Web2Json → Upshift API) | [`0xc36636ed…3518869b`](https://coston2.testnet.flarescan.com/tx/0xc36636ed77d644ff1d6199b09569a3079cf5a6e2cce2ccb278d32a9b3518869b) |
| `submitApy` (on-chain `verifyWeb2Json` + URL binding) | [`0x4bd66431…21189a1a`](https://coston2.testnet.flarescan.com/tx/0x4bd6643169909b9ab2b259633c06575506d9455d55f2610351b718cc21189a1a) |

Reproduce the whole round-trip yourself: `cd contracts && bash scripts/fdc-run.sh` (the round-probing
handles FDC's next-round assignment automatically).

## Roadmap

- Multi-FAsset rotation (FBTC / FDOGE) once live — the cross-sectional engine is already built for it.
- More venues (MXRPY / earnXRP) behind the same `IYieldVenue` adapter interface.
- Cross-chain deposits via the FXRP LayerZero OFT; gasless UX via the EIP-712 forwarder.
- Mainnet deployment with governance-whitelisted FDC sources.

## Building on Flare — feedback

FAssets + the enshrined data protocols make a "read-the-oracle, act-on-chain" product genuinely trustless.
Rough edges we hit (documented in-repo): FXRP resists `deal()` (FAsset proxy accounting) so fork tests
impersonate a holder; Firelight records a redeem in period *P+1*; Upshift instant-redeem needs idle
liquidity and requested-claim needs operator epoch-fulfillment; the FDC jq subset disallows `floor`/`round`.

*Not financial advice. Testnet only; the backtest does not place trades or custody funds.*
