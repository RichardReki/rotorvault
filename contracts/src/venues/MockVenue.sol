// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol";
import {IYieldVenue} from "./IYieldVenue.sol";

/// A minimal async yield venue used as a fallback (if a live testnet vault is flaky) and in unit tests.
/// Models the essential shape of Firelight/Upshift: synchronous deposit, delayed (lagged) redemption,
/// and a simple flat yield applied on redemption. NOT for production value.
contract MockVenue is IYieldVenue {
    using SafeERC20 for IERC20;

    IERC20 public immutable fxrp;
    uint256 public immutable lag; // seconds until a redemption matures
    uint256 public yieldBps; // flat yield applied to redeemed principal
    uint256 public principal; // FXRP currently deployed

    struct Pending {
        uint256 claimableAt;
        uint256 amount;
    }

    Pending[] public pending;

    constructor(address fxrp_, uint256 lag_, uint256 yieldBps_) {
        fxrp = IERC20(fxrp_);
        lag = lag_;
        yieldBps = yieldBps_;
    }

    function asset() external view returns (address) {
        return address(fxrp);
    }

    function deposit(uint256 assets) external returns (uint256) {
        fxrp.safeTransferFrom(msg.sender, address(this), assets);
        principal += assets;
        return assets;
    }

    function positionValue() external view returns (uint256) {
        return principal + (principal * yieldBps) / 10_000;
    }

    function requestRedeem(uint256 assets) external returns (uint256 claimableAt) {
        require(assets <= principal, "MockVenue: exceeds principal");
        principal -= assets;
        uint256 payout = assets + (assets * yieldBps) / 10_000;
        claimableAt = block.timestamp + lag;
        pending.push(Pending(claimableAt, payout));
    }

    function claimMatured() external returns (uint256 delivered) {
        uint256 i;
        while (i < pending.length) {
            if (pending[i].claimableAt <= block.timestamp) {
                delivered += pending[i].amount;
                pending[i] = pending[pending.length - 1];
                pending.pop();
            } else {
                i++;
            }
        }
        if (delivered > 0) fxrp.safeTransfer(msg.sender, delivered);
    }

    function isInstant() external pure returns (bool) {
        return false;
    }

    /// test/demo helper
    function setYieldBps(uint256 b) external {
        yieldBps = b;
    }
}
