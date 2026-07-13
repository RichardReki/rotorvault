# RotorVault — Design Spec

**Date:** 2026-07-14
**Target:** Flare Summer Signal (DoraHacks, Flare org #3103) — **Bounty 1: Interoperable Asset Products**. $6,000 pool (1st $4,000 / 2nd $2,000).
**Deadline:** ~2026-08-14 ~23:59 UTC (VERIFY logged-in; DoraHacks blocks scraping — see §12). Judging Aug 15–21, winners Aug 24.
**Lineage:** ports the **RotorEdge** signal engine (BNB Hack, Track 2 — pre-existing work) onto Flare as a new product. Working name `RotorVault` (placeholder, renameable).

## 0. One-liner

**A self-driving, risk-managed FXRP yield vault.** Deposit FXRP once; the vault automatically rotates capital across the *existing* Flare yield venues (Firelight, Upshift) and idle, steered by a cross-sectional momentum + regime signal that is **consumed on-chain from FTSOv2** and gated by an on-chain risk switch — leaning into yield when risk-on, pulling back to safe/idle when risk-off. Live venue APYs enter the allocation on-chain via **FDC Web2Json**. FXRP flows through the real FAssets lifecycle. Deployed and demonstrated on Coston2 against **real** Firelight/Upshift vaults.

## 1. Why this wins (positioning → the 5 judging criteria)

The field is wide open: as of 2026-07-14 there were ~150 registered hackers and **0 submitted BUIDLs**. The research is blunt that superficial Flare usage is an *explicit scoring downgrade*, and that every cited winner made an enshrined protocol **functionally central and consumed on-chain**, tied to a concrete problem. RotorVault is built to hit all five criteria:

1. **Product usefulness** — a real, unserved need: XRP holders want yield but don't want to sit fully exposed through a downturn and can't babysit positions. Incumbents (Firelight liquid-staking, Upshift/earnXRP, Monarq MXRPY) are all *static, single-strategy* products with **no market-aware risk management**. RotorVault is a meta-vault/router *on top of them* with an on-chain regime gate.
2. **Flare integration quality (meaningful, not superficial)** — three enshrined protocols are load-bearing (§4): FTSOv2 drives on-chain valuation + a regime gate that can *override* allocation; FAssets/FXRP is actively deployed/redeemed (not held passively); FDC Web2Json pulls live APYs on-chain.
3. **Technical execution** — deployed on Coston2 interacting with the **real** Firelight (`0x91Bfe6…`) and Upshift (`0x24c1a47c…`) testnet vaults, not mocks; a reproducible, keyless backtest proving the signal; a working dashboard + demo.
4. **Evidence of new work** — RotorEdge (the momentum engine, from the BNB Hack) is pre-existing and clearly separated. New in this hackathon: the `RotorVault` contract + on-chain FTSO regime gate, venue adapters, the FDC-APY integration, the yield-allocation overlay, the agent driver, and the dashboard.
5. **Clarity & future potential** — explicit new-vs-preexisting section, a "building on Flare" feedback note, and a roadmap (FBTC/FDOGE multi-asset once live, more venues, OFT cross-chain deposits, gasless UX, mainnet).

## 2. Product concept

- **User & problem:** an XRP holder (or a treasury) that wants competitive on-chain yield on XRP but also wants automatic de-risking in downturns, without active management.
- **What it does:** one FXRP deposit → the vault holds an ERC-20 share; on a schedule (or event) it rebalances FXRP across `{Firelight, Upshift, idle}` per a signal. Risk-on & strong → tilt to higher-yield/instant-redeem venue; risk-off → pull to the safest/delayed venue or idle cash.
- **Differentiation:** the incumbents give you *one* strategy and no risk overlay. RotorVault sits above them and adds (a) market-aware rotation and (b) a trustless on-chain regime gate. This is the "interoperable asset product" the bounty asks for: it composes the FXRP ecosystem rather than re-skinning one venue.

## 3. Architecture

```
User (deposit FXRP / web dashboard)
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│  Off-chain Agent driver (TypeScript, RotorEdge signal)          │
│  compute signal → request FDC APY proof → propose weights →     │
│  call RotorVault.rebalance(...)   (dry-run default; real = user) │
└───────────────┬─────────────────────────────────────────────────┘
                │ viem (EVM, off-chain)
                ▼
┌───────────────────────────────────────────────────────────────┐
│  RotorVault.sol  (Coston2, chainId 114)                          │
│  • ERC-4626-style FXRP vault (shares)                            │
│  • reads FTSOv2 feeds → NAV(USD) + ON-CHAIN regime gate          │
│  • verifies FDC Web2Json APY proof → yield-factor                │
│  • rebalance() routes FXRP across venue adapters within          │
│    FTSO-gated bounds (gate can override to risk-off)             │
└───┬───────────────┬───────────────────┬────────────────────────┘
    │ IYieldVenue    │ IYieldVenue       │ reads
    ▼                ▼                   ▼
 Firelight       Upshift             FTSOv2 / FDCVerification
 (real Coston2)  (real Coston2)      (resolved via FlareContractRegistry)
    └─ MockVenue (our ERC-4626) as fallback if real testnet vaults are flaky ─┘
```

**Component layout (mirrors the shipped RangeClaw shape):**

```
rotorvault/
├── contracts/                 # Foundry, Solidity 0.8.25 (evmVersion cancun)
│   ├── src/RotorVault.sol      # the vault: FXRP shares + FTSO gate + FDC APY + rebalance
│   ├── src/venues/IYieldVenue.sol
│   ├── src/venues/{FirelightAdapter,UpshiftAdapter,IdleVenue,MockVenue}.sol
│   ├── src/lib/{FeedIds,RegimeGate}.sol
│   ├── test/                   # unit + fuzz (no-lookahead of gate math, adapter accounting)
│   └── script/Deploy.s.sol
├── agent/                     # TypeScript strategy driver
│   ├── signal (RotorEdge → venue weights), fdc (request/proof APY), attest/execute (viem)
│   └── Mock/Cli venue-status clients + dry-run plan builder
├── backtest/                  # RotorEdge port (Python) — proves the SIGNAL, keyless
├── web/                       # React + viem dashboard
├── docs/                      # README, architecture, demo-script, pitch, superpowers/specs
└── data/snapshot/             # committed keyless OHLCV + manifest (backtest input)
```

**Hard rule — resolve every Flare address at runtime.** `FlareContractRegistry` is at `0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019` on every Flare network. Resolve `AssetManagerFXRP → getSettings().fAsset` for FXRP, `getFtsoV2()`, `getFdcVerification()` from the registry. **Never hardcode FXRP** (genuine FXRP has 6 decimals; a suspect 18-decimal "fXRP" exists — see §12/§14).

## 4. The three enshrined protocols — how each is load-bearing

### 4.1 FTSOv2 (prices → NAV + on-chain regime gate)
- On each rebalance the contract reads block-latency feeds (`~1.8s`) via `ContractRegistry.getFtsoV2().getFeedById(bytes21)` → `(uint256 value, int8 decimals, uint64 timestamp)`. **Decimals are read per-call, never hardcoded.** Fee is currently 0 but computed via `IFeeCalculator.calculateFeeById` for robustness. `TestFtsoV2Interface` (all `view`) used in local tests.
- **NAV:** book value in USD = FXRP holdings + venue positions valued at the XRP/USD feed. Drives share price.
- **Regime gate (the load-bearing part):** the contract stores periodic XRP/USD (and cross-asset) samples, derives a trailing MA + momentum/breadth on-chain, and maintains a `riskOn/riskOff` state. When risk-off, `rebalance` is **forced** to the safe/idle allocation regardless of the agent's proposed weights — FTSO can *veto*, not merely display. This is the anti-"superficial" design.
- Feed IDs (bytes21): XRP/USD `0x015852502f55534400000000000000000000000000`, FLR/USD `0x01464c522f55534400000000000000000000000000`, BTC/USD `0x014254432f55534400000000000000000000000000`, ETH/USD `0x014554482f55534400000000000000000000000000`.

### 4.2 FAssets / FXRP (the asset through the full lifecycle)
- FXRP (ERC-20, 6 decimals, resolved at runtime) is deposited, **actively deployed** into Firelight/Upshift, and redeemed back — exercising deposit→use→redeem, not passive holding.
- Test FXRP obtained from the Coston2 faucet (dispenses C2FLR + FXRP + USDT0 directly; no mint flow needed). Standard/direct mint via FDC Payment is **out of core scope** (roadmap/stretch) since the faucet suffices — keeps scope focused.

### 4.3 FDC — Web2Json (live APYs → on-chain yield-factor)
- The yield-factor in the allocation consumes **live venue APYs** brought on-chain via **FDC Web2Json** (fetch an off-chain yield JSON API, JQ-transform, ABI-encode). Flow: `FdcHub.requestAttestation` → DA-layer proof (`/api/v0/fdc/get-proof-round-id-bytes`) → contract verifies via `ContractRegistry.getFdcVerification().verify…(proof)` → APY drives the allocation.
- Makes the allocation react to *real* yields trustlessly, and ties FTSO + FAssets + FDC into one coherent story rather than three bolt-ons.
- **Open item (resolve in planning):** the exact public APY endpoint (protocol status APIs vs a yield aggregator). If no clean endpoint exists, fall back to deriving venue yield on-chain from ERC-4626 `convertToAssets` deltas over time and reserve FDC Web2Json for a related off-chain datum (still load-bearing). See §12.

## 5. Strategy logic (two-level)

**Level 1 — Signal (RotorEdge engine reused):** cross-sectional, vol-adjusted trailing momentum over the FTSO-priced universe (XRP, BTC, ETH, FLR), plus a BTC-style regime gate and a breadth/exposure scalar. Output: `riskOn/off`, an exposure scalar in `[floor, 1]`, and XRP relative strength. All features causal (computed on closed samples, shifted ≥1 period).

**Level 2 — Allocation:** map `(signal, live APYs)` → target weights over `{Firelight, Upshift, idle}`:
- risk-off → 100% safe/idle (or the delayed-redeem venue), exposure scaled down;
- risk-on → tilt toward the higher risk-adjusted APY venue, size by exposure scalar;
- turnover deadband to avoid churn/fees (Upshift instant-redeem carries ~1.0% fee, requested ~0.5%).

The agent proposes weights; the contract accepts them only within FTSO-gated bounds (gate can force risk-off).

## 6. Backtest & the honesty split (RotorEdge's DNA)

Same discipline that made RotorEdge credible. Every signal is labeled.

- **`[BACKTESTED]` — the momentum + regime/exposure signal**, on keyless historical daily OHLCV (Binance `data.binance.vision`, checksum-verified) for XRP/BTC/ETH (FLR history sourcing is an open item — see §12; FLR may be live-only). The causal engine, walk-forward (anchored, train/validate/test-once), metrics (Sharpe/Sortino/Calmar/maxDD+dur/CAGR/turnover/DSR), and baselines (XRP HODL, always-in-vault) all port from RotorEdge. **Claim we prove:** the regime/exposure gate reduces drawdown vs an always-fully-exposed FXRP position.
- **`[LIVE-ONLY]` — the yield/APY overlay and the actual venue routing.** No free history exists for Flare vault yields, so — exactly like RotorEdge's CMC layer — this is demonstrated live on Coston2 and its historical value is **not** claimed. No fabricated history.
- Emits a **StrategySpec JSON** (the machine-readable IR), reproducible via one command reading only the committed snapshot, asserting a results hash.

## 7. Contracts design

- **`RotorVault.sol`** — ERC-4626-style FXRP vault (shares); `deposit/withdraw`; `rebalance(weights, apyProof)`; reads FTSOv2 for NAV + regime; verifies FDC APY proof; routes via adapters; `owner`/`agent` roles (agent may only `rebalance` within gated bounds); pausable; no custody of keys.
- **`IYieldVenue`** — uniform adapter interface (`deposit`, `requestWithdraw`/`withdraw`, `positionValue`, `apySource`) so the vault is agnostic to venue mechanics.
  - `FirelightAdapter` — ERC-4626 period-based: `deposit/mint`, `redeem`→request, `claimWithdraw(period)`. (Coston2 `0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B`.)
  - `UpshiftAdapter` — `deposit`, `instantRedeem` (higher fee) vs `requestRedeem`+`claim(y,m,d)` (lower fee, ~1-day lag). (Coston2 `0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81`.)
  - `IdleVenue` — holds FXRP, zero yield, instant.
  - `MockVenue` — our own minimal ERC-4626, **fallback only** if the real testnet vaults are unreliable; the demo prefers real venues.
- **Tests (Foundry):** regime-gate math (monotonic, no-lookahead on stored samples), adapter accounting, NAV/share correctness, access control, fuzz on weights. (Note: local `forge` availability to be confirmed on this machine — RangeClaw hit this; plan for review + human verification if `forge` isn't runnable locally.)

## 8. Agent driver (TypeScript)

Monitor (venue status via ERC-4626 reads / protocol clients, Mock + Cli variants) → compute RotorEdge signal → request FDC APY attestation + fetch proof → build a `rebalance` plan → **dry-run by default**; real signing/broadcast is the user's (see §13). Mirrors RangeClaw's `Mock/Cli` client + `buildExecutionPlan` + gated-write pattern.

## 9. Dashboard (React + viem)

Live NAV & share price, current allocation across venues, FTSOv2 feed panel + regime state (risk-on/off with the MA), FDC-attested APYs (with proof/verify indicator), rebalance history, and the backtest equity vs baselines + StrategySpec. LIVE reads the deployed vault; a DEMO mode (real-computed mock) works with no deployment — same graceful fallback as RangeClaw.

## 10. Deliverables ↔ judging

- Deployed & (optionally) verified contracts on **Coston2**, addresses in README; runtime address resolution demonstrated.
- Reproducible keyless backtest + StrategySpec (`[BACKTESTED]`/`[LIVE-ONLY]` labels).
- Working dashboard (LIVE + DEMO).
- README with: architecture, "how it uses Flare" (the §4 three-protocol story), an explicit **new-vs-preexisting** section, a "building on Flare" feedback note, and a roadmap.
- ~2 min demo video (script): problem → live FTSO regime flip forcing risk-off → real venue rotation on Coston2 → backtest drawdown reduction → FDC APY proof verify.

## 11. Scope & must-ship order

Solo, ~1 month, empty field. Always keep a submittable artifact:
1. **Backtest port + StrategySpec** (fastest credible core; reuses RotorEdge). 
2. **`RotorVault` + FTSO regime gate + one real venue adapter**, deployed to Coston2. 
3. **Agent driver (dry-run) + second venue + FDC-APY** integration. 
4. **Dashboard**. 
5. **README / new-work separation / demo video / pitch.**
Fallbacks if tight: MockVenue instead of a flaky real venue; APY-from-ERC4626-deltas instead of Web2Json; single venue + idle; dashboard before video.

## 12. Risks & mitigations

- **DoraHacks provenance** — all event facts came via a proxy (DoraHacks blocks scrapers); no independent Flare press corroboration. → *User verifies the event page logged in; confirm exact deadline/timezone before relying to the minute.*
- **APY data source for FDC Web2Json** unconfirmed — a clean public APY endpoint for Firelight/Upshift may not exist. → *Planning phase confirms the endpoint; fallback = on-chain ERC-4626 yield deltas + FDC used for a related off-chain datum.*
- **Real testnet vault reliability** (deposit/redeem may be flaky or ABI-shifted). → *`IYieldVenue` abstraction + `MockVenue` fallback; verify real ABIs on Coston2 first.*
- **Address/decimals traps** — FXRP address differs per network and a suspect 18-decimal token exists. → *Resolve via `AssetManager.fAsset()` at runtime; read decimals from the token; read `getSettings()` on the target network (params differ mainnet vs Coston2).*
- **FDC Web2Json complexity** (JQ transform, ABI encoding, DA-layer proof timing ~90–180s). → *Prototype the attestation round early; it's on the critical path.*
- **Backtest framing honesty** — the vault asset is XRP-centric, so the cross-sectional story is thinner than RotorEdge's alt universe. → *Frame as cross-sectional breadth/regime → FXRP exposure gate; prove drawdown reduction, not alpha; keep `[LIVE-ONLY]` labels strict.*
- **FLR historical data** for the backtest may lack a keyless source. → *Use XRP/BTC/ETH (Binance keyless) for the backtested signal; treat FLR as a live FTSO input only.*
- **Scope** for a solo month. → *Must-ship order (§11); each step yields a submittable artifact.*
- **x402/EIP-3009 for FXRP does NOT work yet** (token lacks `transferWithAuthorization`). → *Excluded; gasless UX via `GaslessPaymentForwarder`/OFT is roadmap only.*
- **Phishing note in memory pertains to a DIFFERENT event (BNB RotorEdge), not Flare** — do not conflate; route all Flare claims through the verified DoraHacks page.

## 13. Standing rules / user-only blocking actions (Claude does NOT do these)

Carried over from RangeClaw's CLAUDE.md §7:
- ❌ Never touch/generate/store private keys, seeds, or wallet credentials.
- ❌ Never execute real-fund on-chain txs. Everything is **Coston2 testnet** (no real funds).
- ❌ Coston2 contract **deploy signing/broadcast** is the user's (Claude prepares scripts).
- ❌ DoraHacks registration + final BUIDL submission are the user's.
- ✅ Testnet private key (if needed) lives in `.env` (gitignored), filled by the user.
- ✅ Any real venue `--confirm`/write is user-reviewed; Claude defaults to dry-run.

## 14. Key facts reference (from grounding research — verify at runtime)

| Item | Value | Confidence / note |
|---|---|---|
| FlareContractRegistry (all nets) | `0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019` | high |
| Coston2 | chainId 114, RPC `https://coston2-api.flare.network/ext/C/rpc`, faucet `faucet.flare.network/coston2` | high |
| FXRP (Coston2) | `0x0b6A3645c240605887a5532109323A3E12273dc7`, name FTestXRP, 6 decimals | **resolve via `AssetManager.fAsset()`** |
| Firelight vault (Coston2) | `0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B` | medium (dev-hub example) |
| Upshift FXRP vault (Coston2) | `0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81` | high (dev-hub) |
| FXRP OFT adapter (Coston2) | `0xCd3d2127935Ae82Af54Fc31cCD9D3440dbF46639` | high (roadmap only) |
| Toolchain | Solidity 0.8.25, evmVersion cancun, `flare-hardhat-starter`/`flare-foundry-starter`, `@flarenetwork/flare-periphery-contracts` | high |
| FTSOv2 read | `ContractRegistry.getFtsoV2().getFeedById(bytes21)` → `(value, int8 decimals, uint64 ts)`; payable, fee 0 now | high |
| FDC verify | `ContractRegistry.getFdcVerification().verify…(proof)`; request via `FdcHub.requestAttestation`; proof from DA layer | high |
| Suspect token | 18-decimal "fXRP" `0xAf7278D3…` — do NOT use | do-not-use |

---

*Pre-existing (not new work for this hackathon): the RotorEdge signal engine (momentum, causal backtest, walk-forward, metrics) from the BNB Hack. Everything Flare-specific in this spec is new work.*
