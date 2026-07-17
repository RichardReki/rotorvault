// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

/// The FDC-attested APY oracle, as consumed on-chain by RotorVault. `apy()` returns the last
/// FDC Web2Json-verified venue APY in basis points; `updatedAt()` is when it was stored, so the
/// vault can reject a stale attestation.
interface IApyOracle {
    function apy() external view returns (uint256);
    function updatedAt() external view returns (uint256);
}
