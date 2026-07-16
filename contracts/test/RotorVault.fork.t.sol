// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {RotorVault} from "../src/RotorVault.sol";
import {RegimeGate} from "../src/RegimeGate.sol";
import {FirelightAdapter} from "../src/venues/FirelightAdapter.sol";
import {UpshiftAdapter} from "../src/venues/UpshiftAdapter.sol";

/// End-to-end: the REAL RotorVault + RegimeGate(live FTSO) + adapters over the REAL Coston2 Firelight
/// and Upshift vaults. Proves deposit -> FTSO-gated rebalance into live venues -> claim cycle on-chain.
contract RotorVaultForkTest is Test {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;
    address constant UPSHIFT = 0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81;

    RegimeGate gate;
    FirelightAdapter fire;
    UpshiftAdapter up;
    RotorVault vault;
    IERC20 fxrp;

    function setUp() public {
        vm.createSelectFork(vm.envString("COSTON2_RPC_URL"));
        gate = new RegimeGate(0, 0);
        fire = new FirelightAdapter(FIRELIGHT, address(this));
        up = new UpshiftAdapter(UPSHIFT, address(this));
        vault = new RotorVault(fire.asset(), address(gate), address(fire), address(up));
        fire.setOwner(address(vault));
        up.setOwner(address(vault));
        fxrp = IERC20(fire.asset());

        // fund the test with FXRP from a real holder (the Firelight vault holds ~15 FXRP)
        vm.prank(FIRELIGHT);
        fxrp.transfer(address(this), 10e6);
    }

    // fill the gate's ring buffer with live samples so riskOn() becomes true
    function _primeRiskOn() internal {
        for (uint256 i; i < gate.N(); i++) {
            gate.sample();
        }
        assertTrue(gate.riskOn(), "gate primed risk-on");
    }

    function _deposit(uint256 a) internal {
        fxrp.approve(address(vault), a);
        vault.deposit(a, address(this));
    }

    function test_deployIntoRealVenues() public {
        _deposit(4e6);
        _primeRiskOn();

        vault.rebalance(4000, 4000); // 40% Firelight, 40% Upshift, 20% idle
        assertGt(fire.positionValue(), 0, "deployed into live Firelight");
        assertGt(up.positionValue(), 0, "deployed into live Upshift");
        assertApproxEqAbs(fxrp.balanceOf(address(vault)), 0.8e6, 5e4, "~20% idle");
        // NAV roughly conserved (small entry differences on the live vaults)
        assertApproxEqAbs(vault.totalAssets(), 4e6, 1e5, "NAV ~= deposit");
    }

    function test_firelightRedeemCycleThroughVault() public {
        _deposit(4e6);
        _primeRiskOn();

        vault.rebalance(10000, 0); // all into Firelight
        assertApproxEqAbs(fire.positionValue(), 4e6, 1e5, "all deployed to Firelight");

        vault.rebalance(0, 0); // request full redemption from Firelight
        assertEq(fire.positionValue(), 0, "Firelight position requested out");

        // advance past Firelight's withdrawal period, then claim back into the vault
        vm.warp(block.timestamp + 3 days);
        vm.roll(block.number + 1);
        uint256 idleBefore = fxrp.balanceOf(address(vault));
        vault.claimMatured();
        assertGt(fxrp.balanceOf(address(vault)), idleBefore, "FXRP returned to vault idle");
    }
}
