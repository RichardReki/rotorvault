// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

/// Minimal surface of the Upshift FXRP vault (Coston2 0x24c1a47c…), Flare ITokenizedVault form.
/// Shares are a SEPARATE ERC-20 (lpTokenAddress). Redemptions: instant (higher fee) or requested
/// (lower fee, ~24h lag, claimed by the returned UTC date). Never hardcode fees — use previewRedemption.
interface IUpshiftVault {
    function asset() external view returns (address);
    function lpTokenAddress() external view returns (address);
    function lagDuration() external view returns (uint256);
    function withdrawalFee() external view returns (uint256);
    function instantRedemptionFee() external view returns (uint256);

    function deposit(address assetIn, uint256 amountIn, address receiver) external returns (uint256 shares);
    function instantRedeem(uint256 shares, address receiver) external returns (uint256 assets);
    function requestRedeem(uint256 shares, address receiver)
        external
        returns (uint256 claimableEpoch, uint32 year, uint32 month, uint32 day);
    function claim(uint32 year, uint32 month, uint32 day, address receiver)
        external
        returns (uint256 shares, uint256 assetsAfterFee);
    function previewRedemption(uint256 shares, bool isInstant)
        external
        view
        returns (uint256 assetsAmount, uint256 assetsAfterFee);
}
