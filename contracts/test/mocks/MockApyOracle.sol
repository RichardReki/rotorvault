// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {IApyOracle} from "../../src/interfaces/IApyOracle.sol";

/// Test double for ApyOracle: settable APY (bips) + updatedAt, so vault tests can drive the
/// FDC freshness/floor guard (fresh -> Upshift may deploy; zero or stale -> Upshift forced idle).
contract MockApyOracle is IApyOracle {
    uint256 public apyBips;
    uint256 public updatedAt;

    constructor(uint256 bips, uint256 at) {
        apyBips = bips;
        updatedAt = at;
    }

    function set(uint256 bips, uint256 at) external {
        apyBips = bips;
        updatedAt = at;
    }

    function apy() external view returns (uint256) {
        return apyBips;
    }
}
