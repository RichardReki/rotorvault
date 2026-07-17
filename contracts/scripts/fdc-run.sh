#!/usr/bin/env bash
# One-command FDC Web2Json round-trip: fetch the Upshift APY, attest it via FDC, and store it on-chain
# in ApyOracle. Prereqs: contracts/.env has DEPLOYER_PRIVATE_KEY + APY_ORACLE + the FDC vars
# (VERIFIER_URL_TESTNET, VERIFIER_API_KEY_TESTNET, X_API_KEY, COSTON2_DA_LAYER_URL — see .env.example).
# Deployer needs a little C2FLR for the attestation fee. Run: cd contracts && bash scripts/fdc-run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.foundry/bin:$PATH"
set -a && source ./.env && set +a
: "${DEPLOYER_PRIVATE_KEY:?}" "${APY_ORACLE:?}"
export PRIVATE_KEY="$DEPLOYER_PRIVATE_KEY"   # the FDC scripts read PRIVATE_KEY
mkdir -p data

echo "== 1/4 prepare attestation request (FDC verifier) =="
forge script script/SubmitApy.s.sol:PrepareApyRequest --rpc-url coston2 --ffi >/dev/null
echo "   ok — abiEncodedRequest written"

echo "== 2/4 submit attestation request on-chain (broadcast) =="
forge script script/SubmitApy.s.sol:SubmitApyRequest --rpc-url coston2 --broadcast --ffi >/dev/null
echo "   ok — voting round $(cat data/Apy_votingRoundId.txt)"

echo "== 3/4 wait for round finalization + fetch proof from the DA layer =="
ok=0
for i in $(seq 1 15); do
  sleep 30
  if forge script script/SubmitApy.s.sol:RetrieveApyProof --rpc-url coston2 --ffi >/dev/null 2>&1; then
    ok=1; echo "   ok — proof retrieved (after ~$((i*30))s)"; break
  fi
  echo "   round not finalized / proof not ready yet ($i/15)…"
done
[ "$ok" = 1 ] || { echo "!! proof not available after ~7.5 min — re-run later (the round may need more time)"; exit 1; }

echo "== 4/4 submit the proof to ApyOracle (broadcast) =="
forge script script/SubmitApy.s.sol:SubmitApyToOracle --rpc-url coston2 --broadcast --ffi >/dev/null
echo ""
echo "DONE. ApyOracle.apy() now = $(cast call "$APY_ORACLE" 'apy()(uint256)' --rpc-url coston2) bips  (on-chain, FDC-attested)"
echo "The last two transactions (requestAttestation + submitApy) are your on-chain FDC proof — grab their hashes from the explorer for the README."
