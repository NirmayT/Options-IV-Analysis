import numpy as np
import pandas as pd
from scipy.stats import norm
import config


def black_scholes_call(S, K, T_days, volatility,
                       r=config.RISK_FREE_RATE, q=0.0):
    """European call approximation with continuous dividend yield."""
    values = (S, K, T_days, volatility, r, q)
    if any(pd.isna(v) for v in values):
        return np.nan
    if T_days <= 0:
        return max(0.0, S - K)
    if volatility <= 0 or S <= 0 or K <= 0:
        return np.nan

    t = T_days / 365.0
    try:
        d1 = (np.log(S / K) + (r - q + 0.5 * volatility ** 2) * t) / (
            volatility * np.sqrt(t)
        )
        d2 = d1 - volatility * np.sqrt(t)
        price = (
            S * np.exp(-q * t) * norm.cdf(d1)
            - K * np.exp(-r * t) * norm.cdf(d2)
        )
        return max(0.0, float(price))
    except Exception:
        return np.nan


def calculate_theoretical_prices(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bs_theoretical_price"] = [
        black_scholes_call(S, K, T, vol, r, q)
        for S, K, T, vol, r, q in zip(
            out["underlying_price"], out["strike"], out["days_to_expiry"],
            out["yahoo_iv"], out["risk_free_rate"], out["dividend_yield"]
        )
    ]
    return out
