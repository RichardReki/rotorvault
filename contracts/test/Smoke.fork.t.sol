// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";

interface IERC20Meta {
    function decimals() external view returns (uint8);
    function symbol() external view returns (string memory);
}

interface IFirelightMin {
    function asset() external view returns (address);
    function totalAssets() external view returns (uint256);
    function currentPeriod() external view returns (uint256);
}

/// Smoke test: prove the real Coston2 Firelight vault is reachable and shaped as researched.
contract SmokeForkTest is Test {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;
    address constant FXRP_C2 = 0x0b6A3645c240605887a5532109323A3E12273dc7;

    function setUp() public {
        vm.createSelectFork(vm.envString("COSTON2_RPC_URL"));
    }

    function test_liveFirelightReadable() public {
        IFirelightMin fl = IFirelightMin(FIRELIGHT);
        address asset = fl.asset();
        assertEq(asset, FXRP_C2, "Firelight.asset() should be Coston2 FXRP");
        assertEq(IERC20Meta(asset).decimals(), 6, "FXRP is 6 decimals");
        fl.totalAssets(); // must not revert
        fl.currentPeriod(); // must not revert
        emit log_named_uint("Firelight currentPeriod", fl.currentPeriod());
        emit log_named_uint("Firelight totalAssets (6dp)", fl.totalAssets());
    }
}
