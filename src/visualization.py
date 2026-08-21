import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import config
import utils

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 0.8

REGIME_COLORS = {
    "Calm": "#2ca02c",
    "Normal": "#1f77b4",
    "Stressed": "#d62728",
    "Unknown": "#7f7f7f",
}

TICKER_COLORS = {
    config.STOCK_TICKER: "#1f77b4",
    config.ETF_TICKER: "#ff7f0e",
}


def _clean_smile_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies presentation-quality filters without deleting rows from the
    analytical database. The aim is to avoid interpreting wide-spread,
    near-zero-premium quotes as reliable smile information.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    required = ["log_moneyness", "calculated_iv", "mid_price"]
    out = out.dropna(subset=[c for c in required if c in out.columns])

    out = out[
        out["log_moneyness"].between(
            config.SMILE_LOG_M_MIN,
            config.SMILE_LOG_M_MAX,
            inclusive="both",
        )
    ]
    out = out[
        out["calculated_iv"].between(
            config.PLOT_IV_MIN,
            config.PLOT_IV_MAX,
            inclusive="both",
        )
    ]
    out = out[out["mid_price"] >= config.MIN_OPTION_MID_PRICE]

    if "relative_spread" in out.columns:
        out = out[
            out["relative_spread"].notna()
            & (out["relative_spread"] <= config.MAX_RELATIVE_SPREAD)
        ]

    if config.REQUIRE_POSITIVE_BID_FOR_SMILE and "bid" in out.columns:
        out = out[out["bid"] > 0]

    return out.sort_values(["ticker", "log_moneyness"])


def _add_sample_note(ax, before: int, after: int) -> None:
    ax.text(
        0.99,
        0.02,
        f"Quote-quality filter retained {after} of {before} contracts",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#666666",
        bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none"},
    )


def plot_volatility_smile(df: pd.DataFrame, ticker: str):
    """Plots the cleaned single-ticker IV curve for the current snapshot."""
    required = [
        "ticker",
        "log_moneyness",
        "calculated_iv",
        "mid_price",
    ]
    if not utils.validate_required_columns(df, required):
        return

    raw_ticker = utils.filter_by_ticker(df, ticker)
    plot_df = _clean_smile_data(raw_ticker)
    if plot_df.empty:
        print(f"[VISUALIZATION] No quality-filtered smile data for {ticker}.")
        return

    plot_df = plot_df.copy()
    plot_df["iv_pct"] = plot_df["calculated_iv"] * 100

    fig, ax = plt.subplots(figsize=(9, 5))
    color = TICKER_COLORS.get(ticker, "#1f77b4")

    ax.scatter(
        plot_df["log_moneyness"],
        plot_df["iv_pct"],
        color=color,
        alpha=0.72,
        s=42,
        label="Quality-filtered contracts",
    )

    # A connected curve is more honest than calling single-observation bins a
    # mean trend. The data are sorted by moneyness before connecting.
    ax.plot(
        plot_df["log_moneyness"],
        plot_df["iv_pct"],
        color="black",
        linewidth=1.8,
        alpha=0.85,
        label="Observed IV curve",
    )

    ax.axvline(
        0.0,
        color="gray",
        linestyle="--",
        alpha=0.8,
        label="ATM",
    )

    atm = plot_df.iloc[(plot_df["log_moneyness"].abs()).argsort()[:1]]
    if not atm.empty:
        atm_x = float(atm["log_moneyness"].iloc[0])
        atm_y = float(atm["iv_pct"].iloc[0])
        ax.annotate(
            f"Nearest ATM: {atm_y:.1f}%",
            xy=(atm_x, atm_y),
            xytext=(10, 15),
            textcoords="offset points",
            fontsize=9,
            arrowprops={"arrowstyle": "->", "color": "#555555"},
        )

    ax.set_title(f"{ticker} Implied Volatility Curve", fontsize=13, fontweight="bold")
    ax.set_xlabel("Log-Moneyness ln(Spot / Strike)", fontsize=11)
    ax.set_ylabel("Calculated Implied Volatility (%)", fontsize=11)
    ax.legend(frameon=True)
    _add_sample_note(ax, len(raw_ticker), len(plot_df))

    utils.save_figure(fig, f"{ticker.lower()}_volatility_curve.png")


