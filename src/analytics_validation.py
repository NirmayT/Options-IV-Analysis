import numpy as np
import pandas as pd
import config


def generate_analytics_validation_report(df, tolerance=config.IV_SOLVER_TOLERANCE):
    if df.empty:
        return {"Status": "Empty DataFrame"}
    errors = df["iv_reconstruction_error"].dropna()
    return {
        "total_records": len(df),
        "null_bs_prices": df["bs_theoretical_price"].isnull().sum(),
        "unsolved_ivs": df["calculated_iv"].isnull().sum(),
        "negative_bs_prices": (df["bs_theoretical_price"] < 0).sum(),
        "negative_calculated_ivs": (df["calculated_iv"] < 0).sum(),
        "null_moneyness": df["moneyness"].isnull().sum(),
        "invalid_moneyness": (df["moneyness"] <= 0).sum(),
        "null_reconstructed_price": df["reconstructed_market_price"].isnull().sum(),
        "mean_reconstruction_error": float(errors.mean()) if not errors.empty else np.nan,
        "max_abs_reconstruction_error": float(errors.abs().max()) if not errors.empty else np.nan,
        "reconstruction_tolerance_exceeded": (errors.abs() > tolerance).sum(),
    }


def clean_analytics_data(df):
    if df.empty:
        return df
    mask = (
        df["bs_theoretical_price"].notna() & df["calculated_iv"].notna()
        & (df["bs_theoretical_price"] >= 0) & (df["calculated_iv"] >= 0)
        & df["moneyness"].notna() & (df["moneyness"] > 0)
        & df["log_moneyness"].notna() & df["reconstructed_market_price"].notna()
    )
    return df[mask].copy().reset_index(drop=True)


def run_analytics_validation_and_cleaning(df, tolerance=config.IV_SOLVER_TOLERANCE):
    if df.empty:
        return pd.DataFrame()
    print("=" * 120)
    print("--- Pre-Cleaning Analytics Report ---")
    for k, val in generate_analytics_validation_report(df, tolerance).items():
        print(f"{k}: {val}")
    clean = clean_analytics_data(df)
    print("--- Post-Cleaning Analytics Report ---")
    for k, val in generate_analytics_validation_report(clean, tolerance).items():
        print(f"{k}: {val}")
    print(f"[ANALYTICS] Retained {len(clean)}/{len(df)} rows")
    print("=" * 120)
    return clean
