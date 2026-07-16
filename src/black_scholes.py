import numpy as np
import pandas as pd
import config
from scipy.stats import norm

def black_scholes_call(S: float, K: float, T_days: float, volatility: float,
                        r: float = config.RISK_FREE_RATE) -> float:
    """
    Calculates the theoretical Black-Scholes price for a European Call Option.

    Parameters:
    S (float): Current stock price (underlying_price)
    K (float): Strike price (strike)
    T_days (float): Days tp expiry
    r (float): Risk-free rate
    Volatility (float): Sigma

    Returns:
    float: Theoretical call price (returns 0.0 if calculations are invalid or option is expired)
    """
    if (pd.isna(S)or pd.isna(K) or pd.isna(T_days) or pd.isna(volatility)):
        return np.nan

    # 1. Edge Case: If option is expired or non-positive days, it has no time value
    if T_days <= 0:
        return max(0.0, S-K)

    # Convert days to years (t)
    t = T_days / 365.0

    # 2. Edge Case: Volatility or stock/strike price must be positive to calculate d1/d2
    if volatility <= 0 or S<= 0 or K <= 0:
        return max(0.0, S-K)

    try:
        # Calculate d1 and d2
        d1 = (np.log(S/K) + (r + (volatility ** 2) / 2.0) * t) / (volatility * np.sqrt(t))
        d2 = d1 - volatility * np.sqrt(t)

        # Calculate Call Price
        call_price = S * norm.cdf(d1) - K * np.exp(-r * t) * norm.cdf(d2)

        # Options prices cannot realistically be negative
        return max(0.0, float(call_price))

    except Exception:
        return max(0.0, S-K)

def calculate_theoretical_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a DataFrame of clean options data, calculates the Black-Scholes
    theoretical pricce for each call option, and appends it as a new column.

    Parameters:
    df (pd.DataFrame): DataFrame containing clean options data

    Returns:
    pd.DataFrame: Enriched DataFrame with a "bs_theoretical_price" column
    """
    # Ensure we don't modify the incoming dataframe directly
    priced_df = df.copy()

    # Apply our pricing function row-by-row
    priced_df["bs_theoretical_price"] = [black_scholes_call(S, K, T_days, vol)
                                     for S, K, T_days, vol in zip(
                                         priced_df["underlying_price"],
                                         priced_df["strike"],
                                         priced_df["days_to_expiry"],
                                         priced_df["yahoo_iv"])]

    # Calculate the pricing error feature (Market - Theory)
    priced_df["pricing_error"] = priced_df["mid_price"] - priced_df["bs_theoretical_price"]

    return priced_df


