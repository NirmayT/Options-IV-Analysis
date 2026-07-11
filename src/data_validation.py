import pandas as pd
import numpy as np

from sqlalchemy import text
from database_manager import engine

def load_raw_data(engine) -> pd.DataFrame:
    """
    Load raw data from the database.
    """

    query = text("SELECT * FROM options_snapshot")

    try:
        df = pd.read_sql_query(query, engine)
        return df
    except Exception as e:
        print(f"Error loading data from the database: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

def generate_validation_report(df: pd.DataFrame) -> dict:
    """
    Analyzes the data to identify and count anomalies
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
    report["duplicate_records"] = df.duplicated(subset=['snapshot_time', 'ticker', 'expiry', 'strike']).sum()
    
    # 5. Liquidity Anomalies
    report["zero_volume"] = (df['volume'] == 0).sum()
    report["zero_open_interest"] = (df['openInterest'] == 0).sum()
    report["completely_illiquid"] = ((df['bid'] == 0) & (df['ask'] == 0)).sum()

    # 6. Expired Contracts
    snap_dt = pd.to_datetime(df['snapshot_time']).dt.date
    expiry_dt = pd.to_datetime(df['expiry']).dt.date
    report["expired_contracts"] = (snap_dt >= expiry_dt).sum()

    return report

def clean_option_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the option data by removing anomalies.
    Returns a cleaned DataFrame.
    """
    if df.empty:
        return df  # Return empty DataFrame if input is empty

    # Remove rows with null bids or asks
    df_cleaned = df.dropna(subset=['bid', 'ask','strike','mid_price']).copy()

    # Remove rows with negative prices
    df_cleaned = df_cleaned[(df_cleaned['bid'] >= 0) & (df_cleaned['ask'] >= 0) & (df_cleaned['strike'] > 0)]

    # Remove crossed bid-ask
    df_cleaned = df_cleaned[df_cleaned['bid'] <= df_cleaned['ask']]

    # Drop completely illiquid options (both bid and ask are zero)
    df_cleaned = df_cleaned[((df_cleaned['bid'] > 0) | (df_cleaned['ask'] > 0))]

    # Remove duplicates based on primary key columns
    df_cleaned = df_cleaned.drop_duplicates(subset=['snapshot_time', 'ticker', 'expiry', 'strike'])

    # Remove expired contracts
    snap_dt = pd.to_datetime(df_cleaned['snapshot_time']).dt.date
    expiry_dt = pd.to_datetime(df_cleaned['expiry']).dt.date
    df_cleaned = df_cleaned[snap_dt < expiry_dt]

    return df_cleaned

def save_cleaned_data(df: pd.DataFrame, engine):
    """
    Saves the cleaned DataFrame back to the database.
    """
    if df.empty:
        print("No clean data to save. The DataFrame is empty.")
        return

    try:
        with engine.begin() as connection:
            # Use 'replace' to overwrite the existing table with cleaned data
            df.to_sql('cleaned_options_snapshots', connection, if_exists='replace', index=False)
        print(f"Cleaned data saved to the database successfully. Total records saved: {len(df)}")
    except Exception as e:
        print(f"Error saving cleaned data to the database: {e}")

def validate_pipeline(engine) -> pd.DataFrame:
    """
    Runs the entire validation pipeline: load, validate, clean, and save.
    Returns the validation report.
    """

    print("="*150)
    # Load raw data
    raw_df = load_raw_data(engine)
    if raw_df.empty:
        print("No data found in the database for validation.")
        return {"Status": "No Data"}
    
    # Generate validation report
    validation_report = generate_validation_report(raw_df)
    print("Validation Report:")
    for key, value in validation_report.items():
        print(f"{key}: {value}")
    
    # Clean the data
    cleaned_df = clean_option_data(raw_df)
    
    # Save cleaned data back to the database
    save_cleaned_data(cleaned_df, engine)

    # Verify the cleaned data
    cleaned_validation_report = generate_validation_report(cleaned_df)
    pct_retained = (len(cleaned_df) / len(raw_df)) * 100 if len(raw_df) > 0 else 0
    print(f"Percentage of data retained after cleaning: {pct_retained:.2f}%")


    
    return cleaned_df

if __name__ == "__main__":
    # Run the validation pipeline
    validate_pipeline(engine)