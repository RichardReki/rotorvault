# RotorVault — Agent (TS/viem)

The off-chain driver for RotorVault: it reads the live on-chain state, computes a proposed FXRP venue
allocation with the **same `allocate()` logic as the backtest** (parity-tested), builds a `rebalance`
plan (**dry-run by default**), and runs the **FDC Web2Json → ApyOracle** pipeline to bring the Upshift
APY on-chain.

## Setup

```bash
cd agent
npm install
cp .env.example .env     # fill COSTON2_RPC_URL + the Plan 2 deploy addresses
```

## Commands

```bash
npm test                                   # allocate/signal/rebalance/fdc unit tests
node --env-file=.env node_modules/.bin/tsx src/index.ts apy-request   # print the FDC Web2Json request (offline)
node --env-file=.env node_modules/.bin/tsx src/index.ts state         # print live on-chain reads (needs addresses)
node --env-file=.env node_modules/.bin/tsx src/index.ts plan          # propose weights + dry-run simulate the rebalance
```

## Safety model (dry-run by default)

- The agent **never broadcasts** unless BOTH `ENABLE_ONCHAIN_WRITE=true` **and** `AGENT_PRIVATE_KEY` are
  set in `.env`. `rebalance.ts::execute` is the single choke point and throws otherwise.
- Claude/the agent never generates or handles a private key. Real signing/broadcasting is the user's.
- `state`/`plan` are read-only; `plan` simulates the rebalance as the on-chain agent (no key needed).

## How the signal maps to the vault

1. `readState` reads `RegimeGate.riskOn()` (the FTSOv2-driven gate), `ApyOracle.apy()` (Upshift APY via
   FDC), vault NAV, and each venue's `positionValue()`.
2. `proposeWeights` sets exposure = 1 when risk-on else 0 (the gate can veto), then splits the deployed
   portion across venues by live APY via `allocate()` — the identical overlay the backtest validates.
3. `buildPlan` simulates `RotorVault.rebalance(wFirelight, wUpshift)`; `execute` broadcasts only when armed.

## FDC Web2Json (Upshift APY on-chain)

`fdc.ts` builds the Web2Json attestation request for `api.upshift.finance` (mainnet earnXRP), scaling
`reported_apy.apy` to integer basis points with a jq filter that avoids the disallowed `floor`/`round`
builtins. The live round-trip (verifier `prepareRequest` → `FdcHub.requestAttestation` → DA-layer proof
→ `ApyOracle.submitApy`) needs the testnet verifier API key + a deployed ApyOracle — a post-deploy step.

*LIVE-ONLY: FTSOv2 prices and venue APYs are runtime data, never mixed into the backtested numbers.*
