# RotorVault — a self-driving, risk-managed FXRP yield vault on Flare

**Flare Summer Signal · Bounty 1 — Interoperable Asset Products**

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

## The proof (out-of-sample, 2021-06-30 → 2026-05-31)

The strategy's risk overlay was validated on a keyless, reproducible backtest. **It cuts XRP's worst
drawdown from −77.9% to −44.4% while keeping ~96% of the buy-and-hold return** — nearly doubling Calmar.

| Strategy | Sharpe | CAGR | max drawdown | Calmar |
|---|---|---|---|---|
| **RotorVault** | 0.47 | 13.1% | **−44.4%** | **0.29** |
| XRP buy & hold | 0.55 | 13.7% | −77.9% | 0.18 |
| XRP, no overlay (ablation) | 0.54 | 12.1% | −77.9% | 0.16 |

Honest framing: this is a **risk-management** win, not a higher-return claim — raw Sharpe is a hair below
HODL. Deflated Sharpe 0.89. Reproduce with zero API keys: `cd backtest && bash reproduce.sh`.

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

## Deployed contracts (Coston2, chainId 114)

Live on Coston2 ([explorer](https://coston2.testnet.flarescan.com/)):

| Contract | Address |
|---|---|
| **RotorVault** | [`0x6343119ee8F85bF8a85A47cad58d33e49601CfE6`](https://coston2.testnet.flarescan.com/address/0x6343119ee8F85bF8a85A47cad58d33e49601CfE6) |
| RegimeGate | [`0xe31906a2A7162b865b672a3a51B75813564db5e9`](https://coston2.testnet.flarescan.com/address/0xe31906a2A7162b865b672a3a51B75813564db5e9) |
| FirelightAdapter | [`0xCFd5E8e697A1956F063B9Bb71E9E33fd78F3d0ef`](https://coston2.testnet.flarescan.com/address/0xCFd5E8e697A1956F063B9Bb71E9E33fd78F3d0ef) |
| UpshiftAdapter | [`0x08F8b91A9d447C309F1788002BF51BF0BEE69021`](https://coston2.testnet.flarescan.com/address/0x08F8b91A9d447C309F1788002BF51BF0BEE69021) |
| ApyOracle | [`0xC45f8594579191b5125B24f721cA4e2f93811A8c`](https://coston2.testnet.flarescan.com/address/0xC45f8594579191b5125B24f721cA4e2f93811A8c) |

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
