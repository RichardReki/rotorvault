// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol";
import {IYieldVenue} from "./IYieldVenue.sol";
import {IUpshiftVault} from "../interfaces/IUpshiftVault.sol";

/// Wraps the live Upshift FXRP vault. Deposits are synchronous. Redemptions use the REQUESTED path
/// (lower fee, ~24h lag, claimed by the returned UTC date); the vault operator must fulfill the epoch
/// before claim() delivers, so claimMatured() try/catches each pending date and delivers what is ready.
/// Shares are a separate LP ERC-20 that must be approved back to the vault before a redeem request.
contract UpshiftAdapter is IYieldVenue {
    using SafeERC20 for IERC20;

    IUpshiftVault public immutable up;
    IERC20 public immutable fxrp;
    IERC20 public immutable lp;
    address public owner;

    struct Req {
        uint32 y;
        uint32 m;
        uint32 d;
    }

    Req[] public pending;

    constructor(address upshift_, address owner_) {
        up = IUpshiftVault(upshift_);
        fxrp = IERC20(up.asset());
        lp = IERC20(up.lpTokenAddress());
        owner = owner_;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "UpshiftAdapter: not owner");
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
        fxrp.forceApprove(address(up), assets);
        up.deposit(address(fxrp), assets, address(this));
        return assets;
    }

    /// Net FXRP value of the LP shares held (requested-path preview, AFTER the withdrawal fee).
    function positionValue() external view returns (uint256) {
        uint256 shares = lp.balanceOf(address(this));
        if (shares == 0) return 0;
        (, uint256 assetsAfterFee) = up.previewRedemption(shares, false);
        return assetsAfterFee;
    }

    function requestRedeem(uint256 assets) external onlyOwner returns (uint256 claimableAt) {
        uint256 shares = lp.balanceOf(address(this));
        require(shares > 0, "UpshiftAdapter: no position");
        (uint256 pv,) = up.previewRedemption(shares, false);
        uint256 sharesToRedeem = (pv == 0 || assets >= pv) ? shares : (shares * assets) / pv;

        lp.forceApprove(address(up), sharesToRedeem);
        (uint256 epoch, uint32 y, uint32 m, uint32 d) = up.requestRedeem(sharesToRedeem, address(this));
        pending.push(Req(y, m, d));
        claimableAt = epoch;
    }

    /// Claim every pending redemption whose epoch the operator has fulfilled; deliver FXRP to the owner.
    function claimMatured() external onlyOwner returns (uint256 delivered) {
        uint256 i;
        while (i < pending.length) {
            Req memory r = pending[i];
            try up.claim(r.y, r.m, r.d, address(this)) returns (uint256, uint256) {
                pending[i] = pending[pending.length - 1];
                pending.pop();
            } catch {
                i++; // epoch not fulfilled yet; retry on a later call
            }
        }
        delivered = fxrp.balanceOf(address(this));
        if (delivered > 0) fxrp.safeTransfer(owner, delivered);
    }

    function pendingCount() external view returns (uint256) {
        return pending.length;
    }

    function isInstant() external pure returns (bool) {
        return false;
    }
}
