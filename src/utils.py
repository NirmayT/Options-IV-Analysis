import os
import matplotlib.pyplot as plt
import pandas as pd

def validate_required_columns(df: pd.DataFrame, required_cols: list) -> bool:
    """Ensures input DataFrame contains necessary columns before processing."""
    if df is None or df.empty:
        print("[UTILS] Warning: Provided DataFrame is empty or None.")
        return False
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"[UTILS] Missing required columns: {missing}")
        return False
    return True


def filter_by_ticker(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Safely filters DataFrame for a given ticker."""
    if df is None or df.empty or "ticker" not in df.columns:
        return pd.DataFrame()
    return df[df["ticker"].str.upper() == ticker.upper()].copy()


def filter_by_regime(df: pd.DataFrame, regime: str) -> pd.DataFrame:
    """Safely filters DataFrame for a given market regime."""
    if df is None or df.empty or "regime" not in df.columns:
        return pd.DataFrame()
    return df[df["regime"].str.capitalize() == regime.capitalize()].copy()


def save_figure(fig: plt.Figure, filename: str, output_dir: str = "plots") -> None:
    """Saves matplotlib figure to specified directory with robust path creation and closes it."""
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.close(fig)  # Releases memory buffer
    print(f"[UTILS] Saved research figure to: {file_path}")