#!/usr/bin/env bash
# Source-verify the redeployed contracts (RotorVault + the two adapters) on the Coston2 Blockscout
# explorer. No API key, no private key needed. RegimeGate + ApyOracle are reused unchanged from the
# earlier deploy, so they are already verified.
# Run:  cd contracts && bash verify.sh
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.foundry/bin:$PATH"
VER=(--verifier blockscout --verifier-url https://coston2-explorer.flare.network/api/ --chain 114 --watch)

DEPLOYER=0x66F9Bd73c4847584f158c8D19EEd179F21adC169
FXRP=0x0b6A3645c240605887a5532109323A3E12273dc7
FIRELIGHT=0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B
UPSHIFT=0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81
GATE=0xc3762daB9AB246771a91B764d0E45f03619A61ea       # reused (already verified)
APY_ORACLE=0xD3103fb1189a6f21C72387efab1c77aaF79803cF # reused (already verified)
FIRELIGHT_ADAPTER=0x256b037EEF65aAb98C9CBc4b39866fc643E523b7
UPSHIFT_ADAPTER=0xb31a17B2B8B17f9bb8b8494B1BcC59a4b8CAe446
ROTOR_VAULT=0x8C7FF254D4723186f660DdFB0EaF084cb7654831

echo "== FirelightAdapter =="
forge verify-contract "$FIRELIGHT_ADAPTER" src/venues/FirelightAdapter.sol:FirelightAdapter "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address)' "$FIRELIGHT" "$DEPLOYER")"
echo "== UpshiftAdapter =="
forge verify-contract "$UPSHIFT_ADAPTER" src/venues/UpshiftAdapter.sol:UpshiftAdapter "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address)' "$UPSHIFT" "$DEPLOYER")"
echo "== RotorVault =="
forge verify-contract "$ROTOR_VAULT" src/RotorVault.sol:RotorVault "${VER[@]}" \
  --constructor-args "$(cast abi-encode 'c(address,address,address,address,address)' "$FXRP" "$GATE" "$FIRELIGHT_ADAPTER" "$UPSHIFT_ADAPTER" "$APY_ORACLE")"
echo "All submitted. (RegimeGate + ApyOracle unchanged from the prior deploy -- already verified.)"
