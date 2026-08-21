from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf
import config


def fetch_risk_free_rate() -> float:
    """Fetch ^IRX once per run; return decimal rate with fallback."""
    try:
        quote = float(yf.Ticker(config.RISK_FREE_TICKER).fast_info["lastPrice"])
        if quote <= 0:
            raise ValueError("non-positive yield")
        rate = quote / 100.0
        print(f"[MARKET] Risk-free proxy {config.RISK_FREE_TICKER}: {rate:.4%}")
        return rate
    except Exception as exc:
        print(f"[MARKET] Risk-free fetch failed ({exc}); fallback {config.RISK_FREE_RATE:.2%}")
        return config.RISK_FREE_RATE


def estimate_dividend_yield(ticker_obj, ticker_symbol, spot, snapshot_time) -> float:
    """Trailing-12-month cash dividends divided by current spot."""
    if spot is None or spot <= 0:
        return 0.0
    try:
        dividends = ticker_obj.dividends
        if dividends is None or dividends.empty:
            print(f"[MARKET] {ticker_symbol} dividend yield estimate: 0.0000%")
            return 0.0
        dividends = dividends.copy()
        dividends.index = pd.to_datetime(dividends.index)
        if dividends.index.tz is not None:
            dividends.index = dividends.index.tz_localize(None)
        end = pd.Timestamp(snapshot_time)
        if end.tz is not None:
            end = end.tz_localize(None)
        start = end - pd.Timedelta(days=config.DIVIDEND_LOOKBACK_DAYS)
        trailing = float(dividends.loc[(dividends.index > start) & (dividends.index <= end)].sum())
        q = trailing / spot
        if not np.isfinite(q) or q < 0:
            q = 0.0
        print(f"[MARKET] {ticker_symbol} dividend yield estimate: {q:.4%}")
        return q
    except Exception as exc:
        print(f"[MARKET] {ticker_symbol} dividend fetch failed ({exc}); using 0.0%")
        return 0.0


def select_expiry(ticker_obj, ticker_symbol, snapshot_time):
    expiries = ticker_obj.options
    if not expiries:
        print(f"[MARKET] No expiries listed for {ticker_symbol}")
        return None
    snapshot_date = pd.to_datetime(snapshot_time).normalize()
    candidates = [(exp, (pd.to_datetime(exp) - snapshot_date).days) for exp in expiries]
    preferred = [(e, d) for e, d in candidates if config.MIN_DTE <= d <= config.MAX_DTE]
    if preferred:
        chosen, dte = sorted(preferred, key=lambda x: x[1])[0]
        print(f"[MARKET] {ticker_symbol}: selected {chosen} ({dte} DTE)")
        return chosen
    if config.FALLBACK_TO_NEAREST:
        positive = sorted([(e, d) for e, d in candidates if d > 0], key=lambda x: x[1])
        if positive:
            chosen, dte = positive[0]
            print(f"[MARKET] {ticker_symbol}: fallback {chosen} ({dte} DTE)")
            return chosen
    print(f"[MARKET] {ticker_symbol}: no usable expiry")
    return None


def prepare_option_df(ticker_obj, ticker_symbol, spot, snapshot_time,
                      option_type, risk_free_rate, dividend_yield):
    expiry = select_expiry(ticker_obj, ticker_symbol, snapshot_time)
    if expiry is None:
        return pd.DataFrame()
    try:
        chain = ticker_obj.option_chain(expiry)
        options = chain.calls.copy() if option_type.lower() == "call" else chain.puts.copy()
    except Exception as exc:
        print(f"[MARKET] Option-chain fetch failed for {ticker_symbol}: {exc}")
        return pd.DataFrame()

    options["snapshot_time"] = snapshot_time.strftime("%Y-%m-%d %H:%M:%S")
    options["ticker"] = ticker_symbol
    options["underlying_price"] = spot
    options["option_type"] = option_type.capitalize()
    options["expiry"] = expiry
    options["mid_price"] = (options["bid"] + options["ask"]) / 2
    options["days_to_expiry"] = (
        pd.to_datetime(options["expiry"]) - pd.to_datetime(snapshot_time).normalize()
    ).dt.days
    options["risk_free_rate"] = risk_free_rate
    options["dividend_yield"] = dividend_yield
    options = options.rename(columns={
        "openInterest": "open_interest",
        "impliedVolatility": "yahoo_iv",
        "lastPrice": "last_trade_price",
    })
    columns = [
        "snapshot_time", "ticker", "underlying_price", "option_type", "expiry",
        "days_to_expiry", "strike", "bid", "ask", "mid_price",
        "last_trade_price", "volume", "open_interest", "yahoo_iv",
        "risk_free_rate", "dividend_yield",
    ]
    return options[columns]


def create_market_snapshot():
    snapshot_time = datetime.now()
    risk_free_rate = fetch_risk_free_rate()
    frames = []
    for symbol in config.TICKERS:
        ticker_obj = yf.Ticker(symbol)
        try:
            spot = float(ticker_obj.fast_info["lastPrice"])
            print(f"[MARKET] {symbol} price: ${spot:.2f}")
        except Exception as exc:
            print(f"[MARKET] Price fetch failed for {symbol}: {exc}")
            continue
        q = estimate_dividend_yield(ticker_obj, symbol, spot, snapshot_time)
        frame = prepare_option_df(
            ticker_obj, symbol, spot, snapshot_time, config.OPTION_TYPE,
            risk_free_rate, q,
        )
        if not frame.empty:
            print(f"[MARKET] Retrieved {len(frame)} contracts for {symbol}")
            frames.append(frame)
    return (pd.concat(frames, ignore_index=True), snapshot_time) if frames else (pd.DataFrame(), snapshot_time)
