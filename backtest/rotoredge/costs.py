"""4-part BSC / PancakeSwap cost model, charged on the realized fill BEFORE any metric.

All inputs/outputs are fractions of current portfolio value V. A trade vector is
(target_weights - current_weights). Costs:
  1. swap fee        : fee_bps on traded notional
  2. AMM price impact: linear constant-product proxy  impact_i = traded_usd_i / pool_depth
  3. slippage buffer : buffer_bps on traded notional (adverse fill / MEV)
  4. gas             : fixed gas_usd per swapped name (BSC) -> kills tiny/high-freq trades
Round-trip ~ 2x(fee+impact+buffer) + 2x gas across a full enter+exit cycle.
"""
from __future__ import annotations

import numpy as np


def compute_cost(current_w: np.ndarray, target_w: np.ndarray, cfg: dict, mult: float = 1.0) -> dict:
    """Return cost as a fraction of portfolio value, with a breakdown. mult scales ALL costs."""
    c = cfg["costs"]
    fee_bps = float(c["fee_bps"])
    buffer_bps = float(c["buffer_bps"])
    gas_usd = float(c["gas_usd"])
    pool_depth = float(c["pool_depth_usd"])
    notional = float(c["notional_usd"])

    trade = np.abs(np.asarray(target_w, float) - np.asarray(current_w, float))
    eps = 1e-9
    traded = trade[trade > eps]
    turnover = float(traded.sum())
    n_trades = int(traded.size)

    fee = turnover * fee_bps / 1e4
    buf = turnover * buffer_bps / 1e4
    # per-name linear AMM impact: traded_usd/pool_depth, paid on the traded fraction
    impact = float(np.sum(traded * (traded * notional / pool_depth)))
    gas = n_trades * gas_usd / notional

    total = (fee + buf + impact + gas) * mult
    return {
        "total": total,
        "turnover": turnover,
        "n_trades": n_trades,
        "fee": fee * mult,
        "buffer": buf * mult,
        "impact": impact * mult,
        "gas": gas * mult,
    }
