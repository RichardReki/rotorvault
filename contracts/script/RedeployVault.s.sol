// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Script, console2} from "forge-std/Script.sol";
import {FlareResolver} from "../src/lib/FlareResolver.sol";
import {FirelightAdapter} from "../src/venues/FirelightAdapter.sol";
import {UpshiftAdapter} from "../src/venues/UpshiftAdapter.sol";
import {RotorVault} from "../src/RotorVault.sol";

/// Redeploys RotorVault (now FDC-load-bearing: rebalance() reads ApyOracle.apy()/updatedAt) plus fresh
/// adapters, REUSING the existing RegimeGate and ApyOracle. Reuse matters: the keeper keeps priming the
/// same gate (no warmup reset) and the live FDC proof txs (submitApy -> apy()=800) stay valid. The old
/// adapters are permanently owned by the old vault (no re-point path), so fresh adapters are required.
///
///   Simulate (no key):  forge script script/RedeployVault.s.sol --rpc-url coston2
///   Broadcast (USER):   forge script script/RedeployVault.s.sol --rpc-url coston2 --broadcast --private-key $DEPLOYER_PRIVATE_KEY --legacy
contract RedeployVault is Script {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;
    address constant UPSHIFT = 0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81;
    address constant GATE = 0xc3762daB9AB246771a91B764d0E45f03619A61ea; // reuse: keeper is priming it
    address constant APY_ORACLE = 0xD3103fb1189a6f21C72387efab1c77aaF79803cF; // reuse: apy()=800, FDC proofs valid

    function run() external {
        address fxrp = FlareResolver.fxrp();

        vm.startBroadcast();
        FirelightAdapter fire = new FirelightAdapter(FIRELIGHT, msg.sender);
        UpshiftAdapter up = new UpshiftAdapter(UPSHIFT, msg.sender);
        RotorVault vault = new RotorVault(fxrp, GATE, address(fire), address(up), APY_ORACLE);
        fire.setOwner(address(vault));
        up.setOwner(address(vault));
        vm.stopBroadcast();

        console2.log("FXRP (resolved)   ", fxrp);
        console2.log("RegimeGate (reuse)", GATE);
        console2.log("ApyOracle (reuse) ", APY_ORACLE);
        console2.log("FirelightAdapter  ", address(fire));
        console2.log("UpshiftAdapter    ", address(up));
        console2.log("RotorVault (NEW)  ", address(vault));
    }
}
