// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {UpshiftAdapter} from "../src/venues/UpshiftAdapter.sol";

/// Verifies the UpshiftAdapter against the live Coston2 vault for the paths testnet supports:
/// deposit + positionValue + requestRedeem. The final claim delivery depends on the vault operator
/// fulfilling the epoch (an off-chain step a fork cannot trigger), so we only assert claimMatured()
/// is safely callable (try/catch) — delivery is exercised end-to-end via MockVenue in the vault tests.
contract UpshiftAdapterForkTest is Test {
    address constant UPSHIFT = 0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81;
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B; // FXRP holder

    UpshiftAdapter adapter;
    IERC20 fxrp;

    function setUp() public {
        vm.createSelectFork(vm.envString("COSTON2_RPC_URL"));
        adapter = new UpshiftAdapter(UPSHIFT, address(this));
        fxrp = IERC20(adapter.asset());
        vm.prank(FIRELIGHT);
        fxrp.transfer(address(this), 8e6);
    }

    function test_depositAndPositionValue() public {
        fxrp.approve(address(adapter), 5e6);
        adapter.deposit(5e6);
        // gross position ~= deposit (small entry difference)
        assertApproxEqAbs(adapter.positionValue(), 5e6, 5e4, "position ~= deposited");
    }

    function test_requestRedeemRecordsPending() public {
        fxrp.approve(address(adapter), 5e6);
        adapter.deposit(5e6);

        uint256 claimAt = adapter.requestRedeem(5e6);
        assertGt(claimAt, 0, "returns a claimable epoch");
        assertEq(adapter.pendingCount(), 1, "recorded a pending request");

        // claimMatured is safely callable even before the operator fulfills (delivers 0)
        vm.warp(block.timestamp + 2 days);
        vm.roll(block.number + 1);
        uint256 delivered = adapter.claimMatured();
        // On testnet the epoch is typically not operator-fulfilled, so delivery is 0 and the request
        // remains pending; in production claim() delivers once fulfilled.
        assertEq(delivered, 0, "no delivery until operator fulfills the epoch");
        assertEq(adapter.pendingCount(), 1, "request stays pending until fulfilled");
    }
}
