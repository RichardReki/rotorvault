# RotorVault — Pitch

## One line
A self-driving, risk-managed FXRP yield vault: it reads FTSOv2 on-chain and pulls capital out of yield
back to safety when the market turns — automatically.

## The problem
XRP holders want on-chain yield, but the FXRP venues that exist today (Firelight, Upshift/earnXRP, MXRPY)
are static, single-strategy products with **no market-aware risk management**. You either sit fully
exposed through an 80% drawdown, or you babysit positions manually. Neither is a product.

## The solution
RotorVault is a **risk overlay on the whole FXRP ecosystem**. Deposit FXRP once; the vault routes it
across the existing venues for yield, and an **on-chain FTSOv2 regime gate** forces everything to idle the
moment the market breaks trend. The intelligence lives in the contract, enforced by the oracle — not in a
promise.

## Why it wins Bounty 1
- **Product usefulness:** solves a real, unserved need for XRP holders — yield *with* downside protection.
- **Flare integration (meaningful, not superficial):** three enshrined protocols are load-bearing —
  FTSOv2 vetoes the allocation on-chain, FAssets/FXRP is deployed into the **real** Firelight & Upshift
  vaults (fork-verified on Coston2), and FDC Web2Json brings the live APY on-chain.
- **Technical execution:** 63 tests green, including contract fork-tests against the live vaults; deployed
  to Coston2; a keyless, byte-reproducible backtest.
- **Evidence of new work:** the RotorEdge signal engine is our pre-existing BNB Hack work, clearly
  separated — everything Flare (contracts, agent, gate, FDC oracle, overlay, dashboard) is new.
- **Clarity & future:** a concrete roadmap (multi-FAsset rotation, more venues, cross-chain deposits).

## The proof point
Out-of-sample 2021→2026, the risk overlay cut XRP's worst drawdown from **−77.9% to −44.4%** while keeping
~96% of the buy-and-hold return — nearly doubling Calmar. Reproducible with zero API keys. This validates
the *thesis* on RotorEdge's multi-factor research signal; the deployed v1 ships a minimal, fully-trustless
on-chain FTSO SMA gate embodying the same idea, with the richer signal on the roadmap.

## The ask
A first-place slot in Bounty 1 — and a design partner in Flare to take the risk overlay to mainnet across
every FAsset as they go live.

## Anticipated judge questions
- *"Is the FTSO integration real or decorative?"* — The `RegimeGate` reads `getFeedById` and stores an
  on-chain SMA; `RotorVault.rebalance` calls `gate.riskOn()` and overrides the agent to idle when false.
  A fork test drives a live sample and the veto path. It can't be removed without breaking the vault.
- *"Do you actually touch the real vaults?"* — Yes; `FirelightAdapter`/`UpshiftAdapter` fork tests deposit,
  redeem and claim against the live Coston2 addresses (`0x91Bfe6…`, `0x24c1a47c…`).
- *"Backtested returns look modest."* — By design. This is a drawdown/Calmar product; we lead with risk,
  disclose the raw-return tradeoff, and report the Deflated Sharpe.
- *"Does the −44% number describe the deployed contract?"* — No, and we flag it up front. That figure
  validates the *thesis* on RotorEdge's multi-factor research signal; the deployed v1 is a minimal,
  fully-trustless FTSO SMA gate embodying the same idea. The roadmap brings the full signal on-chain
  (agent-proposed, FTSO-verified).
