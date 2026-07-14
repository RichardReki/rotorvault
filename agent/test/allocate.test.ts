import { describe, it, expect } from "vitest";
import { allocate, type Allocation } from "../src/allocate";

const CFG = { maxVenueWeight: 0.8 };
const sum = (a: Allocation) => a.venueAllocation.firelight + a.venueAllocation.upshift + a.venueAllocation.idle;

describe("allocate (parity with vault.py)", () => {
  it("risk-off goes fully idle", () => {
    const a = allocate(0, false, { firelight: 0.03, upshift: 0.08 }, CFG);
    expect(a.fxrpExposure).toBe(0);
    expect(a.venueAllocation.idle).toBe(1);
    expect(sum(a)).toBeCloseTo(1, 9);
  });

  it("deployed portion tilts to higher APY", () => {
    const a = allocate(1, true, { firelight: 0.02, upshift: 0.08 }, CFG);
    expect(a.venueAllocation.upshift).toBeGreaterThan(a.venueAllocation.firelight);
    expect(a.venueAllocation.firelight).toBeGreaterThan(0);
    expect(sum(a)).toBeCloseTo(1, 9);
  });

  it("exposure leaves remainder idle", () => {
    const a = allocate(0.6, true, { firelight: 0.04, upshift: 0.04 }, CFG);
    expect(a.venueAllocation.idle).toBeCloseTo(0.4, 9);
    expect(a.venueAllocation.firelight).toBeCloseTo(0.3, 9);
    expect(a.venueAllocation.upshift).toBeCloseTo(0.3, 9);
  });

  it("per-venue cap overflows to idle", () => {
    const a = allocate(1, true, { firelight: 0, upshift: 0.1 }, { maxVenueWeight: 0.7 });
    expect(a.venueAllocation.upshift).toBeCloseTo(0.7, 9);
    expect(a.venueAllocation.idle).toBeCloseTo(0.3, 9);
    expect(sum(a)).toBeCloseTo(1, 9);
  });

  it("zero apy info splits equally", () => {
    const a = allocate(1, true, { firelight: 0, upshift: 0 }, CFG);
    expect(a.venueAllocation.firelight).toBeCloseTo(0.5, 9);
    expect(a.venueAllocation.upshift).toBeCloseTo(0.5, 9);
  });

  it("negative cap is floored (no negative weights)", () => {
    const a = allocate(1, true, { firelight: 0.05, upshift: 0.05 }, { maxVenueWeight: -0.1 });
    const v = a.venueAllocation;
    expect(v.firelight).toBeGreaterThanOrEqual(0);
    expect(v.upshift).toBeGreaterThanOrEqual(0);
    expect(v.idle).toBeGreaterThanOrEqual(0);
    expect(sum(a)).toBeCloseTo(1, 9);
  });

  it("clamps out-of-range exposure", () => {
    const hi = allocate(1.5, true, { firelight: 0, upshift: 0 }, CFG);
    expect(hi.fxrpExposure).toBe(1);
    expect(sum(hi)).toBeCloseTo(1, 9);
    const lo = allocate(-0.5, true, { firelight: 0, upshift: 0 }, CFG);
    expect(lo.venueAllocation.idle).toBe(1);
    expect(sum(lo)).toBeCloseTo(1, 9);
  });
});
