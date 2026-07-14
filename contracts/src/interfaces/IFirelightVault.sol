// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.25;

/// Minimal, verified surface of the Firelight FXRP vault (Coston2 0x91Bfe6…).
/// The vault IS its own stFXRP share token (6 dp). Deposits are synchronous; withdrawals/redeems
/// burn shares immediately and create a request for currentPeriod(), delivering FXRP only via
/// claimWithdraw(period) once that period has ended. (Ref: flare-hardhat-starter IFirelightVault.sol)
interface IFirelightVault {
    function asset() external view returns (address);
    function deposit(uint256 assets, address receiver) external returns (uint256 shares);
    function redeem(uint256 shares, address receiver, address owner) external returns (uint256 assets);
    function claimWithdraw(uint256 period) external returns (uint256 assets);
    function currentPeriod() external view returns (uint256);
    function currentPeriodStart() external view returns (uint48);
    function currentPeriodEnd() external view returns (uint48);
    function convertToAssets(uint256 shares) external view returns (uint256);
    function convertToShares(uint256 assets) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function withdrawalsOf(uint256 period, address account) external view returns (uint256);
    function isWithdrawClaimed(uint256 period, address account) external view returns (bool);
}
