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

    uint256 public apyBips; // e.g. 800 == 8.00% APY
    uint256 public updatedAt;

    event ApyUpdated(uint256 apyBips, uint256 at);

    /// @param verifier_ the FdcVerification contract (resolve via FlareResolver.fdc()/ContractRegistry at deploy).
    constructor(address verifier_) {
        verifier = IFdcVerification(verifier_);
    }

    /// Verify an FDC Web2Json proof and store the attested APY (in basis points).
    function submitApy(IWeb2Json.Proof calldata proof) external {
        require(verifier.verifyWeb2Json(proof), "ApyOracle: invalid proof");
        uint256 bips = abi.decode(proof.data.responseBody.abiEncodedData, (uint256));
        apyBips = bips;
        updatedAt = block.timestamp;
        emit ApyUpdated(bips, block.timestamp);
    }

    function apy() external view returns (uint256) {
        return apyBips;
    }
}
