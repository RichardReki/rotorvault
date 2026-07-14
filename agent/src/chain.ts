import { defineChain, createPublicClient, createWalletClient, http, type PublicClient, type WalletClient } from "viem";
import { privateKeyToAccount } from "viem/accounts";

/// Flare Coston2 testnet.
export const coston2 = defineChain({
  id: 114,
  name: "Flare Testnet Coston2",
  nativeCurrency: { name: "Coston2 Flare", symbol: "C2FLR", decimals: 18 },
  rpcUrls: { default: { http: ["https://coston2-api.flare.network/ext/C/rpc"] } },
  blockExplorers: { default: { name: "Coston2 Explorer", url: "https://coston2-explorer.flare.network" } },
});

export function makePublicClient(rpc: string): PublicClient {
  return createPublicClient({ chain: coston2, transport: http(rpc) });
}

/// Only constructed when a private key is supplied (real writes). Never called in dry-run.
export function makeWalletClient(rpc: string, privateKey: `0x${string}`): WalletClient {
  const account = privateKeyToAccount(privateKey);
  return createWalletClient({ account, chain: coston2, transport: http(rpc) });
}
