import yfinance as yf
import pandas as pd
import config

from datetime import datetime

def prepare_option_df(ticker_obj:yf.Ticker, ticker_symbol: str, underlying_price: float,
                      snapshot_time: datetime, option_type:str = "Call") -> pd.DataFrame:
    """
    Fetches and prepares the option chain data for a given ticker symbol and snapshot time.

    Parameters:
    - ticker_symbol (str): The ticker symbol for which to fetch the option chain.
    - snapshot_time (datetime): The timestamp for the snapshot of the option chain.
    - option_type (str): The type of option to fetch ("Call" or "Put"). Default is "Call".
    Returns:
    - pd.DataFrame: A DataFrame containing the option chain data with additional calculated columns.

    """
    expiry_dates = ticker_obj.options

    if not expiry_dates:
        print(f"[WARNING] No expiry dates found for {ticker_symbol}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    # 2. Retrieve Option Chains
    nearest_expiry = expiry_dates[0]
    try:
        if option_type.lower() == "call":
            options_df = ticker_obj.option_chain(nearest_expiry).calls.copy()
        elif option_type.lower() == "put":
            options_df = ticker_obj.option_chain(nearest_expiry).puts.copy()
        else:
            raise ValueError("Invalid option type. Must be 'Call' or 'Put'.")
    except Exception as e:
        print(f"[WARNING] Error fetching option chain for {ticker_symbol} on {nearest_expiry}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

    # 3. Feature Engineering
    options_df['snapshot_time'] = snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
    options_df['ticker'] = ticker_symbol
    options_df['underlying_price'] = underlying_price
    options_df['option_type'] = option_type.capitalize()
    options_df['expiry'] = nearest_expiry
    options_df['mid_price'] = (options_df['bid'] + options_df['ask']) / 2 # Mid price calculation

    # Days to expiry calculation
    snapshot_dt = pd.to_datetime(snapshot_time)
    expiry_dt = pd.to_datetime(options_df['expiry'])
    options_df['days_to_expiry'] = (expiry_dt - snapshot_dt).dt.days

    # 4. Rename and Align columns to match database schema
    rename_mapping = {
        'openInterest': 'open_interest',
        'impliedVolatility': 'yahoo_iv',
        'lastPrice': 'last_trade_price'
    }
    options_df = options_df.rename(columns=rename_mapping)

    target_columns = ['snapshot_time', 'ticker', 'underlying_price', 'option_type','expiry', 'days_to_expiry',
                        'strike', 'bid', 'ask', 'mid_price', 'last_trade_price', 'volume', 'open_interest', 'yahoo_iv']

    options_df = options_df[target_columns] # Return only the relevant columns in correct order

    return options_df[target_columns]

def create_market_snapshot() -> tuple[pd.DataFrame, datetime]:
    """
    Loops through the config tickers, prepares their dataframes using the helper,
    and concatenates them into a single master dataframe.
    Parameters:
    """
    unified_snapshot_time = datetime.now()  # Generate a single timestamp for the entire snapshot

    # Load tickers from config into a list so we can loop through them
    tickers_to_fetch = [config.STOCK_TICKER, config.ETF_TICKER]
    all_frames = []

    for symbol in tickers_to_fetch:
        ticker_obj = yf.Ticker(symbol)

        try:
            current_price = ticker_obj.fast_info["lastPrice"]
        except Exception as e:
            print(f"[WARNING] Could not fetch price for {symbol}: {e}")
            continue # Skip to next ticker if this one fails

       # Call helper function for each ticker
        df = prepare_option_df(ticker_obj=ticker_obj, ticker_symbol=symbol, underlying_price=current_price,
                                   snapshot_time=unified_snapshot_time, option_type=config.OPTION_TYPE)
        
        if not df.empty:
            all_frames.append(df)

    if all_frames:
            return pd.concat(all_frames, ignore_index=True), unified_snapshot_time

    return pd.DataFrame(), unified_snapshot_time