// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol";
import {IYieldVenue} from "./IYieldVenue.sol";
import {IFirelightVault} from "../interfaces/IFirelightVault.sol";

/// Wraps the live Firelight FXRP liquid-staking vault behind the uniform IYieldVenue interface.
/// Deposits are synchronous; redemptions are delayed (burn shares now, claim FXRP after the period).
contract FirelightAdapter is IYieldVenue {
    using SafeERC20 for IERC20;

    IFirelightVault public immutable firelight; // also the stFXRP share token
    IERC20 public immutable fxrp;
    address public owner; // the RotorVault; deposits pulled from / redemptions returned to it

    uint256[] public pendingPeriods;
    mapping(uint256 => bool) public tracked;

    constructor(address firelight_, address owner_) {
        firelight = IFirelightVault(firelight_);
        fxrp = IERC20(firelight.asset());
        owner = owner_;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "FirelightAdapter: not owner");
        _;
    }

    /// One-time hand-off from the deployer to the RotorVault after deployment.
    function setOwner(address o) external onlyOwner {
        owner = o;
    }

    function asset() external view returns (address) {
        return address(fxrp);
    }

    function deposit(uint256 assets) external onlyOwner returns (uint256) {
        fxrp.safeTransferFrom(msg.sender, address(this), assets);
        fxrp.forceApprove(address(firelight), assets);
        firelight.deposit(assets, address(this));
        return assets;
    }

    function positionValue() external view returns (uint256) {
        return firelight.convertToAssets(firelight.balanceOf(address(this)));
    }

    function requestRedeem(uint256 assets) external onlyOwner returns (uint256 claimableAt) {
        uint256 shares = firelight.convertToShares(assets);
        // Firelight records a redeem made in period P as claimable in the NEXT period (P+1),
        // and claimWithdraw(P+1) only succeeds once currentPeriod() > P+1.
        uint256 wp = firelight.currentPeriod() + 1;
        firelight.redeem(shares, address(this), address(this));
        if (!tracked[wp]) {
            tracked[wp] = true;
            pendingPeriods.push(wp);
        }
        // Claimable once period wp ends: end of current period + one full period duration.
        uint256 periodDuration = firelight.currentPeriodEnd() - firelight.currentPeriodStart();
        claimableAt = uint256(firelight.currentPeriodEnd()) + periodDuration;
    }

    function claimMatured() external onlyOwner returns (uint256 delivered) {
        uint256 cur = firelight.currentPeriod();
        uint256 i;
        while (i < pendingPeriods.length) {
            uint256 p = pendingPeriods[i];
            if (cur > p && firelight.withdrawalsOf(p, address(this)) > 0) {
                delivered += firelight.claimWithdraw(p);
                pendingPeriods[i] = pendingPeriods[pendingPeriods.length - 1];
                pendingPeriods.pop();
                tracked[p] = false;
            } else {
                i++;
            }
        }
        if (delivered > 0) fxrp.safeTransfer(owner, delivered);
    }

    function isInstant() external pure returns (bool) {
        return false;
    }
}