def plot_smile_comparison(df: pd.DataFrame):
    """Directly compares the configured instruments at comparable log-moneyness levels."""
    required = ["ticker", "log_moneyness", "calculated_iv", "mid_price"]
    if not utils.validate_required_columns(df, required):
        return

    plot_df = _clean_smile_data(df)
    if plot_df.empty:
        print("[VISUALIZATION] No quality-filtered data for smile comparison.")
        return

    plot_df = plot_df.copy()
    plot_df["iv_pct"] = plot_df["calculated_iv"] * 100
    plot_df["moneyness_bin"] = plot_df["log_moneyness"].round(2)

    curve_df = (
        plot_df.groupby(["ticker", "moneyness_bin"], observed=True)
        .agg(iv_pct=("iv_pct", "median"), observations=("iv_pct", "size"))
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    for ticker, group in curve_df.groupby("ticker", observed=True):
        group = group.sort_values("moneyness_bin")
        ax.plot(
            group["moneyness_bin"],
            group["iv_pct"],
            marker="o",
            linewidth=2.0,
            label=ticker,
            color=TICKER_COLORS.get(ticker),
        )

    ax.axvline(0.0, color="gray", linestyle="--", alpha=0.8, label="ATM")
    ax.set_title(f"{config.PRIMARY_TICKER} vs {config.COMPARISON_TICKER} Implied Volatility Curves", fontsize=13, fontweight="bold")
    ax.set_xlabel("Log-Moneyness ln(Spot / Strike)", fontsize=11)
    ax.set_ylabel("Calculated Implied Volatility (%)", fontsize=11)
    ax.legend(frameon=True)
    utils.save_figure(fig, f"{config.PRIMARY_TICKER.lower()}_vs_{config.COMPARISON_TICKER.lower()}_iv_curves.png")


def plot_atm_iv_comparison(df: pd.DataFrame):
    """Compares nearest-to-ATM calculated IV for each ticker."""
    required = ["ticker", "log_moneyness", "calculated_iv", "mid_price"]
    if not utils.validate_required_columns(df, required):
        return

    plot_df = _clean_smile_data(df)
    if plot_df.empty:
        return

    atm_rows = (
        plot_df.assign(abs_log_m=plot_df["log_moneyness"].abs())
        .sort_values(["ticker", "abs_log_m"])
        .groupby("ticker", observed=True)
        .head(1)
        .copy()
    )
    atm_rows["atm_iv_pct"] = atm_rows["calculated_iv"] * 100

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(
        data=atm_rows,
        x="ticker",
        y="atm_iv_pct",
        hue="ticker",
        palette=TICKER_COLORS,
        legend=False,
        ax=ax,
    )

    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f%%", padding=3)

    ax.set_title("Nearest-to-ATM Implied Volatility", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Calculated Implied Volatility (%)", fontsize=11)
    utils.save_figure(fig, f"atm_iv_{config.PRIMARY_TICKER.lower()}_vs_{config.COMPARISON_TICKER.lower()}.png")


def plot_calculated_vs_yahoo_iv(df: pd.DataFrame):
    """Benchmark comparison, with quote spread represented by marker size."""
    required = [
        "yahoo_iv",
        "calculated_iv",
        "ticker",
        "relative_spread",
    ]
    if not utils.validate_required_columns(df, required):
        return

    plot_df = df.dropna(subset=required).copy()
    if plot_df.empty:
        return

    plot_df["yahoo_iv_pct"] = plot_df["yahoo_iv"] * 100
    plot_df["calculated_iv_pct"] = plot_df["calculated_iv"] * 100
    plot_df["spread_for_size"] = plot_df["relative_spread"].clip(0, 1)

    fig, ax = plt.subplots(figsize=(7.5, 7))
    sns.scatterplot(
        data=plot_df,
        x="yahoo_iv_pct",
        y="calculated_iv_pct",
        hue="ticker",
        size="spread_for_size",
        sizes=(30, 150),
        palette=TICKER_COLORS,
        alpha=0.68,
        ax=ax,
    )

    max_val = max(plot_df["yahoo_iv_pct"].max(), plot_df["calculated_iv_pct"].max())
    min_val = min(0.0, plot_df["yahoo_iv_pct"].min(), plot_df["calculated_iv_pct"].min())
    ax.plot(
        [min_val, max_val],
        [min_val, max_val],
        color="black",
        linestyle="--",
        linewidth=1.4,
        label="1:1 identity",
    )

    stats = (
        plot_df.groupby("ticker", observed=True)
        .agg(
            observations=("calculated_iv", "size"),
            mean_abs_iv_diff=("abs_iv_difference", "mean"),
        )
    )
    stats_lines = [
        f"{ticker}: MAE {row.mean_abs_iv_diff * 100:.1f} vol pts (n={int(row.observations)})"
        for ticker, row in stats.iterrows()
    ]
    ax.text(
        0.98,
        0.03,
        "\n".join(stats_lines),
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "#cccccc"},
    )

    ax.set_title("Calculated IV vs Yahoo IV Benchmark", fontsize=13, fontweight="bold")
    ax.set_xlabel("Yahoo Finance IV (%)", fontsize=11)
    ax.set_ylabel("Calculated Midpoint IV (%)", fontsize=11)
    ax.legend(frameon=True)
    utils.save_figure(fig, "calculated_vs_yahoo_iv.png")


def plot_pricing_difference_by_ticker(df: pd.DataFrame):
    """Splits midpoint-minus-Yahoo-IV-price differences by ticker."""
    required = ["ticker", "pricing_error"]
    if not utils.validate_required_columns(df, required):
        return

    tickers = [t for t in [config.STOCK_TICKER, config.ETF_TICKER] if t in df["ticker"].unique()]
    if not tickers:
        return

    fig, axes = plt.subplots(1, len(tickers), figsize=(6.5 * len(tickers), 5), sharex=True)
    if len(tickers) == 1:
        axes = [axes]

    for ax, ticker in zip(axes, tickers):
        errors = df.loc[df["ticker"] == ticker, "pricing_error"].dropna()
        if errors.empty:
            ax.set_visible(False)
            continue

        sns.histplot(
            errors,
            kde=False,
            bins=min(15, max(6, len(errors) // 2)),
            color=TICKER_COLORS.get(ticker),
            ax=ax,
        )
        ax.axvline(0.0, color="red", linestyle="--", linewidth=1.4, label="Zero")
        ax.axvline(
            errors.median(),
            color="black",
            linestyle=":",
            linewidth=1.6,
            label=f"Median ${errors.median():.2f}",
        )
        ax.set_title(f"{ticker}: Midpoint - Price Using Yahoo IV", fontweight="bold")
        ax.set_xlabel("Pricing Difference ($)")
        ax.legend(frameon=True)

    axes[0].set_ylabel("Contract Count")
    for ax in axes[1:]:
        ax.set_ylabel("")
    utils.save_figure(fig, "pricing_difference_by_ticker.png")


def plot_iv_reconstruction_error(df: pd.DataFrame):
    """Shows numerical solver precision without a misleading KDE curve."""
    required = ["iv_reconstruction_error"]
    if not utils.validate_required_columns(df, required):
        return

    errors = df["iv_reconstruction_error"].dropna()
    if errors.empty:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(
        errors,
        kde=False,
        bins=min(20, max(8, len(errors) // 2)),
        color="#2ca02c",
        ax=ax,
    )
    ax.axvline(0.0, color="red", linestyle="--", linewidth=1.5, label="Zero error")

    mean_abs = errors.abs().mean()
    max_abs = errors.abs().max()
    within = (errors.abs() <= config.IV_SOLVER_TOLERANCE).mean() * 100
    ax.text(
        0.02,
        0.95,
        f"Mean absolute error: ${mean_abs:.6f}\n"
        f"Maximum absolute error: ${max_abs:.6f}\n"
        f"Within tolerance: {within:.1f}%",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.82, "edgecolor": "#cccccc"},
    )

    ax.set_title("IV Solver Reconstruction Error", fontsize=13, fontweight="bold")
    ax.set_xlabel("Market Midpoint - Reconstructed Price ($)", fontsize=11)
    ax.set_ylabel("Contract Count", fontsize=11)
    ax.legend(frameon=True)
    utils.save_figure(fig, "iv_reconstruction_error.png")


def generate_all_plots(regime_enriched_df: pd.DataFrame, summary_df: pd.DataFrame):
    """Generates only charts that the current snapshot can support honestly."""
    print("\n[VISUALIZATION] Rendering research and validation figures...")
    if regime_enriched_df is None or regime_enriched_df.empty:
        print("[VISUALIZATION] No data available.")
        return
    if "ticker" not in regime_enriched_df.columns:
        print("[VISUALIZATION] Ticker column missing.")
        return

    tickers = sorted(regime_enriched_df["ticker"].dropna().unique())
    print(f"[VISUALIZATION] Available tickers: {tickers}")

    for ticker in tickers:
        plot_volatility_smile(regime_enriched_df, ticker)

    plot_smile_comparison(regime_enriched_df)
    plot_atm_iv_comparison(regime_enriched_df)
    plot_calculated_vs_yahoo_iv(regime_enriched_df)
    plot_pricing_difference_by_ticker(regime_enriched_df)
    plot_iv_reconstruction_error(regime_enriched_df)

    known_regimes = (
        regime_enriched_df["regime"].dropna()
        .loc[lambda x: x != "Unknown"]
        .unique()
        if "regime" in regime_enriched_df.columns
        else []
    )
    if len(known_regimes) < 2:
        print(
            "[VISUALIZATION] Regime-comparison charts not generated: "
            "fewer than two known regimes are available."
        )

    print("[VISUALIZATION] Finished generating supported charts.")
