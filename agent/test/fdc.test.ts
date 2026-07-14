import { describe, it, expect } from "vitest";
import { encodeAttestationName, buildUpshiftApyRequestBody, buildPrepareRequest } from "../src/fdc";

describe("fdc Web2Json request builder", () => {
  it("encodes attestation names as right-padded bytes32", () => {
    const t = encodeAttestationName("Web2Json");
    expect(t).toMatch(/^0x[0-9a-f]{64}$/);
    // "Web2Json" ascii hex sits at the front (right-padded)
    expect(t.startsWith("0x576562324a736f6e")).toBe(true);
  });

  it("builds a Web2Json body for the Upshift APY without disallowed jq builtins", () => {
    const b = buildUpshiftApyRequestBody();
    expect(b.url).toContain("api.upshift.finance");
    expect(b.httpMethod).toBe("GET");
    expect(b.postProcessJq).not.toMatch(/floor|round/);
    expect(b.postProcessJq).toContain("apyBips");
    expect(b.abiSignature).toContain("uint256");
  });

  it("assembles a full prepareRequest", () => {
    const r = buildPrepareRequest();
    expect(r.attestationType).toMatch(/^0x[0-9a-f]{64}$/);
    expect(r.sourceId).toMatch(/^0x[0-9a-f]{64}$/);
    expect(r.requestBody.url).toContain("373D7d201C8134D4a2f7b5c63560da217e3dEA28");
  });
});
