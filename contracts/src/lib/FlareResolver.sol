// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {ContractRegistry} from "flare-periphery/src/coston2/ContractRegistry.sol";
import {IAssetManager} from "flare-periphery/src/coston2/IAssetManager.sol";
import {TestFtsoV2Interface} from "flare-periphery/src/coston2/TestFtsoV2Interface.sol";
import {IFdcVerification} from "flare-periphery/src/coston2/IFdcVerification.sol";

/// Runtime resolution of Flare protocol contracts via the FlareContractRegistry
/// (0xaD67…6019, identical on every network). Never hardcode FXRP — genuine FXRP is 6 decimals.
library FlareResolver {
    function assetManagerFXRP() internal view returns (IAssetManager) {
        return ContractRegistry.getAssetManagerFXRP();
    }

    /// The FXRP ERC-20 (FAsset) address, resolved at runtime.
    function fxrp() internal view returns (address) {
        return address(ContractRegistry.getAssetManagerFXRP().fAsset());
    }

    /// Free/view FTSOv2 reader (Coston2); use ContractRegistry.getFtsoV2() (payable) for production.
    function ftso() internal view returns (TestFtsoV2Interface) {
        return ContractRegistry.getTestFtsoV2();
    }

    function fdc() internal view returns (IFdcVerification) {
        return ContractRegistry.getFdcVerification();
    }
}
