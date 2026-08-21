import numpy as np
import pandas as pd
import config
from black_scholes import calculate_theoretical_prices, black_scholes_call
from implied_volatility import calculate_dataframe_iv


def generate_analytics_df(df: pd.DataFrame) -> pd.DataFrame:
    """Creates pricing, volatility, liquidity, time, and moneyness features."""
    priced_df = calculate_theoretical_prices(df)
    analytics_df = calculate_dataframe_iv(priced_df)

    analytics_df["reconstructed_market_price"] = [
        black_scholes_call(S, K, T, iv, r, q) if pd.notna(iv) else np.nan
        for S, K, T, iv, r, q in zip(
            analytics_df["underlying_price"],
            analytics_df["strike"],
            analytics_df["days_to_expiry"],
            analytics_df["calculated_iv"],
            analytics_df["risk_free_rate"],
            analytics_df["dividend_yield"],
        )
    ]

    analytics_df["iv_reconstruction_error"] = (
        analytics_df["mid_price"]
        - analytics_df["reconstructed_market_price"]
    )

    analytics_df["pricing_error"] = (
        analytics_df["mid_price"]
        - analytics_df["bs_theoretical_price"]
    )
    analytics_df["abs_pricing_error"] = analytics_df["pricing_error"].abs()
    analytics_df["rel_pricing_error"] = np.where(
        analytics_df["bs_theoretical_price"] > config.IV_SOLVER_TOLERANCE,
        analytics_df["pricing_error"]
        / analytics_df["bs_theoretical_price"],
        np.nan,
    )

    analytics_df["iv_difference"] = (
        analytics_df["calculated_iv"]
        - analytics_df["yahoo_iv"]
    )
    analytics_df["abs_iv_difference"] = analytics_df["iv_difference"].abs()

    # Quote-quality measures. These support research-chart filtering and make
    # divergences between midpoint IV and Yahoo IV easier to interpret.
    analytics_df["bid_ask_spread"] = (
        analytics_df["ask"] - analytics_df["bid"]
    )
    analytics_df["relative_spread"] = np.where(
        analytics_df["mid_price"] > 0,
        analytics_df["bid_ask_spread"]
        / analytics_df["mid_price"],
        np.nan,
    )

    analytics_df["years_to_expiry"] = (
        analytics_df["days_to_expiry"] / 365.0
    )

    # Retain the established project-wide convention: S / K.
    analytics_df["moneyness"] = (
        analytics_df["underlying_price"]
        / analytics_df["strike"]
    )
    analytics_df["log_moneyness"] = np.log(
        np.maximum(
            analytics_df["moneyness"],
            config.IV_SOLVER_TOLERANCE,
        )
    )

    return analytics_df
