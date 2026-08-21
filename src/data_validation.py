import pandas as pd


def generate_validation_report(df):
    if df.empty:
        return {"Status": "Empty DataFrame"}
    return {
        "total_records": len(df),
        "null_bids": df["bid"].isnull().sum(),
        "null_asks": df["ask"].isnull().sum(),
        "negative_bids": (df["bid"] < 0).sum(),
        "negative_asks": (df["ask"] < 0).sum(),
        "negative_strikes": (df["strike"] <= 0).sum(),
        "crossed_bid_ask": ((df["bid"] > df["ask"]) & df["bid"].notna() & df["ask"].notna()).sum(),
        "duplicate_records": df.duplicated(subset=["snapshot_time", "ticker", "expiry", "strike", "option_type"]).sum(),
        "zero_volume": (df["volume"] == 0).sum(),
        "zero_open_interest": (df["open_interest"] == 0).sum(),
        "completely_illiquid": ((df["bid"] == 0) & (df["ask"] == 0)).sum(),
        "expired_contracts": (df["days_to_expiry"] < 0).sum(),
    }


def clean_option_data(df):
    if df.empty:
        return df
    out = df.dropna(subset=["bid", "ask", "strike", "mid_price"]).copy()
    out = out[(out["bid"] >= 0) & (out["ask"] >= 0) & (out["strike"] > 0)]
    out = out[out["bid"] <= out["ask"]]
    out = out[(out["bid"] > 0) | (out["ask"] > 0)]
    out = out.drop_duplicates(subset=["snapshot_time", "ticker", "expiry", "strike", "option_type"])
    return out[out["days_to_expiry"] >= 0]


def run_validation_and_cleaning(raw_df):
    if raw_df.empty:
        print("[VALIDATION] Empty input")
        return pd.DataFrame()
    print("=" * 120)
    print("--- Pre-Cleaning Report ---")
    for k, val in generate_validation_report(raw_df).items():
        print(f"{k}: {val}")
    clean = clean_option_data(raw_df)
    print("--- Post-Cleaning Report ---")
    for k, val in generate_validation_report(clean).items():
        print(f"{k}: {val}")
    print(f"[VALIDATION] Retained {len(clean)}/{len(raw_df)} rows ({len(clean)/len(raw_df)*100:.2f}%)")
    print("=" * 120)
    return clean
