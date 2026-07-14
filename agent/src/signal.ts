import { type PublicClient } from "viem";
import { rotorVaultAbi, regimeGateAbi, apyOracleAbi, venueAbi } from "./abis";
import { allocate, type Allocation } from "./allocate";
import { type Addresses } from "./config";

export interface OnchainState {
  riskOn: boolean;
  ready: boolean;
  priceUsd: number; // XRP/USD
  apyBips: number; // Upshift APY from the on-chain ApyOracle
  nav: bigint; // FXRP, 6 dp
  posFirelight: bigint;
  posUpshift: bigint;
}

export async function readState(client: PublicClient, a: Addresses): Promise<OnchainState> {
  const [riskOn, ready, price, apyBips, nav, posFire, posUp] = await Promise.all([
    client.readContract({ address: a.gate, abi: regimeGateAbi, functionName: "riskOn" }),
    client.readContract({ address: a.gate, abi: regimeGateAbi, functionName: "ready" }),
    client.readContract({ address: a.gate, abi: regimeGateAbi, functionName: "currentPrice1e18" }),
    client.readContract({ address: a.apyOracle, abi: apyOracleAbi, functionName: "apy" }),
    client.readContract({ address: a.vault, abi: rotorVaultAbi, functionName: "totalAssets" }),
    client.readContract({ address: a.firelight, abi: venueAbi, functionName: "positionValue" }),
    client.readContract({ address: a.upshift, abi: venueAbi, functionName: "positionValue" }),
  ]);
  return {
    riskOn: riskOn as boolean,
    ready: ready as boolean,
    priceUsd: Number(price as bigint) / 1e18,
    apyBips: Number(apyBips as bigint),
    nav: nav as bigint,
    posFirelight: posFire as bigint,
    posUpshift: posUp as bigint,
  };
}

export interface SignalCfg {
  maxVenueWeight?: number;
  firelightApyBips?: number; // Firelight APY isn't on-chain in v1; supply a floor (LIVE-ONLY)
}

export interface ProposedWeights {
  wFirelightBips: number;
  wUpshiftBips: number;
  alloc: Allocation;
}

/// Exposure = 1 when the on-chain regime is risk-on, else 0 (the gate can veto). The deployed portion
/// is split across venues by live APY via the same allocate() the backtest uses.
export function proposeWeights(s: OnchainState, cfg: SignalCfg = {}): ProposedWeights {
  const exposure = s.riskOn ? 1 : 0;
  const apys = { firelight: (cfg.firelightApyBips ?? 0) / 10_000, upshift: s.apyBips / 10_000 };
  const alloc = allocate(exposure, s.riskOn, apys, { maxVenueWeight: cfg.maxVenueWeight ?? 0.8 });
  return {
    wFirelightBips: Math.round(alloc.venueAllocation.firelight * 10_000),
    wUpshiftBips: Math.round(alloc.venueAllocation.upshift * 10_000),
    alloc,
  };
}
