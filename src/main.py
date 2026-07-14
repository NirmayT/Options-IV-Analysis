import pandas as pd
import numpy as np
import scipy as sp
import matplotlib as mpl
import yfinance as yf
import sqlalchemy

from datetime import datetime, timedelta
from sqlalchemy import text
from database_manager import engine
from data_validation import validate_pipeline

def market_data_ingestion():
    """
    Ingests market data for a stock and an ETF, processes it, and stores it in the database.
    """

    # Choose the ticker objects for the stock and ETF
    stock = yf.Ticker("JPM")  
    etf = yf.Ticker("XLF")

    # Retrieve Basic Information
    stock_name = stock.info.get("longName", "Stock name not found")
    stock_ticker = stock.ticker
    stock_price = stock.fast_info["lastPrice"]
    stock_expiry_dates = stock.options

    etf_name = etf.info.get("longName", "ETF name not found")
    etf_ticker = etf.ticker
    etf_price = etf.fast_info["lastPrice"]
    etf_expiry_dates = etf.options

    now_obj = datetime.now()
    snapshot_time = now_obj

    target_columns = ['snapshot_time', 'ticker', 'underlying_price', 'option_type','expiry', 'days_to_expiry', 
                      'strike', 'bid', 'ask', 'mid_price', 'last_trade_price', 'volume', 'open_interest', 'yahoo_iv']
    
    rename_mapping = {
        'openInterest': 'open_interest',
        'impliedVolatility': 'yahoo_iv',
        'lastPrice': 'last_trade_price'
    }

    # 3. Retrieve Option Chains
    if stock_expiry_dates:
        expiry_stock = stock_expiry_dates[0]
        stock_calls = stock.option_chain(expiry_stock).calls.copy()
        
        # Filter columns needed for calculations
        stock_calls['snapshot_time'] = snapshot_time
        stock_calls['ticker'] = stock_ticker
        stock_calls['underlying_price'] = stock_price
        stock_calls['option_type'] = 'Call'
        stock_calls['expiry'] = expiry_stock
        stock_calls['mid_price'] = (stock_calls['bid'] + stock_calls['ask']) / 2

        snapshot_dt = pd.to_datetime(snapshot_time)
        expiry_dt = pd.to_datetime(stock_calls['expiry'])
        stock_calls['days_to_expiry'] = (expiry_dt - snapshot_dt).dt.days

        # Rename and align columns
        filtered_stock_calls = stock_calls.rename(columns=rename_mapping)[target_columns]
    else:
        raise ValueError("No expiry dates found for the stock.")

    if etf_expiry_dates:
        expiry_etf = etf_expiry_dates[0]
        etf_calls = etf.option_chain(expiry_etf).calls.copy()
        
        # Filter columns needed for calculations
        etf_calls['snapshot_time'] = snapshot_time
        etf_calls['ticker'] = etf_ticker
        etf_calls['underlying_price'] = etf_price
        etf_calls['option_type'] = 'Call'
        etf_calls['expiry'] = expiry_etf
        etf_calls['mid_price'] = (etf_calls['bid'] + etf_calls['ask']) / 2

        snapshot_dt = pd.to_datetime(snapshot_time)
        expiry_dt = pd.to_datetime(etf_calls['expiry'])
        etf_calls['days_to_expiry'] = (expiry_dt - snapshot_dt).dt.days

        # Rename and align columns
        filtered_etf_calls = etf_calls.rename(columns=rename_mapping)[target_columns]
    else:
        raise ValueError("No expiry dates found for the ETF.")
    

    # Print the retrieved information

    print("="*150)
    print(f"Stock Name: {stock_name}")
    print(f"Stock Ticker: {stock_ticker}")
    print(f"Current Price: ${stock_price:.2f}")
    print(f"Available Expiries: {stock_expiry_dates[:3]}... (Total: {len(stock_expiry_dates)})")
    print(f"\nCalls for Expiry {expiry_stock}:")
    print(filtered_stock_calls.head())
    print("="*150)

    print(f"ETF Name: {etf_name}")
    print(f"ETF Ticker: {etf_ticker}")
    print(f"Current Price: ${etf_price:.2f}")
    print(f"Available Expiries: {etf_expiry_dates[:3]}... (Total: {len(etf_expiry_dates)})")
    print(f"\nCalls for Expiry {expiry_etf}:")
    print(filtered_etf_calls.head())
    print("="*150)

    # Database Integration: Store the filtered data into the SQLite database

    # Interval limit to remove duplicates based on snapshot_time and ticker
    TIME_WINDOW_MINUTES = 15
    raw_cutoff_time = snapshot_time - pd.Timedelta(minutes=TIME_WINDOW_MINUTES)

    cutoff_str = raw_cutoff_time.strftime('%Y-%m-%d %H:%M:%S') # convert standard string to datetime object

    with engine.begin() as connection:
        # Verify if the table exists to avoid errors when inserting data
        table_exists = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='options_snapshot';")).fetchone()

        if table_exists:
            # Delete rows older than the cutoff time for the same ticker
            connection.execute(text("DELETE FROM options_snapshot WHERE snapshot_time >= :cutoff AND ticker = :ticker"), {"cutoff": cutoff_str, "ticker": stock_ticker})
            connection.execute(text("DELETE FROM options_snapshot WHERE snapshot_time >= :cutoff AND ticker = :ticker"), {"cutoff": cutoff_str, "ticker": etf_ticker})

            print(f"[CLEANUP] Detected recent active session. Overwrote any existing snapshots written since {cutoff_str} for tickers {stock_ticker} and {etf_ticker}.")
        else:
            print("Table 'options_snapshot' does not exist. It will be created when inserting new data.")

        # Append the new data to the database
        filtered_stock_calls.to_sql("options_snapshot", connection, if_exists="append", index=False)
        filtered_etf_calls.to_sql("options_snapshot", connection, if_exists="append", index=False)
        print(f"[DATABASE] Inserted new data for tickers {stock_ticker} and {etf_ticker} into the database.")

    print ("\n" + "="*150)

    df_check = pd.read_sql_query("""SELECT * FROM options_snapshot ORDER BY snapshot_time DESC LIMIT 5""", engine)

    print(df_check)

def main():
    """
    Main function to run the market data ingestion and validation pipeline.
    """
    # Update the database with the latest market data
    market_data_ingestion()

    # Run the validation pipeline on the updated data
    cleaned_df = validate_pipeline(engine)

    if not cleaned_df.empty:
        print("\nCleaned Data Snapshot:")
        print(cleaned_df.head())
    
if __name__ == "__main__":
    main()