// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

/// Uniform adapter over a yield venue. All amounts are FXRP (6 dp). The RotorVault is the
/// only caller. Redemptions may be asynchronous, so the interface separates request from claim.
interface IYieldVenue {
    /// The underlying asset (FXRP).
    function asset() external view returns (address);

    /// Pull `assets` FXRP from the caller (vault) and deploy into the venue. Returns amount deployed.
    function deposit(uint256 assets) external returns (uint256);

    /// Current FXRP value of this venue's position held for the vault.
    function positionValue() external view returns (uint256);

    /// Begin redeeming `assets` FXRP. Instant venues transfer to the caller immediately and return 0;
    /// async venues record the request and return the unix timestamp when claimMatured() can deliver.
    function requestRedeem(uint256 assets) external returns (uint256 claimableAt);

    /// Deliver any matured FXRP back to the caller (vault). Returns the amount delivered (0 if none).
    function claimMatured() external returns (uint256 delivered);

    /// True if redemptions are synchronous (delivered within requestRedeem).
    function isInstant() external view returns (bool);
}
