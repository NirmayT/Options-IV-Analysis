import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import utils

# Set uniform presentation styling
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

# Color Palettes for Consistency Across Plots
REGIME_COLORS = {
    "Calm": "#2ca02c",      # Green
    "Normal": "#1f77b4",    # Blue
    "Stressed": "#d62728",  # Red
    "Unknown": "#7f7f7f"   # Gray
}

TICKER_COLORS = {
    "JPM": "#1f77b4",
    "XLF": "#ff7f0e"
}

# ==============================================================================
# RESEARCH PLOTS (1 - 4)
# ==============================================================================

def plot_volatility_smile(df: pd.DataFrame, ticker: str, regime: str = None):
    """
    Plots the Volatility Smile (Calculated IV vs Log-Moneyness) for a single ticker.
    Optional regime filter allows zooming into a single market environment.
    """
    req_cols = ["ticker", "log_moneyness", "calculated_iv"]
    if not utils.validate_required_columns(df, req_cols):
        return

    filtered_df = utils.filter_by_ticker(df, ticker)
    if regime:
        filtered_df = utils.filter_by_regime(filtered_df, regime)

    if filtered_df.empty:
        print(f"[VISUALIZATION] Skipping smile plot: No data for {ticker} ({regime or 'All'}).")
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    sns.scatterplot(
        data=filtered_df,
        x="log_moneyness",
        y=filtered_df["calculated_iv"] * 100,
        hue="regime" if "regime" in filtered_df.columns and not regime else None,
        palette=REGIME_COLORS,
        alpha=0.6,
        s=30,
        ax=ax
    )

    # Binning for the smooth trendline
    filtered_df["log_m_bin"] = filtered_df["log_moneyness"].round(2)
    trend = filtered_df.groupby("log_m_bin")["calculated_iv"].mean().reset_index()
    ax.plot(trend["log_m_bin"], trend["calculated_iv"] * 100, color="black", linewidth=2, label="Mean Smile Trend")

    ax.axvline(0.0, color="gray", linestyle="--", alpha=0.7, label="ATM (Log-Moneyness = 0)")
    
    title_suffix = f"({regime} Regime)" if regime else "Across All Regimes"
    ax.set_title(f"Volatility Smile: {ticker} {title_suffix}", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Log-Moneyness ln(Strike / Spot)", fontsize=11)
    ax.set_ylabel("Calculated Implied Volatility (%)", fontsize=11)
    ax.legend(frameon=True)

    filename = f"{ticker.lower()}_volatility_smile.png" if not regime else f"{ticker.lower()}_smile_{regime.lower()}.png"
    utils.save_figure(fig, filename)


def plot_smile_by_regime(df: pd.DataFrame, ticker: str):
    """
    Overlays Volatility Smile curves for Calm, Normal, and Stressed regimes.
    Demonstrates how tail risk pricing shifts under market stress.
    """
    req_cols = ["ticker", "regime", "log_moneyness", "calculated_iv"]
    if not utils.validate_required_columns(df, req_cols):
        return

    ticker_df = utils.filter_by_ticker(df, ticker)
    if ticker_df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    ticker_df["log_m_bin"] = ticker_df["log_moneyness"].round(2)
    regime_curves = ticker_df.groupby(["regime", "log_m_bin"], observed=True)["calculated_iv"].mean().reset_index()

    for regime, group in regime_curves.groupby("regime", observed=True):
        if group.empty or regime not in REGIME_COLORS:
            continue
        ax.plot(
            group["log_m_bin"],
            group["calculated_iv"] * 100,
            marker="o",
            linewidth=2,
            label=f"{regime} Regime",
            color=REGIME_COLORS[regime]
        )

    ax.axvline(0.0, color="gray", linestyle="--", alpha=0.7, label="ATM")
    ax.set_title(f"{ticker} Volatility Smile Overlay Across Market Regimes", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Log-Moneyness ln(Strike / Spot)", fontsize=11)
    ax.set_ylabel("Implied Volatility (%)", fontsize=11)
    ax.legend(title="Regime", frameon=True)

    utils.save_figure(fig, f"{ticker.lower()}_smile_by_regime.png")


def plot_regime_summary_bars(summary_df: pd.DataFrame):
    """
    Grouped bar chart comparing Average IV and Downside Skew for JPM vs XLF.
    Uses regime_summary_df.
    """
    req_cols = ["ticker", "regime", "avg_iv", "avg_downside_call_skew"]
    if not utils.validate_required_columns(summary_df, req_cols):
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    plot_df = summary_df.copy()
    plot_df["avg_iv_pct"] = plot_df["avg_iv"] * 100
    plot_df["skew_pct"] = plot_df["avg_downside_call_skew"] * 100

    # Subplot 1: Average IV
    sns.barplot(
        data=plot_df,
        x="regime",
        y="avg_iv_pct",
        hue="ticker",
        palette=TICKER_COLORS,
        ax=ax1
    )
    ax1.set_title("Average Implied Volatility by Regime", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Market Regime", fontsize=10)
    ax1.set_ylabel("Average IV (%)", fontsize=10)

    # Subplot 2: Downside Call Skew
    sns.barplot(
        data=plot_df,
        x="regime",
        y="skew_pct",
        hue="ticker",
        palette=TICKER_COLORS,
        ax=ax2
    )
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("Downside Call Skew Premium by Regime", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Market Regime", fontsize=10)
    ax2.set_ylabel("Downside Skew Premium (pts %)", fontsize=10)

    utils.save_figure(fig, "regime_summary_jpm_vs_xlf.png")


# ==============================================================================
# VALIDATION PLOTS (5 - 7)
# ==============================================================================

def plot_calculated_vs_yahoo_iv(df: pd.DataFrame):
    """
    Scatter plot comparing Calculated IV vs Yahoo IV against a 45-degree identity line.
    Validates solver alignment with the market data baseline.
    """
    req_cols = ["yahoo_iv", "calculated_iv", "ticker"]
    if not utils.validate_required_columns(df, req_cols):
        return

    clean_data = df.dropna(subset=["yahoo_iv", "calculated_iv"]).copy()
    if clean_data.empty:
        return

    fig, ax = plt.subplots(figsize=(7, 7))

    sns.scatterplot(
        data=clean_data,
        x=clean_data["yahoo_iv"] * 100,
        y=clean_data["calculated_iv"] * 100,
        hue="ticker",
        palette=TICKER_COLORS,
        alpha=0.5,
        ax=ax
    )

    # 45-degree reference line
    max_val = max(clean_data["yahoo_iv"].max(), clean_data["calculated_iv"].max()) * 100
    ax.plot([0, max_val], [0, max_val], color="black", linestyle="--", linewidth=1.5, label="1:1 Identity Line")

    ax.set_title("Solver Validation: Calculated IV vs. Yahoo IV", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Yahoo Finance IV (%)", fontsize=11)
    ax.set_ylabel("Calculated Bisection IV (%)", fontsize=11)
    ax.legend(frameon=True)

    utils.save_figure(fig, "calculated_vs_yahoo_iv.png")


def plot_pricing_error_distribution(df: pd.DataFrame):
    """
    Histogram of pricing errors (Mid Price - BS Theoretical Price).
    Shows whether Black-Scholes using Yahoo IV systematically over- or under-prices.
    """
    req_cols = ["pricing_error"]
    if not utils.validate_required_columns(df, req_cols):
        return

    clean_errors = df["pricing_error"].dropna()
    if clean_errors.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    sns.histplot(clean_errors, kde=True, bins=40, color="#1f77b4", ax=ax)
    ax.axvline(0.0, color="red", linestyle="--", linewidth=1.5, label="Zero Error Line")

    ax.set_title("Pricing Error Distribution (Mid Price - BS Price)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Pricing Error ($)", fontsize=11)
    ax.set_ylabel("Option Contract Count", fontsize=11)
    ax.legend(frameon=True)

    utils.save_figure(fig, "pricing_error_distribution.png")


def plot_iv_reconstruction_error(df: pd.DataFrame):
    """
    Histogram of IV reconstruction error (Market Mid Price - Price Reconstructed from Calculated IV).
    Validates numerical convergence of the bisection solver.
    """
    req_cols = ["iv_reconstruction_error"]
    if not utils.validate_required_columns(df, req_cols):
        return

    clean_errors = df["iv_reconstruction_error"].dropna()
    if clean_errors.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    sns.histplot(clean_errors, kde=True, bins=40, color="#2ca02c", ax=ax)
    ax.axvline(0.0, color="red", linestyle="--", linewidth=1.5, label="Zero Convergence Error")

    ax.set_title("IV Reconstruction Error Distribution (Solver Precision)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Reconstruction Error ($)", fontsize=11)
    ax.set_ylabel("Option Contract Count", fontsize=11)
    ax.legend(frameon=True)

    utils.save_figure(fig, "iv_reconstruction_error.png")


# ==============================================================================
# MASTER ORCHESTRATOR
# ==============================================================================

def generate_all_plots(regime_enriched_df: pd.DataFrame, summary_df: pd.DataFrame):
    """
    Master function called at the end of main.py to render all figures.
    """
    print("\n[VISUALIZATION] Rendering research and validation figures...")

    # Plot 1 & 2: Individual Ticker Volatility Smiles
    plot_volatility_smile(regime_enriched_df, ticker="JPM")
    plot_volatility_smile(regime_enriched_df, ticker="XLF")

    # Plot 3: Regime Comparison Smile Overlays
    plot_smile_by_regime(regime_enriched_df, ticker="JPM")
    plot_smile_by_regime(regime_enriched_df, ticker="XLF")

    # Plot 4: Grouped Bar Chart Comparisons
    plot_regime_summary_bars(summary_df)

    # Plot 5: Solver Validation (Calculated vs Yahoo IV)
    plot_calculated_vs_yahoo_iv(regime_enriched_df)

    # Plot 6: Black-Scholes Fit Validation
    plot_pricing_error_distribution(regime_enriched_df)

    # Plot 7: Bisection Solver Precision Validation
    plot_iv_reconstruction_error(regime_enriched_df)

    print("[VISUALIZATION] All research and validation charts generated successfully.")