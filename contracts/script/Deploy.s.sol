// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Script, console2} from "forge-std/Script.sol";
import {ContractRegistry} from "flare-periphery/src/coston2/ContractRegistry.sol";
import {FlareResolver} from "../src/lib/FlareResolver.sol";
import {RegimeGate} from "../src/RegimeGate.sol";
import {FirelightAdapter} from "../src/venues/FirelightAdapter.sol";
import {UpshiftAdapter} from "../src/venues/UpshiftAdapter.sol";
import {ApyOracle} from "../src/ApyOracle.sol";
import {RotorVault} from "../src/RotorVault.sol";

/// Deploys the full RotorVault system to Coston2, resolving FXRP/FDC at runtime.
///
///   Simulate (no key):  forge script script/Deploy.s.sol --rpc-url coston2
///   Broadcast (USER):   forge script script/Deploy.s.sol --rpc-url coston2 --broadcast --private-key $DEPLOYER_PRIVATE_KEY
contract Deploy is Script {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;
    address constant UPSHIFT = 0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81;
    uint256 constant GATE_MIN_INTERVAL = 300; // 5 min between FTSO samples (keeper-friendly warmup ~100 min)
    uint256 constant GATE_BAND = 100; // 1% hysteresis deadband
    string constant APY_URL = "https://api.upshift.finance/v1/tokenized_vaults/0x373D7d201C8134D4a2f7b5c63560da217e3dEA28";

    function run() external {
        address fxrp = FlareResolver.fxrp();
        address fdc = address(ContractRegistry.getFdcVerification());

        vm.startBroadcast();
        RegimeGate gate = new RegimeGate(GATE_MIN_INTERVAL, GATE_BAND);
        FirelightAdapter fire = new FirelightAdapter(FIRELIGHT, msg.sender);
        UpshiftAdapter up = new UpshiftAdapter(UPSHIFT, msg.sender);
        ApyOracle oracle = new ApyOracle(fdc, APY_URL);
        RotorVault vault = new RotorVault(fxrp, address(gate), address(fire), address(up));
        fire.setOwner(address(vault));
        up.setOwner(address(vault));
        vm.stopBroadcast();

        console2.log("FXRP (resolved)  ", fxrp);
        console2.log("FdcVerification  ", fdc);
        console2.log("RegimeGate       ", address(gate));
        console2.log("FirelightAdapter ", address(fire));
        console2.log("UpshiftAdapter   ", address(up));
        console2.log("ApyOracle        ", address(oracle));
        console2.log("RotorVault       ", address(vault));
    }
}
