# RotorVault — Demo Video Script (~2:20)

Recorded assets: the dashboard (`web/index.html`), a terminal, and the Coston2 explorer.

## 0:00 — Cold open (headline first)
> "This is XRP over the last cycle: up 5×, then down 80%. Most FXRP yield vaults ride that whole
> rollercoaster. **RotorVault doesn't.**"

Show the dashboard proof chart: grey HODL swinging violently, teal RotorVault staying smooth.
> "Same ballpark return — **half the drawdown**. −44% instead of −78%. And the de-risk is enforced
> **on-chain**, by Flare's own oracle — not by a promise."

## 0:20 — The product (dashboard)
Pan to the top of the dashboard. Point at the **vane**.
> "Deposit FXRP once. An agent proposes how to spread it across the live Firelight and Upshift vaults for
> yield — but every allocation has to clear an on-chain **FTSOv2** gate that reads the XRP price directly
> in the contract."

Toggle to **LIVE**.
> "This is the real Coston2 deployment — 5 FXRP in the vault. Right now the FTSO gate is risk-off, so it's
> holding everything **idle**: the safety state, live on-chain."

## 0:45 — The killer proof: the veto is real (explorer)
Open the `rebalance` tx on the Coston2 explorer (`0x6cb9c76a…`).
> "Here's what 'enforced on-chain' means. The agent proposed `rebalance(4000, 4000)` — 40% Firelight, 40%
> Upshift. But the gate was risk-off, so the contract **overrode it to zero**. The event reads
> `Rebalanced(0, 0, false)` — the veto isn't a promise, it's in the transaction. No operator can bypass it."

## 1:10 — FDC is load-bearing, not decorative (explorer)
Open the `submitApy` tx (`0x4bd66431…`), then point at `ApyOracle.apy()` = 800.
> "The Upshift APY comes on-chain through an **FDC Web2Json** attestation — verified against Flare's FDC and
> bound to one source URL. And it isn't just stored: `rebalance()` **reads** it, and a zero or stale
> attested APY forces that venue idle. The FDC value gates real capital."

## 1:35 — It's real, on Coston2 (terminal)
```
cd contracts && forge test
```
> "None of this is mocked. Our adapters are fork-tested against the **real** Firelight and Upshift vaults on
> Coston2 — deposit, deploy, redeem, claim. 28 contract tests, green against live state, zero API keys."

Show `test_deployIntoRealVenues … PASS` and `test_staleApyForcesUpshiftIdle … PASS`.

## 1:55 — The thesis is reproducible (terminal)
```
cd backtest && bash reproduce.sh
```
> "And the strategy isn't a story — it's a keyless, byte-for-byte reproducible backtest. Run it with zero
> API keys and you get the same −44% drawdown number."

Show `PASS -- results reproduce byte-identically`.

## 2:10 — Close
> "RotorVault: three Flare protocols, all doing real on-chain work — FTSO vetoes, FAssets flows, FDC gates.
> The risk overlay the FXRP ecosystem doesn't have yet — for XRP holders who want yield without the whiplash."

Show the deployed RotorVault address (`0x8C7F…4831`) on the Coston2 explorer. End.
