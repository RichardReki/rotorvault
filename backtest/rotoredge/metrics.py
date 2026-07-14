"""Performance metrics, incl. the Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)
to honestly correct for the number of strategy variants tried."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

YEAR = 365  # crypto trades every calendar day


def to_equity(daily_returns: pd.Series) -> pd.Series:
    return (1.0 + daily_returns.fillna(0.0)).cumprod()


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def max_drawdown(equity: pd.Series) -> float:
    return float(drawdown(equity).min())


def drawdown_duration_days(equity: pd.Series) -> int:
    """Longest stretch (in days) the curve spent below a prior peak."""
    dd = drawdown(equity)
    longest = cur = 0
    for v in dd.values:
        cur = cur + 1 if v < 0 else 0
        longest = max(longest, cur)
    return int(longest)


def ann_return(daily_returns: pd.Series) -> float:
    r = daily_returns.fillna(0.0)
    n = len(r)
    if n == 0:
        return 0.0
    total = float((1.0 + r).prod())
    if total <= 0:
        return -1.0
    return total ** (YEAR / n) - 1.0


def ann_vol(daily_returns: pd.Series) -> float:
    return float(daily_returns.std(ddof=1) * np.sqrt(YEAR))


def sharpe(daily_returns: pd.Series, rf: float = 0.0) -> float:
    r = daily_returns.dropna() - rf / YEAR
    sd = r.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float(r.mean() / sd * np.sqrt(YEAR))


def sortino(daily_returns: pd.Series, rf: float = 0.0) -> float:
    r = daily_returns.dropna() - rf / YEAR
    downside = r[r < 0]
    dd = downside.std(ddof=1)
    if dd == 0 or np.isnan(dd) or len(downside) == 0:
        return 0.0
    return float(r.mean() / dd * np.sqrt(YEAR))


def calmar(daily_returns: pd.Series) -> float:
    eq = to_equity(daily_returns)
    mdd = abs(max_drawdown(eq))
    if mdd == 0:
        return 0.0
    return ann_return(daily_returns) / mdd


def period_stats(period_returns: pd.Series) -> dict:
    """Hit rate / payoff / profit factor over per-rebalance-period returns."""
    r = period_returns.dropna()
    r = r[r != 0.0]
    n = len(r)
    if n == 0:
        return {"n_trades": 0, "hit_rate": 0.0, "payoff": 0.0, "profit_factor": 0.0}
    wins, losses = r[r > 0], r[r < 0]
    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    payoff = (wins.mean() / -losses.mean()) if len(wins) and len(losses) else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    return {
        "n_trades": int(n),
        "hit_rate": float(len(wins) / n),
        "payoff": float(payoff),
        "profit_factor": float(pf),
    }


def summarize(daily_returns: pd.Series, period_returns: pd.Series | None = None) -> dict:
    eq = to_equity(daily_returns)
    out = {
        "total_return": float(eq.iloc[-1] - 1.0) if len(eq) else 0.0,
        "cagr": ann_return(daily_returns),
        "ann_vol": ann_vol(daily_returns),
        "sharpe": sharpe(daily_returns),
        "sortino": sortino(daily_returns),
        "calmar": calmar(daily_returns),
        "max_drawdown": max_drawdown(eq),
        "max_dd_duration_days": drawdown_duration_days(eq),
        "n_days": int(len(daily_returns)),
    }
    if period_returns is not None:
        out.update(period_stats(period_returns))
    return out


# ---- Deflated Sharpe Ratio ----------------------------------------------------

def probabilistic_sharpe_ratio(sr_obs: float, n: int, skew: float, kurt: float, sr_benchmark: float) -> float:
    """PSR: probability the true (per-observation) Sharpe exceeds sr_benchmark."""
    denom = np.sqrt(max(1e-12, 1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2))
    z = (sr_obs - sr_benchmark) * np.sqrt(max(1, n - 1)) / denom
    return float(norm.cdf(z))


def expected_max_sharpe(var_sr: float, n_trials: int) -> float:
    """Expected maximum (per-observation) Sharpe across n_trials independent trials."""
    if n_trials <= 1 or var_sr <= 0:
        return 0.0
    g = 0.5772156649  # Euler-Mascheroni
    e = np.e
    return float(np.sqrt(var_sr) * ((1 - g) * norm.ppf(1 - 1.0 / n_trials) + g * norm.ppf(1 - 1.0 / (n_trials * e))))


def deflated_sharpe_ratio(daily_returns: pd.Series, trial_sharpes_annual: list[float], n_trials: int | None = None) -> dict:
    """DSR: PSR against the benchmark = expected max Sharpe given how many variants we tried.

    trial_sharpes_annual: the ANNUALISED Sharpe of every variant evaluated (for the
    variance-of-trials term). n_trials defaults to len(trial_sharpes_annual).
    """
    r = daily_returns.dropna()
    n = len(r)
    if n < 5:
        return {"dsr": 0.0, "sr_benchmark_annual": 0.0, "n_trials": n_trials or 0}
    sr_obs = r.mean() / r.std(ddof=1) if r.std(ddof=1) > 0 else 0.0  # per-observation
    skew = float(r.skew())
    kurt = float(r.kurt() + 3.0)  # pandas kurt is excess; DSR uses raw kurtosis
    trials = np.asarray(trial_sharpes_annual, float) / np.sqrt(YEAR)  # -> per-observation
    nt = int(n_trials or len(trials))
    var_sr = float(np.var(trials, ddof=1)) if trials.size > 1 else (1.0 / n)
    sr_bench = expected_max_sharpe(var_sr, nt)
    dsr = probabilistic_sharpe_ratio(sr_obs, n, skew, kurt, sr_bench)
    return {
        "dsr": dsr,
        "sr_benchmark_annual": float(sr_bench * np.sqrt(YEAR)),
        "sr_strategy_annual": float(sr_obs * np.sqrt(YEAR)),
        "skew": skew,
        "kurtosis": kurt,
        "n_trials": nt,
    }
