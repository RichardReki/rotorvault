// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {ApyOracle} from "../src/ApyOracle.sol";
import {IWeb2Json} from "flare-periphery/src/coston2/IWeb2Json.sol";

/// Stand-in for FdcVerification so the on-chain verify+decode logic is testable without a real
/// Merkle proof (which would require live FDC round state). Selector matches IFdcVerification.verifyWeb2Json.
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

    function setUp() public {
        verifier = new MockFdcVerifier();
        oracle = new ApyOracle(address(verifier));
    }

    function _proofWithApy(uint256 bips) internal pure returns (IWeb2Json.Proof memory proof) {
        proof.data.responseBody.abiEncodedData = abi.encode(bips);
    }

    function test_submitStoresDecodedApy() public {
        verifier.setResult(true);
        oracle.submitApy(_proofWithApy(800)); // 8.00%
        assertEq(oracle.apy(), 800);
        assertGt(oracle.updatedAt(), 0);
    }

    function test_rejectsInvalidProof() public {
        verifier.setResult(false);
        vm.expectRevert(bytes("ApyOracle: invalid proof"));
        oracle.submitApy(_proofWithApy(800));
    }

    function test_updatesOnNewProof() public {
        verifier.setResult(true);
        oracle.submitApy(_proofWithApy(800));
        oracle.submitApy(_proofWithApy(450));
        assertEq(oracle.apy(), 450);
    }
}
