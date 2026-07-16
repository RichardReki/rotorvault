#!/usr/bin/env bash
# Drive one real on-chain cycle on the deployed RotorVault so the LIVE dashboard shows a real NAV/positions.
# Prereqs: contracts/.env has DEPLOYER_PRIVATE_KEY + COSTON2_RPC_URL + the v2 deploy addresses
#          (ROTOR_VAULT, ...); the deployer holds testnet FXRP (faucet -> Request FXRP).
# Run:  cd contracts && bash scripts/live-cycle.sh          (default deposits 5 FXRP)
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.foundry/bin:$PATH"
source ./.env
: "${COSTON2_RPC_URL:?}" "${DEPLOYER_PRIVATE_KEY:?}" "${ROTOR_VAULT:?set ROTOR_VAULT in .env}"
RPC="$COSTON2_RPC_URL"
FXRP=0x0b6A3645c240605887a5532109323A3E12273dc7   # Coston2 FTestXRP (resolve at runtime in contracts; fixed here for cast)
ME=$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")
AMOUNT=${AMOUNT:-5000000}   # 5 FXRP (6 decimals)

echo "deployer $ME  |  FXRP balance: $(cast call "$FXRP" "balanceOf(address)(uint256)" "$ME" --rpc-url "$RPC")"
echo "== approve + deposit ${AMOUNT} (6dp) FXRP =="
cast send "$FXRP" "approve(address,uint256)" "$ROTOR_VAULT" "$AMOUNT" --rpc-url "$RPC" --private-key "$DEPLOYER_PRIVATE_KEY" --legacy >/dev/null
cast send "$ROTOR_VAULT" "deposit(uint256,address)" "$AMOUNT" "$ME" --rpc-url "$RPC" --private-key "$DEPLOYER_PRIVATE_KEY" --legacy >/dev/null
echo "vault totalAssets: $(cast call "$ROTOR_VAULT" "totalAssets()(uint256)" --rpc-url "$RPC")  (now nonzero on the explorer)"

echo "== attempt rebalance 40/40/20 (deploys into real Firelight/Upshift IF the gate is ready & risk-on) =="
cast send "$ROTOR_VAULT" "rebalance(uint16,uint16)" 4000 4000 --rpc-url "$RPC" --private-key "$DEPLOYER_PRIVATE_KEY" --legacy \
  && echo "rebalanced." \
  || echo "rebalance did nothing / reverted — expected until the keeper has primed the gate (ready + risk-on). Re-run after warmup."
