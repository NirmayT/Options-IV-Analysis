import numpy as np
import pandas as pd
import yfinance as yf
import config


def fetch_historical_vix(start_date, end_date):
    try:
        raw = yf.download(config.VIX_TICKER, start=start_date, end=end_date, progress=False)
        if raw.empty:
            return pd.DataFrame(columns=["date", "vix_level"])
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        close = close.reset_index()
        close.columns = ["date", "vix_level"]
        close["date"] = pd.to_datetime(close["date"]).dt.strftime("%Y-%m-%d")
        return close
    except Exception as exc:
        print(f"[REGIME] VIX fetch failed: {exc}")
        return pd.DataFrame(columns=["date", "vix_level"])


def classify_vix_regime(value):
    if pd.isna(value): return "Unknown"
    if value < config.CALM_VIX_THRESHOLD: return "Calm"
    if value < config.STRESSED_VIX_THRESHOLD: return "Normal"
    return "Stressed"


def assign_regimes(df):
    if df.empty or "snapshot_time" not in df.columns:
        return df
    out = df.copy()
    out["snapshot_date"] = pd.to_datetime(out["snapshot_time"]).dt.strftime("%Y-%m-%d")
    start = (pd.to_datetime(out["snapshot_date"].min()) - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end = (pd.to_datetime(out["snapshot_date"].max()) + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    vix = fetch_historical_vix(start, end)
    if not vix.empty:
        vix["date_dt"] = pd.to_datetime(vix["date"])
        out["snapshot_dt"] = pd.to_datetime(out["snapshot_date"])
        out = pd.merge_asof(
            out.sort_values("snapshot_dt"),
            vix[["date_dt", "vix_level"]].sort_values("date_dt"),
            left_on="snapshot_dt", right_on="date_dt", direction="backward"
        )
        out = out.drop(columns=["date_dt", "snapshot_dt"], errors="ignore")
    else:
        out["vix_level"] = np.nan
    out["regime"] = out["vix_level"].apply(classify_vix_regime)
    return out.drop(columns=["snapshot_date"], errors="ignore")


def calculate_smile_metrics(df):
    if df.empty:
        return pd.DataFrame()
    rows = []
    groups = ["snapshot_time", "ticker", "expiry", "regime"]
    for keys, group in df.groupby(groups):
        atm = group["moneyness"].between(config.ATM_LOWER, config.ATM_UPPER)
        low = group["moneyness"] < config.DOWN_WING_THRESHOLD
        high = group["moneyness"] > config.UP_WING_THRESHOLD
        atm_iv = group.loc[atm, "calculated_iv"].mean()
        low_iv = group.loc[low, "calculated_iv"].mean()
        high_iv = group.loc[high, "calculated_iv"].mean()
        rec = dict(zip(groups, keys))
        rec.update({
            "atm_iv": atm_iv,
            "downside_wing_call_iv": low_iv,
            "upside_wing_call_iv": high_iv,
            "downside_call_skew": low_iv - atm_iv if pd.notna(low_iv) and pd.notna(atm_iv) else np.nan,
            "upside_call_skew": high_iv - atm_iv if pd.notna(high_iv) and pd.notna(atm_iv) else np.nan,
            "total_contracts": len(group),
        })
        for lo, hi, label in config.MONEYNESS_BUCKETS:
            rec[f"iv_bucket_{label}"] = group.loc[group["moneyness"].between(lo, hi, inclusive="left"), "calculated_iv"].mean()
        rows.append(rec)
    return pd.DataFrame(rows)


def calculate_regime_summary(df, snapshot_time_str=None):
    if df.empty:
        return pd.DataFrame()
    date = snapshot_time_str.split(" ")[0] if snapshot_time_str else pd.to_datetime(df["snapshot_time"].iloc[0]).strftime("%Y-%m-%d")
    rows = []
    for (ticker, regime), group in df.groupby(["ticker", "regime"]):
        atm = group["moneyness"].between(config.ATM_LOWER, config.ATM_UPPER)
        lo = group["moneyness"] < config.DOWN_WING_THRESHOLD
        hi = group["moneyness"] > config.UP_WING_THRESHOLD
        atm_iv = group.loc[atm, "calculated_iv"].mean()
        low_iv = group.loc[lo, "calculated_iv"].mean()
        high_iv = group.loc[hi, "calculated_iv"].mean()
        rows.append({
            "snapshot_date": date, "ticker": ticker, "regime": regime,
            "avg_iv": group["calculated_iv"].mean(),
            "median_iv": group["calculated_iv"].median(),
            "atm_iv": atm_iv, "downside_wing_call_iv": low_iv,
            "upside_wing_call_iv": high_iv,
            "avg_downside_call_skew": low_iv - atm_iv if pd.notna(low_iv) and pd.notna(atm_iv) else np.nan,
            "observations": len(group),
        })
    out = pd.DataFrame(rows)
    order = ["Calm", "Normal", "Stressed", "Unknown"]
    out["regime"] = pd.Categorical(out["regime"], categories=order, ordered=True)
    return out.sort_values(["ticker", "regime"]).reset_index(drop=True)
