import pandas as pd
import config
from sqlalchemy import create_engine, text

engine = create_engine(f"sqlite:///{config.DATABASE_NAME}", echo=False)


def _existing_columns(connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def _add_missing_column(connection, table_name: str, column_name: str, sql_type: str) -> None:
    """Adds a column only when it is absent, making upgrades safe for old databases."""
    existing = _existing_columns(connection, table_name)
    if column_name not in existing:
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")
        )
        print(f"[DATABASE] Added {table_name}.{column_name}")


def initialize_database():
    """Creates all tables and applies backward-compatible column upgrades."""
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
        risk_free_rate REAL,
        dividend_yield REAL,
        mid_price REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """

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
        risk_free_rate REAL,
        dividend_yield REAL,
        mid_price REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """

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
        risk_free_rate REAL,
        dividend_yield REAL,
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
        bid_ask_spread REAL,
        relative_spread REAL,
        moneyness REAL,
        log_moneyness REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, strike, option_type)
    );
    """

    create_regime_analysis_table_query = f"""
    CREATE TABLE IF NOT EXISTS {config.REGIME_ANALYSIS_TABLE} (
        snapshot_time TEXT,
        ticker TEXT,
        expiry TEXT,
        regime TEXT,
        atm_iv REAL,
        downside_wing_call_iv REAL,
        upside_wing_call_iv REAL,
        downside_call_skew REAL,
        upside_call_skew REAL,
        total_contracts INTEGER,
        "iv_bucket_0.80-0.90" REAL,
        "iv_bucket_0.90-0.95" REAL,
        "iv_bucket_0.95-1.00" REAL,
        "iv_bucket_1.00-1.05" REAL,
        "iv_bucket_1.05-1.10" REAL,
        "iv_bucket_1.10-1.20" REAL,
        PRIMARY KEY (snapshot_time, ticker, expiry, regime)
    );
    """

    create_regime_summary_table_query = f"""
    CREATE TABLE IF NOT EXISTS {config.REGIME_SUMMARY_TABLE} (
        snapshot_date TEXT,
        ticker TEXT,
        regime TEXT,
        avg_iv REAL,
        median_iv REAL,
        atm_iv REAL,
        downside_wing_call_iv REAL,
        upside_wing_call_iv REAL,
        avg_downside_call_skew REAL,
        observations INTEGER,
        PRIMARY KEY (snapshot_date, ticker, regime)
    );
    """

    with engine.begin() as connection:
        connection.execute(text(create_raw_table_query))
        connection.execute(text(create_cleaned_table_query))
        connection.execute(text(create_analytics_table_query))
        connection.execute(text(create_regime_analysis_table_query))
        connection.execute(text(create_regime_summary_table_query))

        # Backward-compatible upgrades for databases created by earlier versions.
        for table in (config.RAW_OPTIONS_TABLE, config.CLEAN_OPTIONS_TABLE):
            _add_missing_column(connection, table, "risk_free_rate", "REAL")
            _add_missing_column(connection, table, "dividend_yield", "REAL")

        for column in (
            "risk_free_rate",
            "dividend_yield",
            "bid_ask_spread",
            "relative_spread",
        ):
            _add_missing_column(
                connection,
                config.ANALYTICS_OPTIONS_TABLE,
                column,
                "REAL",
            )

    print("[DATABASE] Connection established, tables verified, and schema upgraded")


def delete_recent_snapshot(cutoff_str: str, tickers: list):
    with engine.begin() as connection:
        for ticker in tickers:
            parameters = {"cutoff": cutoff_str, "ticker": ticker}
            for table in (
                config.RAW_OPTIONS_TABLE,
                config.CLEAN_OPTIONS_TABLE,
                config.ANALYTICS_OPTIONS_TABLE,
                config.REGIME_ANALYSIS_TABLE,
            ):
                connection.execute(
                    text(
                        f"DELETE FROM {table} "
                        "WHERE snapshot_time >= :cutoff AND ticker = :ticker"
                    ),
                    parameters,
                )


def delete_regime_summary_for_date(snapshot_date_str: str, tickers: list):
    with engine.begin() as connection:
        for ticker in tickers:
            connection.execute(
                text(
                    f"DELETE FROM {config.REGIME_SUMMARY_TABLE} "
                    "WHERE snapshot_date = :snapshot_date AND ticker = :ticker"
                ),
                {"snapshot_date": snapshot_date_str, "ticker": ticker},
            )


def save_raw_snapshot(df):
    if not df.empty:
        df.to_sql(config.RAW_OPTIONS_TABLE, engine, if_exists="append", index=False)


def save_clean_snapshot(df):
    if not df.empty:
        df.to_sql(config.CLEAN_OPTIONS_TABLE, engine, if_exists="append", index=False)


def save_analytics_snapshot(df):
    if not df.empty:
        df.to_sql(config.ANALYTICS_OPTIONS_TABLE, engine, if_exists="append", index=False)


def save_regime_analysis_snapshot(df):
    if not df.empty:
        df.to_sql(config.REGIME_ANALYSIS_TABLE, engine, if_exists="append", index=False)


def save_regime_summary_snapshot(df):
    if not df.empty:
        df.to_sql(config.REGIME_SUMMARY_TABLE, engine, if_exists="append", index=False)


def load_raw_snapshot(query_modifier: str = "") -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT * FROM {config.RAW_OPTIONS_TABLE} {query_modifier}",
        engine,
    )


def load_clean_snapshot(query_modifier: str = "") -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT * FROM {config.CLEAN_OPTIONS_TABLE} {query_modifier}",
        engine,
    )


def load_analytics_snapshot(query_modifier: str = "") -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT * FROM {config.ANALYTICS_OPTIONS_TABLE} {query_modifier}",
        engine,
    )


def load_regime_analysis_snapshot(query_modifier: str = "") -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT * FROM {config.REGIME_ANALYSIS_TABLE} {query_modifier}",
        engine,
    )


def load_regime_summary_snapshot(query_modifier: str = "") -> pd.DataFrame:
    return pd.read_sql_query(
        f"SELECT * FROM {config.REGIME_SUMMARY_TABLE} {query_modifier}",
        engine,
    )
