import { toHex, pad } from "viem";

/// Upshift's public APY API only indexes MAINNET vaults; earnXRP is the FXRP yield product we attest.
export const UPSHIFT_MAINNET_EARNXRP = "0x373D7d201C8134D4a2f7b5c63560da217e3dEA28";
export const VERIFIER_BASE = "https://fdc-verifiers-testnet.flare.network";
export const DA_BASE = "https://ctn2-data-availability.flare.network";

/// bytes32 of an ASCII string, right-padded — Flare's attestationType/sourceId encoding.
export function encodeAttestationName(name: string): `0x${string}` {
  return pad(toHex(name), { dir: "right", size: 32 });
}

export interface Web2JsonRequestBody {
  url: string;
  httpMethod: string;
  headers: string;
  queryParams: string;
  body: string;
  postProcessJq: string;
  abiSignature: string;
}

/// Fetch the Upshift APY and scale the fraction (e.g. 0.08) to integer basis points (800). jq's
/// `floor`/`round` are DISALLOWED by the FDC jq subset, so we scale by 1e4, stringify, and truncate
/// on the decimal point before converting back to a number.
export function buildUpshiftApyRequestBody(vaultAddr: string = UPSHIFT_MAINNET_EARNXRP): Web2JsonRequestBody {
  return {
    url: `https://api.upshift.finance/v1/tokenized_vaults/${vaultAddr}`,
    httpMethod: "GET",
    headers: "{}",
    queryParams: "{}",
    body: "{}",
    postProcessJq: '{apyBips: ((.reported_apy.apy * 10000) | tostring | split(".")[0] | tonumber)}',
    abiSignature: '{"components":[{"internalType":"uint256","name":"apyBips","type":"uint256"}],"name":"dto","type":"tuple"}',
  };
}

export interface PrepareRequest {
  attestationType: `0x${string}`;
  sourceId: `0x${string}`;
  requestBody: Web2JsonRequestBody;
}

export function buildPrepareRequest(vaultAddr?: string): PrepareRequest {
  return {
    attestationType: encodeAttestationName("Web2Json"),
    sourceId: encodeAttestationName("PublicWeb2"),
    requestBody: buildUpshiftApyRequestBody(vaultAddr),
  };
}

/// LIVE PIPELINE (post-deploy; needs the testnet verifier X-API-KEY + a deployed ApyOracle):
///   1. POST `${VERIFIER_BASE}/verifier/web2/Web2Json/prepareRequest`  (X-API-KEY) -> { abiEncodedRequest }
///   2. FdcHub.requestAttestation(abiEncodedRequest) { value: FdcRequestFeeConfigurations.getRequestFee(...) }
///   3. after the voting round finalizes (Relay.isFinalized(200, roundId)):
///      POST `${DA_BASE}/api/v1/fdc/proof-by-request-round-raw` { votingRoundId, requestBytes } -> { proof, response_hex }
///   4. decode into an IWeb2Json.Proof and call ApyOracle.submitApy(proof)
export async function prepareRequestBytes(prepare: PrepareRequest, apiKey: string): Promise<`0x${string}`> {
  const res = await fetch(`${VERIFIER_BASE}/verifier/web2/Web2Json/prepareRequest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-KEY": apiKey },
    body: JSON.stringify(prepare),
  });
  if (!res.ok) throw new Error(`verifier prepareRequest failed: ${res.status}`);
  const json = (await res.json()) as { abiEncodedRequest?: `0x${string}` };
  if (!json.abiEncodedRequest) throw new Error("verifier returned no abiEncodedRequest");
  return json.abiEncodedRequest;
}
