from pathlib import Path

# Paths are absolute, so the project works whether main.py is run from the
# repository root or from inside src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_NAME = str(PROJECT_ROOT / "database" / "options.db")
DATABASE_PATH = DATABASE_NAME
PLOTS_DIR = str(PROJECT_ROOT / "plots")

# Instruments. Change only these entries to run another Yahoo-supported
# stock/ETF pair. The aliases below preserve compatibility with older modules.
PRIMARY_INSTRUMENT = {
    "ticker": "JPM",
    "name": "JPMorgan Chase",
    "description": "single financial institution",
    "instrument_type": "stock",
    "exercise_style": "American",
}
COMPARISON_INSTRUMENT = {
    "ticker": "XLF",
    "name": "Financial Select Sector SPDR Fund",
    "description": "diversified financial-sector ETF",
    "instrument_type": "ETF",
    "exercise_style": "American",
}

PRIMARY_TICKER = PRIMARY_INSTRUMENT["ticker"]
COMPARISON_TICKER = COMPARISON_INSTRUMENT["ticker"]
TICKERS = [PRIMARY_TICKER, COMPARISON_TICKER]

# Backward-compatible aliases.
STOCK_TICKER = PRIMARY_TICKER
ETF_TICKER = COMPARISON_TICKER

VIX_TICKER = "^VIX"
OPTION_TYPE = "Call"

TIME_WINDOW_MINUTES = 15
IV_SOLVER_TOLERANCE = 1e-4

# Short-term rate proxy and fallback.
RISK_FREE_TICKER = "^IRX"
RISK_FREE_RATE = 0.05
DIVIDEND_LOOKBACK_DAYS = 365

# Select one reasonably liquid maturity instead of blindly using nearest expiry.
MIN_DTE = 20
MAX_DTE = 45
FALLBACK_TO_NEAREST = True

CALM_VIX_THRESHOLD = 20.0
STRESSED_VIX_THRESHOLD = 30.0

# Project-wide convention: moneyness = spot / strike.
ATM_LOWER = 0.98
ATM_UPPER = 1.02
DOWN_WING_THRESHOLD = 0.90
UP_WING_THRESHOLD = 1.10
MONEYNESS_BUCKETS = [
    (0.80, 0.90, "0.80-0.90"),
    (0.90, 0.95, "0.90-0.95"),
    (0.95, 1.00, "0.95-1.00"),
    (1.00, 1.05, "1.00-1.05"),
    (1.05, 1.10, "1.05-1.10"),
    (1.10, 1.20, "1.10-1.20"),
]

# Research-chart quality filters. These affect charts only, not stored data.
SMILE_LOG_M_MIN = -0.12
SMILE_LOG_M_MAX = 0.12
PLOT_IV_MIN = 0.01
PLOT_IV_MAX = 1.00
MAX_RELATIVE_SPREAD = 0.30
MIN_OPTION_MID_PRICE = 0.10
REQUIRE_POSITIVE_BID_FOR_SMILE = True

RAW_OPTIONS_TABLE = "options_raw"
CLEAN_OPTIONS_TABLE = "options_cleaned"
ANALYTICS_OPTIONS_TABLE = "options_analytics"
REGIME_ANALYSIS_TABLE = "options_regime_analysis"
REGIME_SUMMARY_TABLE = "regime_summary_outputs"
