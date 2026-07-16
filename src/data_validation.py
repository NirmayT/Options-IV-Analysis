import pandas as pd
import numpy as np

def generate_validation_report(df: pd.DataFrame) -> dict:
    """
    Analyzes the data to identify and count anomalies.
    Returns a dictionary containing the validation report.
    """
    if df.empty:
        return {"Status": "Empty DataFrame"}
    
    report = {}
    total_rows = len(df)
    report["total_records"] = total_rows

    # 1. Null Checks
    report["null_bids"] = df['bid'].isnull().sum()
    report["null_asks"] = df['ask'].isnull().sum()

    # 2. Negative Prices
    report["negative_bids"] = (df['bid'] < 0).sum()
    report["negative_asks"] = (df['ask'] < 0).sum()
    report["negative_strikes"] = (df['strike'] <= 0).sum()

    # 3. Crossed Bid-Ask
    report["crossed_bid_ask"] = ((df['bid'] > df['ask']) & (df['bid'].notnull()) & (df['ask'].notnull())).sum()

    # 4. Duplicates 
    report["duplicate_records"] = df.duplicated(subset=['snapshot_time', 'ticker', 'expiry', 'strike', 'option_type']).sum()
    
    # 5. Liquidity Anomalies
    report["zero_volume"] = (df['volume'] == 0).sum()
    report["zero_open_interest"] = (df['open_interest'] == 0).sum()
    report["completely_illiquid"] = ((df['bid'] == 0) & (df['ask'] == 0)).sum()

    # 6. Expired Contracts
    report["expired_contracts"] = (df['days_to_expiry'] < 0).sum()

    return report

def clean_option_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the option data by removing anomalies.
    Returns a cleaned DataFrame.
    """
    if df.empty:
        return df
    
    # Remove rows with null critical fields
    df_cleaned = df.dropna(subset=['bid', 'ask', 'strike', 'mid_price']).copy()

    # Remove rows with negative prices
    df_cleaned = df_cleaned[(df_cleaned['bid'] >= 0) & (df_cleaned['ask'] >= 0) & (df_cleaned['strike'] > 0)]

    # Remove crossed bid-ask
    df_cleaned = df_cleaned[df_cleaned['bid'] <= df_cleaned['ask']]

    # Drop completely illiquid options (both bid and ask are zero)
    df_cleaned = df_cleaned[((df_cleaned['bid'] > 0) | (df_cleaned['ask'] > 0))]

    # Remove duplicates 
    df_cleaned = df_cleaned.drop_duplicates(subset=['snapshot_time', 'ticker', 'expiry', 'strike', 'option_type'])

    # Remove expired contracts
    df_cleaned = df_cleaned[df_cleaned['days_to_expiry'] >= 0]

    return df_cleaned

def run_validation_and_cleaning(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Wrapper function that generates reports, cleans the data, 
    and prints the before/after statistics.
    """
    if raw_df.empty:
        print("[VALIDATION] Input DataFrame is empty. Skipping validation")
        return pd.DataFrame ()
    
    print("=" * 150)

    # Pre-cleaning Report
    validation_report = generate_validation_report(raw_df)
    print("\n--- Pre-Cleaning Anomalies ---")
    for key, value in validation_report.items():
        print (f"{key}: {value}")

    # Clean the data
    cleaned_df = clean_option_data(raw_df)

    # Verify the cleaned data
    cleaned_validation_report = generate_validation_report(cleaned_df)
    print("\n--- Post-Cleaning Validation Report ---")
    for key, value in cleaned_validation_report.items():
        print(f"{key}: {value}")

    pct_retained = (len(cleaned_df) / len(raw_df)) * 100 if len(raw_df) > 0 else 0
    print(f"\n[VALIDATION] Percentage of data retained: {pct_retained:.2f}%")
    print("=" * 150)

    return cleaned_df