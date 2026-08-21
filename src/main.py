from datetime import timedelta
import config
import market_data
import database_manager as db
import data_validation as dv
import analytics
import analytics_validation as av
import regime_analysis as ra
import visualization as viz


def main():
    print("\n" + "=" * 120)
    db.initialize_database()
    raw_df, snapshot_time = market_data.create_market_snapshot()
    if raw_df.empty:
        print("[PIPELINE] No market data fetched")
        return

    tickers = config.TICKERS
    cutoff = (snapshot_time - timedelta(minutes=config.TIME_WINDOW_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    today = snapshot_time.strftime("%Y-%m-%d")
    db.delete_recent_snapshot(cutoff, tickers)
    db.save_raw_snapshot(raw_df)

    clean_df = dv.run_validation_and_cleaning(raw_df)
    if clean_df.empty:
        print("[PIPELINE] No rows survived cleaning")
        return
    db.save_clean_snapshot(clean_df)

    analytics_df = analytics.generate_analytics_df(clean_df)
    validated = av.run_analytics_validation_and_cleaning(analytics_df)
    if validated.empty:
        print("[PIPELINE] No rows survived analytical validation")
        return
    db.save_analytics_snapshot(validated)

    enriched = ra.assign_regimes(validated)
    smile = ra.calculate_smile_metrics(enriched)
    summary = ra.calculate_regime_summary(enriched, today)
    print("\n--- CURRENT SNAPSHOT SUMMARY ---")
    print(summary.to_string(index=False))

    db.save_regime_analysis_snapshot(smile)
    db.delete_regime_summary_for_date(today, tickers)
    db.save_regime_summary_snapshot(summary)
    viz.generate_all_plots(enriched, summary)

    print("\nPIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 120)


if __name__ == "__main__":
    main()
