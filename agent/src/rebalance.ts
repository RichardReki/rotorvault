import { type PublicClient, type WalletClient } from "viem";
import { rotorVaultAbi } from "./abis";
import { type Address } from "./config";

export interface RebalancePlan {
  vault: Address;
  wFirelightBips: number;
  wUpshiftBips: number;
  wIdleBips: number;
  simulated: boolean;
  note: string;
}

/// Build a rebalance plan and (if an account is given) simulate it read-only — never broadcasts.
export async function buildPlan(
  client: PublicClient,
  vault: Address,
  wFirelightBips: number,
  wUpshiftBips: number,
  account?: Address,
): Promise<RebalancePlan> {
  const wIdleBips = 10_000 - wFirelightBips - wUpshiftBips;
  let simulated = false;
  let note = "not simulated (no account configured)";
  if (account) {
    try {
      await client.simulateContract({
        address: vault,
        abi: rotorVaultAbi,
        functionName: "rebalance",
        args: [wFirelightBips, wUpshiftBips],
        account,
      });
      simulated = true;
      note = "simulation OK (dry-run) — not broadcast";
    } catch (e) {
      note = `simulation reverted: ${(e as Error).message.split("\n")[0]}`;
    }
  }
  return { vault, wFirelightBips, wUpshiftBips, wIdleBips, simulated, note };
}

export interface ExecuteOpts {
  enableWrite: boolean;
  wallet?: WalletClient;
  account?: Address;
}

/// Broadcast the rebalance ONLY when explicitly enabled AND a wallet is present. Otherwise refuses.
/// This is the single choke point that keeps the agent dry-run by default.
export async function execute(plan: RebalancePlan, opts: ExecuteOpts): Promise<`0x${string}`> {
  if (!opts.enableWrite || !opts.wallet || !opts.account) {
    throw new Error("dry-run only: set ENABLE_ONCHAIN_WRITE=true and AGENT_PRIVATE_KEY in .env to broadcast");
  }
  return opts.wallet.writeContract({
    address: plan.vault,
    abi: rotorVaultAbi,
    functionName: "rebalance",
    args: [plan.wFirelightBips, plan.wUpshiftBips],
    account: opts.account,
    chain: opts.wallet.chain,
  });
}
