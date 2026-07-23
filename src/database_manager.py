import pandas as pd
import config

from sqlalchemy import create_engine, text

engine = create_engine(f"sqlite:///{config.DATABASE_NAME}", echo=False)

def initialize_database():
    """
    Creates the raw and cleaned tables if they do not exist
    """
    # 1. Raw data table
    create_raw_table_query = f"""
    CREATE TABLE IF NOT EXISTS {config.RAW_OPTIONS_TABLE} (
        snapshot_time TEXT,
        ticker TEXT,
        underlying_price REAL,
        expiry TEXT,
        days_to_expiry INTEGER,
        option_type TEXT,
        strike REAL,
        bid REAL,
        ask REAL,
        last_trade_price REAL,
        volume INTEGER,
        open_interest INTEGER,
        yahoo_iv REAL,
        mid_price REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """
    # 2. Cleaned data table
    create_cleaned_table_query = f"""
    CREATE TABLE IF NOT EXISTS {config.CLEAN_OPTIONS_TABLE} (
        snapshot_time TEXT,
        ticker TEXT,
        underlying_price REAL,
        expiry TEXT,
        days_to_expiry INTEGER,
        option_type TEXT,
        strike REAL,
        bid REAL,
        ask REAL,
        last_trade_price REAL,
        volume INTEGER,
        open_interest INTEGER,
        yahoo_iv REAL,
        mid_price REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """
    # 3. Analystics master table
    create_analytics_table_query = f"""
    CREATE TABLE IF NOT EXISTS {config.ANALYTICS_OPTIONS_TABLE} (
        snapshot_time TEXT,
        ticker TEXT,
        underlying_price REAL,
        expiry TEXT,
        days_to_expiry INTEGER,
        years_to_expiry REAL,
        option_type TEXT,
        strike REAL,
        bid REAL,
        ask REAL,
        last_trade_price REAL,
        volume INTEGER,
        open_interest INTEGER,
        yahoo_iv REAL,
        mid_price REAL,
        bs_theoretical_price REAL,
        calculated_iv REAL,
        reconstructed_market_price REAL,
        iv_reconstruction_error REAL,
        pricing_error REAL,
        abs_pricing_error REAL,
        rel_pricing_error REAL,
        iv_difference REAL,
        abs_iv_difference REAL,
        moneyness REAL,
        log_moneyness REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """
    with engine.begin() as connection:
        connection.execute(text(create_raw_table_query))
        connection.execute(text(create_cleaned_table_query))
        connection.execute(text(create_analytics_table_query))

    print ("[DATABASE] Connection established and tables verified")

def delete_recent_snapshot(cutoff_str: str, tickers: list):
    """
    Deletes any rows in the database that fall within the 15-minute replacement window to
    prevent duplicate constraint errors.
    """
    with engine.begin() as connection:
        for ticker in tickers:
            parameters={"cutoff": cutoff_str, "ticker": ticker}

            # Wipe recent entries from both tables
            connection.execute(text(f"""DELETE FROM {config.RAW_OPTIONS_TABLE} WHERE snapshot_time >= :cutoff
                                    AND ticker = :ticker"""),parameters)
            connection.execute(text(f"""DELETE FROM {config.CLEAN_OPTIONS_TABLE} WHERE snapshot_time >= :cutoff
                                    AND ticker = :ticker"""),parameters)
            connection.execute(text(f"""DELETE FROM {config.ANALYTICS_OPTIONS_TABLE} WHERE snapshot_time >= :cutoff
                                    AND ticker = :ticker"""),parameters)

def save_raw_snapshot(df: pd.DataFrame):
    """ Saves the raw dataframe to SQL database."""
    if not df.empty:
        df.to_sql(config.RAW_OPTIONS_TABLE, engine, if_exists="append", index=False)

def save_clean_snapshot(df: pd.DataFrame):
    """ Saves the cleaned dataframe to SQL database."""
    if not df.empty:
        df.to_sql(config.CLEAN_OPTIONS_TABLE, engine, if_exists="append", index=False)

def save_analytics_snapshot(df: pd.DataFrame):
    """ Saves the analystics dataframe to SQL database."""
    if not df.empty:
        df.to_sql(config.ANALYTICS_OPTIONS_TABLE, engine, if_exists="append", index=False)

def load_raw_snapshot(query_modifier: str = "") -> pd.DataFrame:
    """Loads raw data."""
    query = f"SELECT * FROM {config.RAW_OPTIONS_TABLE} {query_modifier}"
    return pd.read_sql_query(query,engine)

def load_clean_snapshot(query_modifier: str = "") -> pd.DataFrame:
    """Loads clean data."""
    query = f"SELECT * FROM {config.CLEAN_OPTIONS_TABLE} {query_modifier}"
    return pd.read_sql_query(query,engine)

def load_analytics_snapshot(query_modifier: str = "") -> pd.DataFrame:
    """Loads analytics data."""
    query = f"SELECT * FROM {config.ANALYTICS_OPTIONS_TABLE} {query_modifier}"
    return pd.read_sql_query(query,engine)