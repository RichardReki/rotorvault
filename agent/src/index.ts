import { loadConfig } from "./config";
import { makePublicClient } from "./chain";
import { readState, proposeWeights } from "./signal";
import { buildPlan } from "./rebalance";
import { buildPrepareRequest } from "./fdc";
import { rotorVaultAbi } from "./abis";

function bigintReplacer(_k: string, v: unknown) {
  return typeof v === "bigint" ? v.toString() : v;
}

async function main() {
  const cmd = process.argv[2] ?? "state";

  // `apy-request` is offline (pure builder) — no addresses/RPC needed, handy for the demo.
  if (cmd === "apy-request") {
    console.log(JSON.stringify(buildPrepareRequest(), null, 2));
    return;
  }

  const cfg = loadConfig();
  const client = makePublicClient(cfg.rpc);

  if (cmd === "state") {
    const s = await readState(client, cfg.addresses);
    console.log(JSON.stringify(s, bigintReplacer, 2));
    return;
  }

  if (cmd === "plan") {
    const s = await readState(client, cfg.addresses);
    const w = proposeWeights(s, { firelightApyBips: 0 });
    // simulate as the on-chain agent (read-only; needs no key)
    const agent = (await client.readContract({
      address: cfg.addresses.vault,
      abi: rotorVaultAbi,
      functionName: "agent",
    })) as `0x${string}`;
    const plan = await buildPlan(client, cfg.addresses.vault, w.wFirelightBips, w.wUpshiftBips, agent);
    console.log(JSON.stringify({ state: s, proposed: w, plan }, bigintReplacer, 2));
    console.log(
      cfg.enableWrite
        ? "\n[ENABLE_ONCHAIN_WRITE=true] broadcasting is armed — run your own signed rebalance."
        : "\n[dry-run] set ENABLE_ONCHAIN_WRITE=true + AGENT_PRIVATE_KEY to broadcast.",
    );
    return;
  }

  console.log("usage: agent <state|plan|apy-request>");
}

main().catch((e) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
