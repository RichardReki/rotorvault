// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin-contracts/token/ERC20/ERC20.sol";
import {IdleVenue} from "../src/venues/IdleVenue.sol";
import {MockVenue} from "../src/venues/MockVenue.sol";

contract MintFXRP is ERC20 {
    constructor() ERC20("FTestXRP", "FXRP") {}
    function mint(address to, uint256 amt) external { _mint(to, amt); }
    function decimals() public pure override returns (uint8) { return 6; }
}

contract VenuesTest is Test {
    MintFXRP fxrp;

    function setUp() public {
        fxrp = new MintFXRP();
        fxrp.mint(address(this), 1_000e6);
    }

    function test_idle_depositAndInstantRedeem() public {
        IdleVenue v = new IdleVenue(address(fxrp));
        assertTrue(v.isInstant());
        fxrp.approve(address(v), 100e6);
        v.deposit(100e6);
        assertEq(v.positionValue(), 100e6);

        uint256 at = v.requestRedeem(40e6);
        assertEq(at, 0, "idle redeem is instant");
        assertEq(v.positionValue(), 60e6);
        assertEq(fxrp.balanceOf(address(this)), 1_000e6 - 60e6, "40 FXRP returned instantly");
        assertEq(v.claimMatured(), 0);
    }

    function test_mock_asyncRedeemWithYield() public {
        MockVenue v = new MockVenue(address(fxrp), 1 days, 500); // 5% yield
        fxrp.mint(address(v), 100e6); // pre-fund yield coverage
        assertFalse(v.isInstant());

        fxrp.approve(address(v), 100e6);
        v.deposit(100e6);
        assertEq(v.positionValue(), 105e6, "principal + 5% yield");

        uint256 at = v.requestRedeem(v.positionValue()); // full exit at current value
        assertEq(at, block.timestamp + 1 days, "matures after lag");
        assertEq(v.claimMatured(), 0, "nothing matured yet");

        vm.warp(block.timestamp + 1 days + 1);
        uint256 before = fxrp.balanceOf(address(this));
        uint256 delivered = v.claimMatured();
        assertEq(delivered, 105e6, "principal + yield delivered");
        assertEq(fxrp.balanceOf(address(this)), before + 105e6);
    }
}
