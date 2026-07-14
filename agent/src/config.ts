export type Address = `0x${string}`;

export interface Addresses {
  vault: Address;
  gate: Address;
  apyOracle: Address;
  firelight: Address;
  upshift: Address;
}

export interface Config {
  rpc: string;
  addresses: Addresses;
  enableWrite: boolean;
  privateKey?: `0x${string}`;
}

function req(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`missing env ${name} (fill agent/.env from .env.example; addresses come from the Plan 2 deploy)`);
  return v;
}

function addr(name: string): Address {
  const v = req(name);
  if (!/^0x[0-9a-fA-F]{40}$/.test(v)) throw new Error(`env ${name} is not a 20-byte address: ${v}`);
  return v as Address;
}

/// Load full config (needs deployed addresses). Unit tests do NOT call this — they test pure functions.
export function loadConfig(): Config {
  const enableWrite = (process.env.ENABLE_ONCHAIN_WRITE ?? "").toLowerCase() === "true";
  const pk = process.env.AGENT_PRIVATE_KEY as `0x${string}` | undefined;
  if (enableWrite && !pk) throw new Error("ENABLE_ONCHAIN_WRITE=true but AGENT_PRIVATE_KEY is unset");
  return {
    rpc: req("COSTON2_RPC_URL"),
    addresses: {
      vault: addr("ROTOR_VAULT"),
      gate: addr("REGIME_GATE"),
      apyOracle: addr("APY_ORACLE"),
      firelight: addr("FIRELIGHT_ADAPTER"),
      upshift: addr("UPSHIFT_ADAPTER"),
    },
    enableWrite,
    privateKey: enableWrite ? pk : undefined,
  };
}
