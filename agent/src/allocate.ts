/// TS port of backtest/rotoredge/vault.py::allocate — the LIVE-ONLY venue-allocation overlay.
/// Kept line-for-line faithful to the Python so the on-chain agent and the backtest agree.

export interface Apys {
  firelight: number;
  upshift: number;
}

export interface AllocateCfg {
  maxVenueWeight?: number;
}

export interface Allocation {
  fxrpExposure: number;
  venueAllocation: { firelight: number; upshift: number; idle: number };
}

const VENUES = ["firelight", "upshift"] as const;

export function allocate(exposure: number, regimeOn: boolean, apys: Apys, cfg: AllocateCfg = {}): Allocation {
  const exp = Math.max(0, Math.min(1, exposure));
  if (!regimeOn || exp <= 0) {
    return { fxrpExposure: 0, venueAllocation: { firelight: 0, upshift: 0, idle: 1 } };
  }

  const cap = Math.max(0, cfg.maxVenueWeight ?? 0.8);
  const pos = { firelight: Math.max(0, apys.firelight), upshift: Math.max(0, apys.upshift) };
  const total = pos.firelight + pos.upshift;

  const split: { firelight: number; upshift: number } =
    total <= 0
      ? { firelight: exp / VENUES.length, upshift: exp / VENUES.length }
      : { firelight: exp * (pos.firelight / total), upshift: exp * (pos.upshift / total) };

  let overflow = 0;
  for (const v of VENUES) {
    if (split[v] > cap) {
      overflow += split[v] - cap;
      split[v] = cap;
    }
  }

  const idle = 1 - exp + overflow;
  return { fxrpExposure: exp, venueAllocation: { firelight: split.firelight, upshift: split.upshift, idle } };
}
