// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {RegimeGate} from "../src/RegimeGate.sol";

/// Exposes the internal ring-buffer store so the SMA/gate math can be unit-tested without an oracle.
contract RegimeGateHarness is RegimeGate {
    constructor(uint256 minInterval_) RegimeGate(minInterval_) {}
    function push(uint256 price1e18) external {
        _store(price1e18, uint64(block.timestamp));
    }
}

contract RegimeGateTest is Test {
    function test_notReadyUntilBufferFull() public {
        RegimeGateHarness g = new RegimeGateHarness(60);
        for (uint256 i; i < g.N() - 1; i++) g.push(100e18);
        assertFalse(g.ready());
        assertFalse(g.riskOn(), "no signal until full");
    }

    function test_riskOnFlipsOnCross() public {
        RegimeGateHarness g = new RegimeGateHarness(60);
        for (uint256 i; i < g.N(); i++) g.push(100e18);
        assertTrue(g.ready());
        assertEq(g.sma(), 100e18);
        assertEq(g.latest(), 100e18);
        assertTrue(g.riskOn(), "latest == sma is risk-on");

        // one sharp drop pulls latest below the (barely moved) SMA
        g.push(50e18);
        assertLt(g.latest(), g.sma());
        assertFalse(g.riskOn(), "drawdown -> risk-off");

        // sustained higher prices lift latest back above the SMA
        for (uint256 i; i < g.N(); i++) g.push(200e18);
        assertEq(g.latest(), 200e18);
        assertTrue(g.riskOn(), "recovery -> risk-on");
    }
}
