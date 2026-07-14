# RotorVault — Demo Video Script (~2:10)

Recorded assets: the dashboard (`web/index.html`), a terminal, and the Coston2 explorer.

## 0:00 — Cold open (headline first)
> "This is XRP over the last cycle: up 5×, then down 80%. Most FXRP yield vaults ride that whole
> rollercoaster. **RotorVault doesn't.**"

Show the dashboard proof chart: grey HODL swinging violently, teal RotorVault staying smooth.
> "Same ballpark return — **half the drawdown**. −44% instead of −78%. And it does it automatically,
> on-chain."

## 0:20 — The product (dashboard)
Pan to the top of the dashboard. Point at the **vane**.
> "Deposit FXRP once. The vault reads the XRP price from **FTSOv2** — Flare's oracle — directly in the
> contract. Right now it's risk-on, so the needle points to DEPLOY: 40% into Firelight, 40% into Upshift,
> a buffer idle."

Toggle the regime narrative:
> "The moment the FTSO regime breaks, the on-chain gate **vetoes the allocation** and forces everything
> back to idle — no keeper, no button. That's the risk management, enforced by the oracle itself."

## 0:50 — It's real, on Coston2 (terminal)
```
cd contracts && forge test --fork-url https://coston2-api.flare.network/ext/C/rpc
```
> "These aren't mocks. Our adapters are fork-tested against the **real** Firelight and Upshift vaults on
> Coston2 — deposit, deploy, redeem, claim. 23 contract tests, green against live state."

Show the end-to-end test line: `test_deployIntoRealVenues ... PASS`.

## 1:20 — All three enshrined protocols (screen: the 3 chips)
> "FTSOv2 drives the regime gate and NAV. FAssets/FXRP flows through the real vault lifecycle. And the
> **FDC** brings the live Upshift APY on-chain via a Web2Json attestation — so the yield tilt reacts to
> real yields, trustlessly. Three protocols, all load-bearing."

## 1:40 — The proof is reproducible (terminal)
```
cd backtest && bash reproduce.sh
```
> "The strategy isn't a story — it's a keyless, byte-for-byte reproducible backtest. A judge runs this
> with zero API keys and gets the same −44% drawdown number."

Show `PASS — results reproduce byte-identically`.

## 2:00 — Close
> "RotorVault: the risk overlay the FXRP ecosystem doesn't have yet. Built on Flare, for XRP holders who
> want yield without the whiplash."

Show the deployed RotorVault address on the Coston2 explorer. End.
