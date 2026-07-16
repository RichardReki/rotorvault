# RotorVault — a self-driving, risk-managed FXRP yield vault on Flare

**Flare Summer Signal · Bounty 1 — Interoperable Asset Products**

**[▶ Live dashboard](https://richardreki.github.io/rotorvault/web/)** · **RotorVault on Coston2:**
[`0x6504…A99B`](https://coston2.testnet.flarescan.com/address/0x6504f672d60aB6864c5945E90b313e0D6dB3A99B)
· 63 tests green · keyless-reproducible backtest

An XRP holder wants on-chain yield but doesn't want to sit fully exposed through a crash and can't babysit
positions. Today's FXRP venues (Firelight, Upshift/earnXRP, MXRPY) are all *static, single-strategy*
products with **no market-aware risk management**. **RotorVault** sits on top of them: deposit FXRP once,
and the vault automatically routes it across those venues for yield — but the moment the on-chain
**FTSOv2** regime turns, it **pulls capital out of yield and back to safety**, trustlessly.

> The vault reads the oracle and turns the wheel. When the market is healthy it deploys FXRP to the
> highest-yielding venue; when the FTSO regime breaks it forces everything to idle. No one has to press a
> button.

## Why it's different

Not another yield vault — a **risk overlay** on the whole FXRP ecosystem, with the enshrined Flare
protocols as **load-bearing on-chain logic** (judges downgrade superficial usage; every protocol here does
real work):

| Protocol | What it does in RotorVault |
|---|---|
| **FTSOv2** | The `RegimeGate` samples the XRP/USD feed into an on-chain ring buffer, derives an SMA, and **vetoes** the allocation whenever price is below trend — forcing FXRP to idle regardless of what the off-chain agent proposes. FTSO *drives contract logic*, it isn't just displayed. |
| **FAssets / FXRP** | The asset flows through the real lifecycle: deposited, **actively deployed into the live Firelight & Upshift vaults**, and redeemed — verified on Coston2, not held passively. |
| **FDC (Web2Json)** | The live Upshift APY is brought on-chain via an FDC Web2Json attestation (`verifyWeb2Json`) so the yield-tilt reacts to real yields trustlessly. |

## The proof — the thesis, validated (out-of-sample 2021-06-30 → 2026-05-31)

A keyless, reproducible backtest validates the *thesis* behind the vault: gating FXRP exposure by a
market-regime signal roughly halves XRP's worst drawdown for about the same return. **It cuts XRP's
drawdown from −77.9% to −44.4% while keeping ~96% of the buy-and-hold return** — nearly doubling Calmar.

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
signal, not the v1 gate's own path**. The roadmap brings the full multi-factor signal on-chain
(agent-proposed, FTSO-verified). We flag this rather than let the number imply the contract runs it.
Reproduce with zero API keys: `cd backtest && bash reproduce.sh`.

## Architecture

```
FTSOv2 XRP/USD ──▶ RegimeGate (on-chain SMA gate, can veto)
                              │
Agent (TS/viem): signal ──▶ RotorVault.rebalance(wFirelight, wUpshift)
   │  reads on-chain state          │  (gate forces idle when risk-off)
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

# 2) contracts — unit tests + fork tests against the REAL Coston2 vaults
cd contracts && forge soldeer install && forge test --fork-url https://coston2-api.flare.network/ext/C/rpc
#   (deploy: forge script script/Deploy.s.sol --rpc-url coston2 --broadcast --private-key <key>)

# 3) agent — signal/allocation/FDC unit tests + offline FDC request
cd agent && npm install && npm test && npx tsx src/index.ts apy-request

# 4) dashboard — open web/index.html (DEMO), or paste deploy addresses for LIVE
```

**Tests: 63 green** (25 backtest · 23 contracts incl. live-fork · 15 agent).

## Hardening & rigor

Weaknesses we found and *fixed* rather than hid — the on-chain-trustless thesis taken seriously (v2):
- **FDC source-binding:** `ApyOracle.submitApy` rejects a valid Web2Json proof of any URL other than the
  bound Upshift API — permissionless but source-bound (closes an "anyone can set any APY" hole).
- **Continuous NAV:** `totalAssets()` counts in-flight (requested-but-unclaimed) redemptions, so a deposit
  mid-rebalance can't be mispriced or dilute holders (`test_inflightKeepsNavContinuous`).
- **Regime hysteresis:** the FTSO gate uses a deadband + sticky state, so it won't thrash multi-day async
  redemptions on price noise.
- **Net-of-fee valuation:** Upshift positions are valued after the withdrawal fee.

Operational: a keeper (`.github/workflows/keeper.yml`) samples the gate to accrue real on-chain regime
history; `contracts/scripts/live-cycle.sh` drives a real deposit + rebalance; `contracts/verify.sh`
source-verifies all five contracts on the explorer.

## Deployed contracts (Coston2, chainId 114)

Live on Coston2 ([explorer](https://coston2.testnet.flarescan.com/)):

| Contract | Address |
|---|---|
| **RotorVault** | [`0x6504f672d60aB6864c5945E90b313e0D6dB3A99B`](https://coston2.testnet.flarescan.com/address/0x6504f672d60aB6864c5945E90b313e0D6dB3A99B) |
| RegimeGate | [`0xc3762daB9AB246771a91B764d0E45f03619A61ea`](https://coston2.testnet.flarescan.com/address/0xc3762daB9AB246771a91B764d0E45f03619A61ea) |
| FirelightAdapter | [`0x44F388C71EE257bD7CF12AcEde1a3b084c0fBc53`](https://coston2.testnet.flarescan.com/address/0x44F388C71EE257bD7CF12AcEde1a3b084c0fBc53) |
| UpshiftAdapter | [`0xA595C95964efaec78D85Ad18D38a05004440Bbb2`](https://coston2.testnet.flarescan.com/address/0xA595C95964efaec78D85Ad18D38a05004440Bbb2) |
| ApyOracle | [`0xD3103fb1189a6f21C72387efab1c77aaF79803cF`](https://coston2.testnet.flarescan.com/address/0xD3103fb1189a6f21C72387efab1c77aaF79803cF) |

FXRP resolved at runtime via `FlareContractRegistry` (`0xaD67…6019`) → `AssetManagerFXRP.fAsset()` =
`0x0b6A3645…dc7`. Deployed from `0x66F9Bd73c4847584f158c8D19EEd179F21adC169`.

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
