// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {FirelightAdapter} from "../src/venues/FirelightAdapter.sol";
import {IFirelightVault} from "../src/interfaces/IFirelightVault.sol";

contract FirelightAdapterForkTest is Test {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;

    FirelightAdapter adapter;
    IFirelightVault fl;
    IERC20 fxrp;

    function setUp() public {
        vm.createSelectFork(vm.envOr("COSTON2_RPC_URL", string("https://coston2-api.flare.network/ext/C/rpc")));
        adapter = new FirelightAdapter(FIRELIGHT, address(this));
        fl = IFirelightVault(FIRELIGHT);
        fxrp = IERC20(adapter.asset());
        // deal() fails on FXRP (FAsset proxy with custom accounting); fund from a real holder instead.
        vm.prank(FIRELIGHT);
        fxrp.transfer(address(this), 10e6);
        assertGe(fxrp.balanceOf(address(this)), 10e6, "funding from FXRP holder failed");
    }

    function test_depositAndPositionValue() public {
        fxrp.approve(address(adapter), 5e6);
        adapter.deposit(5e6);
        assertApproxEqAbs(adapter.positionValue(), 5e6, 1e5, "position ~= deposited");
    }

    function test_asyncRedeemThenClaim() public {
        fxrp.approve(address(adapter), 5e6);
        adapter.deposit(5e6);

        uint256 claimAt = adapter.requestRedeem(5e6);
        assertGt(claimAt, block.timestamp, "redemption is delayed");

        // warp past the end of the withdrawal period so claimWithdraw becomes valid
        vm.warp(claimAt + 1);
        vm.roll(block.number + 1);
        assertGt(fl.currentPeriod(), 306, "advanced past the withdrawal period");

        uint256 before = fxrp.balanceOf(address(this));
        uint256 delivered = adapter.claimMatured();
        assertApproxEqAbs(delivered, 5e6, 1e5, "claimed ~= redeemed FXRP");
        assertEq(fxrp.balanceOf(address(this)), before + delivered, "FXRP returned to owner");
    }
}
