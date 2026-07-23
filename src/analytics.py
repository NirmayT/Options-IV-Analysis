import numpy as np
import pandas as pd
import config

from black_scholes import calculate_theoretical_prices, black_scholes_call
from implied_volatility import calculate_dataframe_iv

def generate_analytics_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering layer:
    Combines Black-Scholes theoretical pricing, IV solving, 
    and all derived error metrics & quantitative features.
    """
    # 1. Theoretical BS Price (using Yahoo IV)
    priced_df = calculate_theoretical_prices(df)

    # 2. Implied Volatility calculation via numerical solver
    analytics_df = calculate_dataframe_iv(priced_df)

    # 3. Solver Round-Trip Check: Reconstruct market price using calculated IV
    analytics_df["reconstructed_market_price"] = [
        black_scholes_call(S, K, T, iv) if pd.notna(iv) else np.nan
        for S, K, T, iv in zip(
            analytics_df["underlying_price"],
            analytics_df["strike"],
            analytics_df["days_to_expiry"],
            analytics_df["calculated_iv"]
        )
    ]

    analytics_df["iv_reconstruction_error"] = analytics_df["mid_price"] - analytics_df["reconstructed_market_price"]

    # 4. Pricing Error Metrics (Moved from black_scholes.py)
    analytics_df["pricing_error"] = analytics_df["mid_price"] - analytics_df["bs_theoretical_price"]
    analytics_df["abs_pricing_error"] = analytics_df["pricing_error"].abs()
    analytics_df["rel_pricing_error"] = np.where(
        analytics_df["bs_theoretical_price"] > config.IV_SOLVER_TOLERANCE,
        analytics_df["pricing_error"] / analytics_df["bs_theoretical_price"],
        np.nan
    )

    # 5. Volatility Discrepancy Metrics (Moved from implied_volatility.py)
    analytics_df["iv_difference"] = analytics_df["calculated_iv"] - analytics_df["yahoo_iv"]
    analytics_df["abs_iv_difference"] = analytics_df["iv_difference"].abs()

    # 6. Time and Moneyness Transformations
    analytics_df["years_to_expiry"] = analytics_df["days_to_expiry"] / 365.0
    analytics_df["moneyness"] = analytics_df["underlying_price"] / analytics_df["strike"]
    analytics_df["log_moneyness"] = np.log(np.maximum(analytics_df["moneyness"], config.IV_SOLVER_TOLERANCE))

    return analytics_df