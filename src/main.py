import pandas as pd
import numpy as np
import scipy as sp
import matplotlib as mpl
import yfinance as yf
import sqlalchemy

from datetime import datetime, timedelta
from database_manager import engine
from sqlalchemy import text

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

snapshot_time = datetime.now()

# 3. Retrieve Option Chains
if stock_expiry_dates:
    expiry_stock = stock_expiry_dates[0]
    stock_calls = stock.option_chain(expiry_stock).calls

    # Filter columns needed for calculations
    filtered_stock_calls = stock_calls[['strike','bid','ask','lastPrice','volume','openInterest','impliedVolatility']].copy()
    filtered_stock_calls.insert(0, "ticker", stock_ticker)
    filtered_stock_calls.insert(1, "expiry", expiry_stock)
    filtered_stock_calls.insert(5, "mid_price", (filtered_stock_calls["bid"] + filtered_stock_calls["ask"]) / 2)
    filtered_stock_calls.insert(0, "snapshot_time", snapshot_time)

else:
    raise ValueError("No expiry dates found for the stock.")

if etf_expiry_dates:
    expiry_etf = etf_expiry_dates[0]
    etf_calls = etf.option_chain(expiry_etf).calls

    # Filter columns needed for calculations
    filtered_etf_calls = etf_calls[['strike','bid','ask','lastPrice','volume','openInterest','impliedVolatility']].copy()
    filtered_etf_calls.insert(0, "ticker", etf_ticker)
    filtered_etf_calls.insert(1, "expiry", expiry_etf)
    filtered_etf_calls.insert(5, "mid_price", (filtered_etf_calls["bid"] + filtered_etf_calls["ask"]) / 2)
    filtered_etf_calls.insert(0, "snapshot_time", snapshot_time)
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
    table_exists = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='options_raw';")).fetchone()

    if table_exists:
        # Delete rows older than the cutoff time for the same ticker
        connection.execute(text("DELETE FROM options_raw WHERE snapshot_time >= :cutoff AND ticker = :ticker"), {"cutoff": cutoff_str, "ticker": stock_ticker})
        connection.execute(text("DELETE FROM options_raw WHERE snapshot_time >= :cutoff AND ticker = :ticker"), {"cutoff": cutoff_str, "ticker": etf_ticker})

        print(f"[CLEANUP] Detected recent active session. Overwrote any existing snapshots written since {cutoff_str} for tickers {stock_ticker} and {etf_ticker}.")
    else:
        print("Table 'options_raw' does not exist. It will be created when inserting new data.")

    # Append the new data to the database
    filtered_stock_calls.to_sql("options_raw", connection, if_exists="append", index=False)
    filtered_etf_calls.to_sql("options_raw", connection, if_exists="append", index=False)
    print(f"[DATABASE] Inserted new data for tickers {stock_ticker} and {etf_ticker} into the database.")

print ("\n" + "="*150)

df_check = pd.read_sql_query("""SELECT * FROM options_raw ORDER BY snapshot_time DESC LIMIT 5""", engine)

print(df_check)