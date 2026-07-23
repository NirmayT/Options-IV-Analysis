import numpy as np
import pandas as pd
import config

from black_scholes import black_scholes_call

def calculate_implied_volatility(S: float, K: float, T_days: float, market_price: float,
                                 r: float = config.RISK_FREE_RATE, max_iterations: int = 100,
                                 tolerance: float = config.IV_SOLVER_TOLERANCE) -> float:
    """
    Calculates the Implied Volatility for a Call Option using Bisection Serach.

    Parameters:
    S (float): Current stock price (underlying_price)
    K (float): Strike price (strike)
    T_days (float): Days to expiry
    market_price (float): The actual market price of the option (mid_price)
    r (float): Risk-free rate
    max_iterations (int): Safety limit to prevent infinite loops
    tolerance (float): How close our calculated price must be to the market price (e.g., $0.0001)
    
    Returns:
    float: Implied Volatility (returns NaN if it doesn't converge or is invalid)
    """
    # 1. Edge Case: If any input is missing, return NaN
    if pd.isna(S) or pd.isna(K) or pd.isna(T_days) or pd.isna(market_price):
        return np.nan
    
    if market_price <=0 or T_days <= 0:
        return np.nan
    
    # 2. Edge Case: Intrinsic value check
    intrinsic_value = max(0.0, S-K)
    if market_price < intrinsic_value:
        return np.nan

    if np.isclose(market_price, intrinsic_value, atol=tolerance):
        return 0.0
    
    # Set search boundaries (0% to 500% volatility)
    low_vol = 0.0
    high_vol = 5.0

    # 3. Check for upper-bound convergence capability
    max_price = black_scholes_call(S, K, T_days, high_vol, r)
    if market_price > max_price:
        return np.nan
    
    # Run Bisection search
    for i in range(max_iterations):
        mid_vol = (low_vol + high_vol) / 2.0

        # Calculate theoertical price at our current guess
        theoretical_price = black_scholes_call(S, K, T_days, mid_vol, r)

        # Determine pricing error relative to the market
        pricing_error = theoretical_price - market_price

        # Check within tolerance
        if abs(pricing_error) < tolerance:
            return float(mid_vol)
        
        # Adjust search range
        if pricing_error > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol
    
    return mid_vol

def calculate_dataframe_iv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Loops through the cleaned options DataFrame and calculates 
    the Implied Volatility for every option row.
    
    Parameters:
    df (pd.DataFrame): Cleaned options DataFrame
    
    Returns:
    pd.DataFrame: New DataFrame with 'calculated_iv' and 'iv_difference'
    """
    iv_df = df.copy()

    # Calculate the IVs
    iv_df["calculated_iv"] = [calculate_implied_volatility(S, K, T_days, market_price)
                              for S, K, T_days, market_price in zip(iv_df["underlying_price"],
                                  iv_df["strike"],
                                  iv_df["days_to_expiry"],
                                  iv_df["mid_price"])]
    
    # Benchmark against Yahoo's IV
    # iv_df["iv_difference"] = iv_df["calculated_iv"] - iv_df["yahoo_iv"]

    return iv_df