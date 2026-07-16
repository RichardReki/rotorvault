#!/usr/bin/env bash
# Source-verify all five deployed contracts on the Coston2 Blockscout explorer (no API key needed).
# Prereqs: contracts/.env has DEPLOYER_PRIVATE_KEY + the v2 addresses
#          (REGIME_GATE, FIRELIGHT_ADAPTER, UPSHIFT_ADAPTER, APY_ORACLE, ROTOR_VAULT).
# Run:  cd contracts && bash verify.sh
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.foundry/bin:$PATH"
source ./.env
: "${DEPLOYER_PRIVATE_KEY:?}" "${REGIME_GATE:?}" "${FIRELIGHT_ADAPTER:?}" "${UPSHIFT_ADAPTER:?}" "${APY_ORACLE:?}" "${ROTOR_VAULT:?}"

DEPLOYER=$(cast wallet address --private-key "$DEPLOYER_PRIVATE_KEY")
VER=(--verifier blockscout --verifier-url https://coston2-explorer.flare.network/api/ --chain 114 --watch)

FXRP=0x0b6A3645c240605887a5532109323A3E12273dc7
FDC=0x906507E0B64bcD494Db73bd0459d1C667e14B933
FIRELIGHT=0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B
UPSHIFT=0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81
APY_URL="https://api.upshift.finance/v1/tokenized_vaults/0x373D7d201C8134D4a2f7b5c63560da217e3dEA28"

echo "== RegimeGate =="
forge verify-contract "$REGIME_GATE" src/RegimeGate.sol:RegimeGate "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(uint256,uint256)' 300 100)"
echo "== FirelightAdapter =="
forge verify-contract "$FIRELIGHT_ADAPTER" src/venues/FirelightAdapter.sol:FirelightAdapter "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address)' "$FIRELIGHT" "$DEPLOYER")"
echo "== UpshiftAdapter =="
forge verify-contract "$UPSHIFT_ADAPTER" src/venues/UpshiftAdapter.sol:UpshiftAdapter "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address)' "$UPSHIFT" "$DEPLOYER")"
echo "== ApyOracle =="
forge verify-contract "$APY_ORACLE" src/ApyOracle.sol:ApyOracle "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,string)' "$FDC" "$APY_URL")"
echo "== RotorVault =="
forge verify-contract "$ROTOR_VAULT" src/RotorVault.sol:RotorVault "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address,address,address)' "$FXRP" "$REGIME_GATE" "$FIRELIGHT_ADAPTER" "$UPSHIFT_ADAPTER")"
echo "All submitted."
