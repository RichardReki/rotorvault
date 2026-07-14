// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol";
import {IYieldVenue} from "./IYieldVenue.sol";

/// The risk-off destination: holds FXRP as-is, zero yield, instant redemption.
contract IdleVenue is IYieldVenue {
    using SafeERC20 for IERC20;

    IERC20 public immutable fxrp;

    constructor(address fxrp_) {
        fxrp = IERC20(fxrp_);
    }

    function asset() external view returns (address) {
        return address(fxrp);
    }

    function deposit(uint256 assets) external returns (uint256) {
        fxrp.safeTransferFrom(msg.sender, address(this), assets);
        return assets;
    }

    function positionValue() external view returns (uint256) {
        return fxrp.balanceOf(address(this));
    }

    function requestRedeem(uint256 assets) external returns (uint256 claimableAt) {
        fxrp.safeTransfer(msg.sender, assets);
        return 0; // instant
    }

    function claimMatured() external pure returns (uint256) {
        return 0;
    }

    function isInstant() external pure returns (bool) {
        return true;
    }
}
