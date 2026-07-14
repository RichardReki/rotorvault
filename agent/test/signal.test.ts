import { describe, it, expect } from "vitest";
import { proposeWeights, type OnchainState } from "../src/signal";

function state(over: Partial<OnchainState> = {}): OnchainState {
  return {
    riskOn: true,
    ready: true,
    priceUsd: 1.06,
    apyBips: 800,
    nav: 0n,
    posFirelight: 0n,
    posUpshift: 0n,
    ...over,
  };
}

describe("proposeWeights", () => {
  it("risk-off proposes zero weights (all idle)", () => {
    const w = proposeWeights(state({ riskOn: false }));
    expect(w.wFirelightBips).toBe(0);
    expect(w.wUpshiftBips).toBe(0);
  });

  it("risk-on tilts to the higher-APY venue (Upshift via oracle)", () => {
    const w = proposeWeights(state({ riskOn: true, apyBips: 800 }), { firelightApyBips: 200, maxVenueWeight: 0.8 });
    expect(w.wUpshiftBips).toBeGreaterThan(w.wFirelightBips);
    expect(w.wFirelightBips + w.wUpshiftBips).toBeLessThanOrEqual(10_000);
  });

  it("risk-on with only Upshift APY caps at maxVenueWeight and idles the rest", () => {
    const w = proposeWeights(state({ riskOn: true, apyBips: 1000 }), { firelightApyBips: 0, maxVenueWeight: 0.8 });
    expect(w.wUpshiftBips).toBe(8000); // capped at 80%
    expect(w.wFirelightBips).toBe(0);
  });
});
