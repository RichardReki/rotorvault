// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {RegimeGate} from "../src/RegimeGate.sol";

contract RegimeGateForkTest is Test {
    function setUp() public {
        vm.createSelectFork(vm.envString("COSTON2_RPC_URL"));
    }

    function test_liveSampleFromFtso() public {
        RegimeGate g = new RegimeGate(0);
        uint256 p = g.currentPrice1e18();
        // XRP sits in a sane USD band (guards against a decimal-scaling bug)
        assertGt(p, 0.1e18, "XRP > $0.10");
        assertLt(p, 100e18, "XRP < $100");

        g.sample();
        assertEq(g.latest(), p, "sampled the live price");
        assertFalse(g.ready(), "one sample is not a full window");
        emit log_named_decimal_uint("live XRP/USD", p, 18);
    }
}
