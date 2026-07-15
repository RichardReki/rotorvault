#!/usr/bin/env bash
# One-command Coston2 deploy for RotorVault.
# Prereqs: fill contracts/.env with DEPLOYER_PRIVATE_KEY (see README), and fund that
# address with >=25 C2FLR from https://faucet.flare.network/coston2 .
# Run:  cd contracts && bash deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.foundry/bin:$PATH"

[ -f .env ] || { echo "ERROR: contracts/.env not found (copy from .env.example)"; exit 1; }
source ./.env
: "${COSTON2_RPC_URL:?set COSTON2_RPC_URL in .env}"
: "${DEPLOYER_PRIVATE_KEY:?set DEPLOYER_PRIVATE_KEY in .env}"

echo "== deployer =="
ADDR=$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")
echo "address: $ADDR"
BAL=$(cast balance "$ADDR" --rpc-url coston2 --ether)
echo "balance: $BAL C2FLR   (need ~25 for gas)"

echo ""
echo "== dry-run (simulation, no gas) =="
forge script script/Deploy.s.sol --rpc-url coston2

echo ""
read -r -p "Broadcast for real (spends C2FLR gas)? type 'yes' to proceed: " OK
[ "${OK:-}" = "yes" ] || { echo "aborted — nothing broadcast."; exit 0; }

echo ""
echo "== broadcasting =="
forge script script/Deploy.s.sol --rpc-url coston2 --broadcast --private-key "$DEPLOYER_PRIVATE_KEY" 2>&1 | tee deployment-coston2.log

echo ""
echo "Done. Deployed addresses are above and saved to contracts/deployment-coston2.log"
echo "Send the RegimeGate / FirelightAdapter / UpshiftAdapter / ApyOracle / RotorVault lines to your assistant."
