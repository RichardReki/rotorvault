// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {ApyOracle} from "../src/ApyOracle.sol";
import {IWeb2Json} from "flare-periphery/src/coston2/IWeb2Json.sol";

/// Stand-in for FdcVerification so the on-chain verify+decode logic is testable without a real
/// Merkle proof. Selector matches IFdcVerification.verifyWeb2Json.
contract MockFdcVerifier {
    bool public result;

    function setResult(bool r) external {
        result = r;
    }

    function verifyWeb2Json(IWeb2Json.Proof calldata) external view returns (bool) {
        return result;
    }
}

contract ApyOracleTest is Test {
    MockFdcVerifier verifier;
    ApyOracle oracle;
    string constant URL = "https://api.upshift.finance/v1/tokenized_vaults/0x373D";

    function setUp() public {
        verifier = new MockFdcVerifier();
        oracle = new ApyOracle(address(verifier), URL);
    }

    function _proof(uint256 bips, string memory url) internal pure returns (IWeb2Json.Proof memory proof) {
        proof.data.responseBody.abiEncodedData = abi.encode(bips);
        proof.data.requestBody.url = url;
    }

    function test_submitStoresDecodedApy() public {
        verifier.setResult(true);
        oracle.submitApy(_proof(800, URL)); // 8.00%
        assertEq(oracle.apy(), 800);
        assertGt(oracle.updatedAt(), 0);
    }

    function test_rejectsInvalidProof() public {
        verifier.setResult(false);
        vm.expectRevert(bytes("ApyOracle: invalid proof"));
        oracle.submitApy(_proof(800, URL));
    }

    function test_rejectsValidProofOfWrongSource() public {
        verifier.setResult(true); // proof verifies, but it's of a different URL
        vm.expectRevert(bytes("ApyOracle: wrong source"));
        oracle.submitApy(_proof(999, "https://evil.example/fake-apy"));
    }

    function test_updatesOnNewProof() public {
        verifier.setResult(true);
        oracle.submitApy(_proof(800, URL));
        oracle.submitApy(_proof(450, URL));
        assertEq(oracle.apy(), 450);
    }
}
