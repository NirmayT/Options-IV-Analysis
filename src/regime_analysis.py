import numpy as np
import pandas as pd
import yfinance as yf
import config

def fetch_historical_vix(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Retrieves daily historical VIX closing values from Yahoo Finance for a given date range
    Returns a DataFrame with ['date', 'vix_level']
    """
    try:
        vix_df = yf.download(config.VIX_TICKER, start=start_date, end=end_date, progress=False)
        if vix_df.empty:
            print(f"[REGIME ANALYSIS] Warning: Empty VIX response for {start_date} to {end_date}.")
            return pd.DataFrame(columns=["date", "vix_level"])

        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df = vix_df["Close"]
        else:
            vix_df = vix_df[["Close"]]

        vix_df = vix_df.reset_index()
        vix_df.columns = ["date", "vix_level"]
        vix_df["date"] = pd.to_datetime(vix_df["date"]).dt.strftime("%Y-%m-%d")

        return vix_df

    except Exception as e:
        print(f"[REGIME ANALYSIS] Error fetching historical VIX: {e}")
        return pd.DataFrame(columns=["date", "vix_level"])

def classify_vix_regime(vix_value: float) -> str:
    """
    Converts scalar VIX level to market regime:
        - NaN / Null -> Unknown
        - VIX < CALM_VIX_THRESHOLD -> Calm
        - CALM <= VIX < STRESSED_VIX_THRESHOLD -> Normal
        - VIX >= STRESSED_VIX_THRESHOLD -> Stressed
    """
    if pd.isna(vix_value):
        return "Unknown"
    if vix_value < config.CALM_VIX_THRESHOLD:
        return "Calm"
    elif vix_value < config.STRESSED_VIX_THRESHOLD:
        return "Normal"
    else:
        return "Stressed"

def assign_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges historical daily VIX values with options snapshots matching on snapshot date.
    Temporal Join: snapshot_date -> VIX date -> regime label.
    """
    if df.empty or "snapshot_time" not in df.columns:
        return df

    df_out = df.copy()

    # Extract calendar date from snapshot timestamp
    df_out["snapshot_date"] = pd.to_datetime(df_out["snapshot_time"]).dt.strftime("%Y-%m-%d")

    min_date = (pd.to_datetime(df_out["snapshot_date"].min()) - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    max_date = (pd.to_datetime(df_out["snapshot_date"].max()) + pd.Timedelta(days=2)).strftime("%Y-%m-%d")

    vix_df = fetch_historical_vix(min_date, max_date)

    if not vix_df.empty:
        vix_df["date_dt"] = pd.to_datetime(vix_df["date"])
        df_out["snapshot_dt"] = pd.to_datetime(df_out["snapshot_date"])

        vix_df = vix_df.sort_values("date_dt")
        df_out = df_out.sort_values("snapshot_dt")

        df_out = pd.merge_asof(
            df_out,
            vix_df[["date_dt", "vix_level"]],
            left_on="snapshot_dt",
            right_on="date_dt",
            direction="backward"
        )
        df_out.drop(columns=["date_dt", "snapshot_dt"], inplace=True, errors="ignore")
    else:
        # Preserve missing data integrity with NaN instead of arbitrary fallbacks
        df_out["vix_level"] = np.nan

    df_out["regime"] = df_out["vix_level"].apply(classify_vix_regime)
    df_out.drop(columns=["snapshot_date"], inplace=True, errors="ignore")

    return df_out

def calculate_smile_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates volatility smile geometry per (snapshot, ticker, expiry, regime).

    NOTE: Downside wing IV is calculated from lower-strike CALL options as a proxy
          for the left side of the volatility smile (not true put IVs).
    """
    if df.empty or "calculated_iv" not in df.columns or "moneyness" not in df.columns:
        return pd.DataFrame()

    results = []
    group_cols = [c for c in ["snapshot_time", "ticker", "expiry", "regime"] if c in df.columns]

    for keys, group in df.groupby(group_cols):
        atm_mask = (group["moneyness"] >= config.ATM_LOWER) & (group["moneyness"] <= config.ATM_UPPER)
        down_mask = group["moneyness"] < config.DOWN_WING_THRESHOLD
        up_mask = group["moneyness"] > config.UP_WING_THRESHOLD

        atm_iv = group.loc[atm_mask, "calculated_iv"].mean()
        downside_wing_call_iv = group.loc[down_mask, "calculated_iv"].mean()
        upside_wing_call_iv = group.loc[up_mask, "calculated_iv"].mean()

        downside_call_skew = (downside_wing_call_iv - atm_iv) if pd.notna(downside_wing_call_iv) and pd.notna(atm_iv) else np.nan
        upside_call_skew = (upside_wing_call_iv - atm_iv) if pd.notna(upside_wing_call_iv) and pd.notna(atm_iv) else np.nan

        snapshot_record = dict(zip(group_cols, keys))
        snapshot_record.update({
            "atm_iv": atm_iv,
            "downside_wing_call_iv": downside_wing_call_iv,
            "upside_wing_call_iv": upside_wing_call_iv,
            "downside_call_skew": downside_call_skew,
            "upside_call_skew": upside_call_skew,
            "total_contracts": len(group)
        })

        # Fine-grained moneyness buckets for curve plotting
        for low, high, label in config.MONEYNESS_BUCKETS:
            bucket_mask = (group["moneyness"] >= low) & (group["moneyness"] < high)
            snapshot_record[f"iv_bucket_{label}"] = group.loc[bucket_mask, "calculated_iv"].mean()

        results.append(snapshot_record)

    return pd.DataFrame(results)

def calculate_regime_summary(df: pd.DataFrame, snapshot_time_str: str = None) -> pd.DataFrame:
    """
    Aggregates implied volatility metrics across Ticker x Regime.
    Applies custom Categorical sorting to force logical order: Calm -> Normal -> Stressed -> Unknown.
    """
    if df.empty or "calculated_iv" not in df.columns or "regime" not in df.columns:
        return pd.DataFrame()

    summary_rows = []
    
    # Extract date string from snapshot_time if passed or present in df
    if snapshot_time_str:
        calc_date = snapshot_time_str.split(" ")[0]
    elif "snapshot_time" in df.columns and not df["snapshot_time"].empty:
        calc_date = pd.to_datetime(df["snapshot_time"].iloc[0]).strftime("%Y-%m-%d")
    else:
        calc_date = pd.Timestamp.now().strftime("%Y-%m-%d")

    for (ticker, regime), group in df.groupby(["ticker", "regime"]):
        atm_mask = (group["moneyness"] >= config.ATM_LOWER) & (group["moneyness"] <= config.ATM_UPPER)
        down_mask = group["moneyness"] < config.DOWN_WING_THRESHOLD
        up_mask = group["moneyness"] > config.UP_WING_THRESHOLD

        atm_iv = group.loc[atm_mask, "calculated_iv"].mean()
        downside_wing_call_iv = group.loc[down_mask, "calculated_iv"].mean()
        upside_wing_call_iv = group.loc[up_mask, "calculated_iv"].mean()

        downside_call_skew = (downside_wing_call_iv - atm_iv) if pd.notna(downside_wing_call_iv) and pd.notna(atm_iv) else np.nan

        summary_rows.append({
            "snapshot_date": calc_date,
            "ticker": ticker,
            "regime": regime,
            "avg_iv": group["calculated_iv"].mean(),
            "median_iv": group["calculated_iv"].median(),
            "atm_iv": atm_iv,
            "downside_wing_call_iv": downside_wing_call_iv,
            "upside_wing_call_iv": upside_wing_call_iv,
            "avg_downside_call_skew": downside_call_skew,
            "observations": len(group)
        })

    summary_df = pd.DataFrame(summary_rows)

    # Force natural regime sorting instead of alphabetical
    regime_order = ["Calm", "Normal", "Stressed", "Unknown"]
    summary_df["regime"] = pd.Categorical(summary_df["regime"], categories=regime_order, ordered=True)

    return summary_df.sort_values(by=["ticker", "regime"]).reset_index(drop=True)