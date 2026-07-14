export const rotorVaultAbi = [
  { type: "function", name: "totalAssets", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
  { type: "function", name: "agent", stateMutability: "view", inputs: [], outputs: [{ type: "address" }] },
  {
    type: "function",
    name: "rebalance",
    stateMutability: "nonpayable",
    inputs: [
      { name: "wFirelight", type: "uint16" },
      { name: "wUpshift", type: "uint16" },
    ],
    outputs: [],
  },
  { type: "function", name: "claimMatured", stateMutability: "nonpayable", inputs: [], outputs: [{ type: "uint256" }] },
] as const;

export const regimeGateAbi = [
  { type: "function", name: "riskOn", stateMutability: "view", inputs: [], outputs: [{ type: "bool" }] },
  { type: "function", name: "ready", stateMutability: "view", inputs: [], outputs: [{ type: "bool" }] },
  { type: "function", name: "currentPrice1e18", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
  { type: "function", name: "sample", stateMutability: "nonpayable", inputs: [], outputs: [] },
] as const;

export const apyOracleAbi = [
  { type: "function", name: "apy", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
] as const;

export const venueAbi = [
  { type: "function", name: "positionValue", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
] as const;
