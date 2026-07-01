import pandas as pd
import numpy as np
import scipy as sp
import matplotlib as mpl
import yfinance as yf
import sqlalchemy

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

# 3. Retrieve Option Chains
if stock_expiry_dates:
    expiry_stock = stock_expiry_dates[0]
    stock_calls = stock.option_chain(expiry_stock).calls

    # Filter columns needed for calculations
    filtered_stock_calls = stock_calls[['strike','bid','ask','lastPrice','volume','openInterest','impliedVolatility']]
    filtered_stock_calls.insert(0, "ticker", stock_ticker)
    filtered_stock_calls.insert(1, "expiry", expiry_stock)
    filtered_stock_calls.insert(5, "mid_price", (filtered_stock_calls["bid"] + filtered_stock_calls["ask"]) / 2)

else:
    raise ValueError("No expiry dates found for the stock.")

if etf_expiry_dates:
    expiry_etf = etf_expiry_dates[0]
    etf_calls = etf.option_chain(expiry_etf).calls

    # Filter columns needed for calculations
    filtered_etf_calls = etf_calls[['strike','bid','ask','lastPrice','volume','openInterest','impliedVolatility']]
    filtered_etf_calls.insert(0, "ticker", etf_ticker)
    filtered_etf_calls.insert(1, "expiry", expiry_etf)
    filtered_etf_calls.insert(5, "mid_price", (filtered_etf_calls["bid"] + filtered_etf_calls["ask"]) / 2)
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

