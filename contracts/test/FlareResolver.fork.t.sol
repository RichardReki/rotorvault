// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {FlareResolver} from "../src/lib/FlareResolver.sol";

interface IERC20Dec {
    function decimals() external view returns (uint8);
}

contract FlareResolverForkTest is Test {
    // XRP/USD block-latency feed id (category 01 = Crypto)
    bytes21 constant XRP_USD = 0x015852502f55534400000000000000000000000000;

    function setUp() public {
        vm.createSelectFork(vm.envString("COSTON2_RPC_URL"));
    }

    function test_resolvesFxrpAtRuntime() public {
        address fxrp = FlareResolver.fxrp();
        assertEq(fxrp, 0x0b6A3645c240605887a5532109323A3E12273dc7, "resolved FXRP");
        assertEq(IERC20Dec(fxrp).decimals(), 6, "FXRP is 6 decimals");
    }

    function test_ftsoReadsLiveXrpUsd() public {
        (uint256 value, int8 decimals, uint64 ts) = FlareResolver.ftso().getFeedById(XRP_USD);
        assertGt(value, 0, "live XRP/USD value");
        assertGt(ts, 0, "feed timestamp");
        emit log_named_uint("XRP/USD raw value", value);
        emit log_named_int("XRP/USD decimals", decimals);
    }
}
