// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {RegimeGate} from "../src/RegimeGate.sol";

/// Exposes the internal ring-buffer store so the SMA + hysteresis logic can be unit-tested without an oracle.
contract RegimeGateHarness is RegimeGate {
    constructor(uint256 minInterval_, uint256 band_) RegimeGate(minInterval_, band_) {}
    function push(uint256 price1e18) external {
        _store(price1e18, uint64(block.timestamp));
    }
}

contract RegimeGateTest is Test {
    function test_notReadyUntilBufferFull() public {
        RegimeGateHarness g = new RegimeGateHarness(60, 100);
        for (uint256 i; i < g.N() - 1; i++) g.push(100e18);
        assertFalse(g.ready());
        assertFalse(g.riskOn(), "no signal until full");
    }

    function test_hysteresisFlipsOnDeviationFromTrend() public {
        RegimeGateHarness g = new RegimeGateHarness(60, 100); // 1% deadband
        for (uint256 i; i < g.N(); i++) g.push(100e18);
        assertTrue(g.ready());
        assertFalse(g.riskOn(), "flat price at trend is NOT risk-on (needs >1% above trend)");

        g.push(300e18); // spike well above the window mean -> risk-on
        assertTrue(g.riskOn(), "deviation above trend -> risk-on");

        g.push(10e18); // drop well below the window mean -> risk-off
        assertFalse(g.riskOn(), "deviation below trend -> risk-off");
    }
}
