"""BSC cost model behaviour: zero on no-trade, scales with the multiplier and turnover."""
import numpy as np

from rotoredge.config import load_config
from rotoredge.costs import compute_cost

CFG = load_config()


def test_no_trade_is_zero_cost():
    w = np.array([0.3, 0.3, 0.0])
    c = compute_cost(w, w, CFG, 1.0)
    assert c["total"] == 0.0 and c["n_trades"] == 0


def test_cost_scales_linearly_with_multiplier():
    cur = np.array([0.0, 0.0, 0.0])
    tgt = np.array([0.3, 0.3, 0.0])
    c1 = compute_cost(cur, tgt, CFG, 1.0)
    c2 = compute_cost(cur, tgt, CFG, 2.0)
    assert c1["n_trades"] == 2 and c1["total"] > 0
    assert abs(c2["total"] - 2.0 * c1["total"]) < 1e-12


def test_more_turnover_costs_more():
    cur = np.zeros(3)
    small = compute_cost(cur, np.array([0.1, 0.0, 0.0]), CFG, 1.0)
    big = compute_cost(cur, np.array([0.5, 0.5, 0.0]), CFG, 1.0)
    assert big["total"] > small["total"]


def test_gas_charged_per_traded_name():
    cur = np.zeros(3)
    one = compute_cost(cur, np.array([0.3, 0.0, 0.0]), CFG, 1.0)
    two = compute_cost(cur, np.array([0.15, 0.15, 0.0]), CFG, 1.0)
    assert two["gas"] > one["gas"]  # 2 swaps cost more gas than 1


if __name__ == "__main__":
    test_no_trade_is_zero_cost(); test_cost_scales_linearly_with_multiplier()
    test_more_turnover_costs_more(); test_gas_charged_per_traded_name()
    print("test_costs: OK")
