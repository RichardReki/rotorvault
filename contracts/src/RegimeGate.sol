// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {FlareResolver} from "./lib/FlareResolver.sol";

/// On-chain regime gate driven by FTSOv2. Block-latency feeds keep NO on-chain history, so the gate
/// self-samples XRP/USD into a ring buffer and computes an SMA. riskOn() = latest price >= SMA once the
/// buffer is full. This is the load-bearing "FTSO drives contract logic" component: RotorVault forces a
/// risk-off allocation whenever riskOn() is false, regardless of any off-chain agent's proposal.
contract RegimeGate {
    // XRP/USD block-latency feed id (category 01 = Crypto)
    bytes21 public constant XRP_USD = 0x015852502f55534400000000000000000000000000;
    uint256 public constant N = 20; // SMA window / ring size

    uint256 public immutable minInterval; // min seconds between samples
    uint256[N] private _buf;
    uint256 private _count;
    uint256 private _head;
    uint64 public lastSampled;

    event Sampled(uint256 price1e18, uint256 sma, bool riskOn, uint64 ts);

    constructor(uint256 minInterval_) {
        minInterval = minInterval_;
    }

    /// Read the live XRP/USD price normalized to 1e18, reading decimals per-call (never hardcode them).
    function currentPrice1e18() public view returns (uint256) {
        (uint256 v, int8 dec,) = FlareResolver.ftso().getFeedById(XRP_USD);
        require(dec >= 0 && dec <= 18, "RegimeGate: bad feed decimals");
        return v * (10 ** uint256(int256(18) - int256(dec)));
    }

    /// Append the current live price to the ring buffer (respecting minInterval).
    function sample() external {
        require(block.timestamp >= lastSampled + minInterval, "RegimeGate: too soon");
        uint256 p = currentPrice1e18();
        _store(p, uint64(block.timestamp));
        emit Sampled(p, sma(), riskOn(), uint64(block.timestamp));
    }

    function _store(uint256 p, uint64 ts) internal {
        _buf[_head] = p;
        _head = (_head + 1) % N;
        if (_count < N) _count++;
        lastSampled = ts;
    }

    function sma() public view returns (uint256) {
        if (_count == 0) return 0;
        uint256 s;
        for (uint256 i; i < _count; i++) s += _buf[i];
        return s / _count;
    }

    function latest() public view returns (uint256) {
        if (_count == 0) return 0;
        return _buf[(_head + N - 1) % N];
    }

    function ready() public view returns (bool) {
        return _count >= N;
    }

    /// Risk-on once the window is full and the latest sample is at or above the SMA.
    function riskOn() public view returns (bool) {
        return _count >= N && latest() >= sma();
    }
}
