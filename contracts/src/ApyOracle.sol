// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IWeb2Json} from "flare-periphery/src/coston2/IWeb2Json.sol";
import {IFdcVerification} from "flare-periphery/src/coston2/IFdcVerification.sol";

/// Brings a venue's live APY on-chain, trustlessly, via an FDC Web2Json attestation. The off-chain
/// half (an agent/script) fetches the Upshift APY API, requests a Web2Json attestation whose jq filter
/// scales `reported_apy.apy` (a fraction) to integer basis points and whose abiSignature is `uint256`,
/// then submits the resulting proof here. On-chain we verify the proof against FDC and decode the bips.
contract ApyOracle {
    IFdcVerification public immutable verifier;
    bytes32 public immutable expectedUrlHash; // binds accepted proofs to one specific data source

    uint256 public apyBips; // e.g. 800 == 8.00% APY
    uint256 public updatedAt;

    event ApyUpdated(uint256 apyBips, uint256 at);

    /// @param verifier_ the FdcVerification contract (resolve via FlareResolver.fdc()/ContractRegistry at deploy).
    /// @param expectedUrl the exact Web2 URL a proof must attest — a valid proof of any OTHER source is rejected.
    constructor(address verifier_, string memory expectedUrl) {
        verifier = IFdcVerification(verifier_);
        expectedUrlHash = keccak256(bytes(expectedUrl));
    }

    /// Verify an FDC Web2Json proof OF THE EXPECTED SOURCE and store the attested APY (in basis points).
    /// Permissionless but source-bound: anyone may submit a fresh proof, but only of the bound URL.
    function submitApy(IWeb2Json.Proof calldata proof) external {
        require(verifier.verifyWeb2Json(proof), "ApyOracle: invalid proof");
        require(keccak256(bytes(proof.data.requestBody.url)) == expectedUrlHash, "ApyOracle: wrong source");
        uint256 bips = abi.decode(proof.data.responseBody.abiEncodedData, (uint256));
        apyBips = bips;
        updatedAt = block.timestamp;
        emit ApyUpdated(bips, block.timestamp);
    }

    function apy() external view returns (uint256) {
        return apyBips;
    }
}
