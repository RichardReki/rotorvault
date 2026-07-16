// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin-contracts/token/ERC20/ERC20.sol";
import {RotorVault} from "../src/RotorVault.sol";
import {MockVenue} from "../src/venues/MockVenue.sol";
import {IRegimeGate} from "../src/interfaces/IRegimeGate.sol";

contract MintFXRP is ERC20 {
    constructor() ERC20("FTestXRP", "FXRP") {}
    function mint(address t, uint256 a) external { _mint(t, a); }
    function decimals() public pure override returns (uint8) { return 6; }
}

contract MockGate is IRegimeGate {
    bool public on = true;
    function setOn(bool v) external { on = v; }
    function riskOn() external view returns (bool) { return on; }
}

contract RotorVaultTest is Test {
    MintFXRP fxrp;
    MockGate gate;
    MockVenue fire;
    MockVenue up;
    RotorVault vault;

    function setUp() public {
        fxrp = new MintFXRP();
        gate = new MockGate();
        fire = new MockVenue(address(fxrp), 1 days, 0); // yield-free for clean NAV assertions
        up = new MockVenue(address(fxrp), 1 days, 0);
        vault = new RotorVault(address(fxrp), address(gate), address(fire), address(up));
        vault.setAgent(address(this));
        fxrp.mint(address(this), 1_000e6);
    }

    function _deposit(uint256 a) internal {
        fxrp.approve(address(vault), a);
        vault.deposit(a, address(this));
    }

    function test_depositMintsSharesOneToOne() public {
        _deposit(100e6);
        assertEq(vault.balanceOf(address(this)), 100e6);
        assertEq(vault.totalAssets(), 100e6);
    }

    function test_riskOnRebalanceDeploys() public {
        _deposit(100e6);
        vault.rebalance(4000, 4000); // 40% fire, 40% up, 20% idle
        assertEq(fire.positionValue(), 40e6);
        assertEq(up.positionValue(), 40e6);
        assertEq(fxrp.balanceOf(address(vault)), 20e6, "20% stays idle");
        assertEq(vault.totalAssets(), 100e6, "NAV conserved");
    }

    function test_ftsoGateForcesRiskOff() public {
        _deposit(100e6);
        vault.rebalance(5000, 5000); // deploy 50/50
        assertEq(fxrp.balanceOf(address(vault)), 0);

        gate.setOn(false); // FTSO says risk-off
        vault.rebalance(5000, 5000); // agent still proposes 50/50, but gate overrides -> requestRedeem all
        assertEq(fire.positionValue(), 0, "pulled out of firelight");
        assertEq(up.positionValue(), 0, "pulled out of upshift");

        // funds are in-flight; claim after the venue lag returns them to idle
        vm.warp(block.timestamp + 1 days + 1);
        uint256 delivered = vault.claimMatured();
        assertEq(delivered, 100e6, "all FXRP returned");
        assertEq(fxrp.balanceOf(address(vault)), 100e6, "back to idle");
    }

    function test_withdrawFromIdle() public {
        _deposit(100e6);
        uint256 before = fxrp.balanceOf(address(this));
        uint256 assets = vault.withdraw(40e6, address(this)); // 40% of shares
        assertEq(assets, 40e6);
        assertEq(fxrp.balanceOf(address(this)), before + 40e6);
        assertEq(vault.totalAssets(), 60e6);
    }

    function test_withdrawRevertsWhenDeployed() public {
        _deposit(100e6);
        vault.rebalance(10000, 0); // deploy everything to firelight
        vm.expectRevert(bytes("RotorVault: insufficient idle; claimMatured/rebalance first"));
        vault.withdraw(50e6, address(this));
    }

    function test_onlyAgentCanRebalance() public {
        _deposit(100e6);
        vm.prank(address(0xBEEF));
        vm.expectRevert(bytes("RotorVault: not agent"));
        vault.rebalance(5000, 5000);
    }

    function test_inflightKeepsNavContinuous() public {
        _deposit(100e6);
        vault.rebalance(6000, 0); // 60 into firelight, 40 idle
        assertEq(fire.positionValue(), 60e6);

        vault.rebalance(0, 0); // request the 60 out of firelight -> in-flight
        assertEq(fire.positionValue(), 0);
        assertEq(vault.inflight(), 60e6);
        assertEq(fxrp.balanceOf(address(vault)), 40e6);
        assertEq(vault.totalAssets(), 100e6, "NAV = idle 40 + in-flight 60 (continuous)");

        // a deposit mid-in-flight mints FAIR shares against the true 100 NAV (no dilution)
        fxrp.approve(address(vault), 50e6);
        uint256 sh = vault.deposit(50e6, address(this));
        assertEq(sh, 50e6, "50 FXRP -> 50 shares vs 100 NAV / 100 supply");
    }
}
