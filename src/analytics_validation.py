import numpy as np
import pandas as pd
import config

def generate_analytics_validation_report(df: pd.DataFrame, tolerance: float = config.IV_SOLVER_TOLERANCE) -> dict:
    """
    Analyzes analytics data to categorize model behavior into:
      1. Hard Failures (Invalid math / missing solver outputs)
      2. Soft Warnings (Numerical solver tolerance deviations)
      3. Research Observations (Unusual market states preserved for analysis)
    """
    if df.empty:
        return {"Status": "Empty DataFrame"}

    report = {}
    report["total_records"] = len(df)

    # 1. HARD FAILURES (Unusable / Non-physical data)
    report["null_bs_prices"] = df['bs_theoretical_price'].isnull().sum()
    report["unsolved_ivs"] = df['calculated_iv'].isnull().sum()
    report["negative_bs_prices"] = (df['bs_theoretical_price'] < 0).sum()
    report["negative_calculated_ivs"] = (df['calculated_iv'] < 0).sum()
    report["null_moneyness"] = df['moneyness'].isnull().sum()
    report["invalid_moneyness"] = (df['moneyness'] <= 0).sum()
    report["null_log_moneyness"] = df['log_moneyness'].isnull().sum()
    report["null_reconstructed_price"] = df['reconstructed_market_price'].isnull().sum()

    # 2. SOFT WARNINGS (Solver Precision)
    valid_reconstruction_errors = df['iv_reconstruction_error'].dropna() if 'iv_reconstruction_error' in df.columns else pd.Series(dtype=float)
    report["mean_reconstruction_error"] = float(valid_reconstruction_errors.mean()) if not valid_reconstruction_errors.empty else np.nan
    report["max_abs_reconstruction_error"] = float(valid_reconstruction_errors.abs().max()) if not valid_reconstruction_errors.empty else np.nan
    report["iv_reconstruction_tolerance_exceeded"] = (valid_reconstruction_errors.abs() > tolerance).sum()
    report["large_pricing_error (> $5.00)"] = (df['abs_pricing_error'] > 5.0).sum() if 'abs_pricing_error' in df.columns else 0

    # 3. RESEARCH OBSERVATIONS (Kept intentionally for regime analysis)
    report["unusual_high_ivs (> 200%)"] = (df['calculated_iv'] > 2.0).sum()
    report["extreme_high_ivs (> 500%)"] = (df['calculated_iv'] > 5.0).sum()
    report["deep_otm (moneyness < 0.80)"] = (df['moneyness'] < 0.80).sum()
    report["deep_itm (moneyness > 1.20)"] = (df['moneyness'] > 1.20).sum()
    if 'volume' in df.columns:
        report["zero_volume_contracts"] = (df['volume'] == 0).sum()

    return report


def clean_analytics_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out ONLY Hard Failures (non-physical calculations and missing values).
    Preserves Soft Warnings and Research Observations (e.g. high IVs) for market stress analysis.
    """
    if df.empty:
        return df

    # Mask for Hard Failures
    valid_mask = (
        df['bs_theoretical_price'].notnull() &
        df['calculated_iv'].notnull() &
        (df['bs_theoretical_price'] >= 0) &
        (df['calculated_iv'] >= 0) &
        df['moneyness'].notnull() &
        (df['moneyness'] > 0) &
        df['log_moneyness'].notnull() &
        df['reconstructed_market_price'].notnull()
    )

    return df[valid_mask].copy().reset_index(drop=True)


def run_analytics_validation_and_cleaning(analytics_df: pd.DataFrame, tolerance: float = config.IV_SOLVER_TOLERANCE) -> pd.DataFrame:
    """
    Wrapper function that runs pre-cleaning diagnostics, filters out hard numerical failures,
    and reports dataset retention and retained research flags.
    """
    if analytics_df.empty:
        print("[ANALYTICS VALIDATION] Input DataFrame is empty. Skipping validation.")
        return pd.DataFrame()

    print("=" * 150)
    print("--- Pre-Cleaning Analytics Validation Report ---")
    pre_report = generate_analytics_validation_report(analytics_df, tolerance=tolerance)
    for key, value in pre_report.items():
        if isinstance(value, float):
            print(f"  {key}: {value:+.6f}")
        else:
            print(f"  {key}: {value}")

    # Clean hard failures only
    cleaned_df = clean_analytics_data(analytics_df)

    print("\n--- Post-Cleaning Analytics Validation Report ---")
    post_report = generate_analytics_validation_report(cleaned_df, tolerance=tolerance)
    for key, value in post_report.items():
        if isinstance(value, float):
            print(f"  {key}: {value:+.6f}")
        else:
            print(f"  {key}: {value}")

    pct_retained = (len(cleaned_df) / len(analytics_df)) * 100 if len(analytics_df) > 0 else 0
    hard_dropped = len(analytics_df) - len(cleaned_df)

    print("\n--- Validation Summary ---")
    print(f"Hard Failures Dropped : {hard_dropped}")
    print(f"Total Rows Retained   : {len(cleaned_df)} ({pct_retained:.2f}%)")
    print(f"High-IV Contracts (>200%) Retained for Research: {post_report.get('unusual_high_ivs (> 200%)', 0)}")
    print("=" * 150)

    return cleaned_df