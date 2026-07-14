import { describe, it, expect } from "vitest";
import { execute, type RebalancePlan } from "../src/rebalance";

const plan: RebalancePlan = {
  vault: "0x0000000000000000000000000000000000000001",
  wFirelightBips: 4000,
  wUpshiftBips: 4000,
  wIdleBips: 2000,
  simulated: true,
  note: "ok",
};

describe("execute safety gate", () => {
  it("refuses to broadcast without ENABLE_ONCHAIN_WRITE", async () => {
    await expect(execute(plan, { enableWrite: false })).rejects.toThrow(/dry-run only/);
  });

  it("refuses when enabled but no wallet is present", async () => {
    await expect(execute(plan, { enableWrite: true })).rejects.toThrow(/dry-run only/);
  });
});
