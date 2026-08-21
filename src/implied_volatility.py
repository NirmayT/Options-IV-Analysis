import numpy as np
import pandas as pd
import config
from black_scholes import black_scholes_call


def calculate_implied_volatility(S, K, T_days, market_price,
                                 r=config.RISK_FREE_RATE, q=0.0,
                                 max_iterations=100,
                                 tolerance=config.IV_SOLVER_TOLERANCE):
    inputs = (S, K, T_days, market_price, r, q)
    if any(pd.isna(v) for v in inputs):
        return np.nan
    if market_price <= 0 or T_days <= 0 or S <= 0 or K <= 0:
        return np.nan

    t = T_days / 365.0
    lower_bound = max(0.0, S * np.exp(-q * t) - K * np.exp(-r * t))
    if market_price < lower_bound - tolerance:
        return np.nan
    if np.isclose(market_price, lower_bound, atol=tolerance):
        return 0.0

    low_vol, high_vol = 0.0, 5.0
    max_price = black_scholes_call(S, K, T_days, high_vol, r, q)
    if pd.isna(max_price) or market_price > max_price:
        return np.nan

    for _ in range(max_iterations):
        mid_vol = (low_vol + high_vol) / 2.0
        price = black_scholes_call(S, K, T_days, mid_vol, r, q)
        if pd.isna(price):
            return np.nan
        error = price - market_price
        if abs(error) < tolerance:
            return float(mid_vol)
        if error > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol
    return np.nan


def calculate_dataframe_iv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["calculated_iv"] = [
        calculate_implied_volatility(S, K, T, price, r, q)
        for S, K, T, price, r, q in zip(
            out["underlying_price"], out["strike"], out["days_to_expiry"],
            out["mid_price"], out["risk_free_rate"], out["dividend_yield"]
        )
    ]
    return out
