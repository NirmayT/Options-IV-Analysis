import pandas as pd
import numpy as np

def generate_validation_report(df: pd.DataFrame) -> dict:
    """
    Analyzes the data to identify and count anomalies.
    Returns a dictionary containing the validation report.
    """
    if df.empty:
        return {"Status": "Empty DataFrame"}
    
    report = {}
    total_rows = len(df)
    report["total_records"] = total_rows

    # 1. Null Checks
    report["null_bids"] = df['bid'].isnull().sum()
    report["null_asks"] = df['ask'].isnull().sum()

    # 2. Negative Prices
    report["negative_bids"] = (df['bid'] < 0).sum()
    report["negative_asks"] = (df['ask'] < 0).sum()
    report["negative_strikes"] = (df['strike'] <= 0).sum()

    # 3. Crossed Bid-Ask
    report["crossed_bid_ask"] = ((df['bid'] > df['ask']) & (df['bid'].notnull()) & (df['ask'].notnull())).sum()

    # 4. Duplicates 
    report["duplicate_records"] = df.duplicated(subset=['snapshot_time', 'ticker', 'expiry', 'strike', 'option_type']).sum()
    
    # 5. Liquidity Anomalies
    report["zero_volume"] = (df['volume'] == 0).sum()
    report["zero_open_interest"] = (df['open_interest'] == 0).sum()
    report["completely_illiquid"] = ((df['bid'] == 0) & (df['ask'] == 0)).sum()

    # 6. Expired Contracts
    report["expired_contracts"] = (df['days_to_expiry'] < 0).sum()

    return report