import config
import market_data
import database_manager as db
import data_validation as dv
import analytics
import analytics_validation as av

from datetime import timedelta

def main():
    """
    Main orchestrator for the automated options data pipeline.
    Controls the end-to-end data flow:
    Get Data -> Wipe Old Duplicates -> Save Raw -> Clean Data -> Save Clean 
    -> Calculate Options Math -> Validate Analytics -> Save Final Results
    """

    print("\n" + "=" * 150)

    db.initialize_database()
    
    # STEP 1: Fetch Raw Market Snapshot from Yahoo Finance

    raw_df, snapshot_time = market_data.create_market_snapshot()

    if raw_df.empty:
        print("[PIPELINE] No data fetched from market source.")
        print("="*150 + "\n")
        return
    
    # STEP 2: Calculate the sliding replacement threshold

    cutoff_time = snapshot_time - timedelta(minutes=config.TIME_WINDOW_MINUTES)
    cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S')

    tickers = [config.STOCK_TICKER, config.ETF_TICKER]

    print(f"[PIPELINE] Purging records since {cutoff_str} to prevent duplicate PK errors")
    db.delete_recent_snapshot(cutoff_str, tickers)

    # STEP 3: Persist Raw Ingested Snapshot to Database

    print(f"[PIPELINE] Writing {len(raw_df)} records to raw repository")
    db.save_raw_snapshot(raw_df)
    print("[PIPELINE] Raw data snapshot successfully persisted.")

    # STEP 4: Run Data Quality Checks and Apply Cleaning Filters

    print("[PIPELINE] Handing snapshot off to validation engine")
    clean_df = dv.run_validation_and_cleaning(raw_df)

    # STEP 5: Persist Validated Data to Clean Production Table

    if not clean_df.empty:
        print(f"[PIPELINE] Writing {len(clean_df)} valid records to analytical engine")
        db.save_clean_snapshot(clean_df)
        print("[PIPELINE] Clean data snapshot successfully persisted.")
    else:
        print("[PIPELINE] Warning: Zero records survived data clearing parameters. Clean database unchanged.")

    print("\n" + "="*150)
    print("Pipeline Execution Completed Sucessfully")
    print("="*150 + "\n")

    # STEP 6: Run Black-Scholes math (calculate implied volatility and theoretical prices)
    analytics_df = analytics.generate_analytics_df(clean_df)

    # STEP 7: Validate mathematical outputs
    print("[PIPELINE] Validating analytics outputs and dropping hard numerical failures")
    validated_analytics_df = av.run_analytics_validation_and_cleaning(analytics_df)

    if validated_analytics_df.empty:
        print("[PIPELINE] Warning: Zero analytics records survived validation check.")
        print("=" * 150 + "\n")
        return

    # STEP 8: Save all the final calculated results into the master analytics table
    print(f"[PIPELINE] Saving {len(validated_analytics_df)} validated rows to the analytics table")
    db.save_analytics_snapshot(validated_analytics_df)
    print("[PIPELINE] Analytics data saved successfully.")

    print("\n--- Final Analytics Preview ---")
    print(validated_analytics_df.head())

    print("\n" + "=" * 150)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 150 + "\n")


if __name__ == "__main__":
    main()