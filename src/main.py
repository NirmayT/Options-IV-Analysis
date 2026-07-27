import config
import market_data
import database_manager as db
import data_validation as dv
import analytics
import analytics_validation as av
import regime_analysis as ra
import visualization as viz

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

    if clean_df.empty:
        print("[PIPELINE] Warning: Zero records survived data cleaning parameters. Aborting downstream steps.")
        print("=" * 150 + "\n")
        return

    print(f"[PIPELINE] Writing {len(clean_df)} valid records to analytical engine")
    db.save_clean_snapshot(clean_df)
    print("[PIPELINE] Clean data snapshot successfully persisted.")

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

    # STEP 9: Assign historical VIX levels and classify market regimes
    print("\n[RESEARCH] Matching option data with market fear levels (VIX)")
    regime_enriched_df = ra.assign_regimes(validated_analytics_df)

    # STEP 10: Calculate price curves
    print("[RESEARCH] Calculating price curves and insurance costs")
    smile_df = ra.calculate_smile_metrics(regime_enriched_df)

    # STEP 11: Create a simple comparison summary table
    print("[RESEARCH] Building summary table")
    today_str = snapshot_time.strftime("%Y-%m-%d")
    regime_summary_df = ra.calculate_regime_summary(regime_enriched_df, snapshot_time_str=today_str)

    print("\n" + "-" * 50 + " MARKET ENVIRONMENT SUMMARY " + "-" * 50)
    print(regime_summary_df.to_string(index=False))
    print("-" * 150)

    # STEP 12: Save the finished research data into the database tables
    print(f"\n[RESEARCH] Saving detailed results to {config.REGIME_ANALYSIS_TABLE}")
    db.save_regime_analysis_snapshot(smile_df)

    today_str = snapshot_time.strftime("%Y-%m-%d")
    print(f"[RESEARCH] Saving summary totals to {config.REGIME_SUMMARY_TABLE}")
    db.save_regime_summary_snapshot(regime_summary_df)

    print(regime_summary_df.head())

    # STEP 13: Generate research figures and validation charts
    viz.generate_all_plots(regime_enriched_df, regime_summary_df)

    print("\n" + "=" * 150)
    print("PIPELINE & RESEARCH COMPLETED SUCCESSFULLY")
    print("=" * 150 + "\n")

if __name__ == "__main__":
    main()