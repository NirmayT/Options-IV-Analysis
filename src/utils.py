import os
import pandas as pd
import matplotlib.pyplot as plt
import config


def validate_required_columns(df, required_cols):
    if df is None or df.empty:
        print("[UTILS] Empty DataFrame")
        return False
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"[UTILS] Missing columns: {missing}")
        return False
    return True


def filter_by_ticker(df, ticker):
    if df is None or df.empty or "ticker" not in df.columns:
        return pd.DataFrame()
    return df[df["ticker"].str.upper() == ticker.upper()].copy()


def filter_by_regime(df, regime):
    if df is None or df.empty or "regime" not in df.columns:
        return pd.DataFrame()
    return df[df["regime"].astype(str).str.casefold() == regime.casefold()].copy()


def save_figure(fig, filename, output_dir=None):
    output_dir = output_dir or config.PLOTS_DIR
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[UTILS] Saved figure: {path}")
