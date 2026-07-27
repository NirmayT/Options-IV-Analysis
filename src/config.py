# Tickers and Option Type
STOCK_TICKER = "JPM"
ETF_TICKER = "XLF"
VIX_TICKER = "^VIX"
OPTION_TYPE = "Call"

# Parameters
TIME_WINDOW_MINUTES = 15
IV_SOLVER_TOLERANCE = 1e-4
RISK_FREE_RATE = 0.05  # Placeholder for risk-free rate

# Market regime thresholds
CALM_VIX_THRESHOLD = 20.0
STRESSED_VIX_THRESHOLD = 30.0

# Volatility Smile thresholds and buckets
ATM_LOWER = 0.98
ATM_UPPER = 1.02
DOWN_WING_THRESHOLD = 0.90
UP_WING_THRESHOLD = 1.10

# Moneyness ranges for smile curve plotting
MONEYNESS_BUCKETS = [
    (0.80, 0.90, "0.80-0.90"),
    (0.90, 0.95, "0.90-0.95"),
    (0.95, 1.00, "0.95-1.00"),
    (1.00, 1.05, "1.00-1.05"),
    (1.05, 1.10, "1.05-1.10"),
    (1.10, 1.20, "1.10-1.20"),
]

# Database
RAW_OPTIONS_TABLE = "options_raw"
CLEAN_OPTIONS_TABLE = "options_cleaned"
ANALYTICS_OPTIONS_TABLE = "options_analytics"
REGIME_ANALYSIS_TABLE = "options_regime_analysis"
REGIME_SUMMARY_TABLE = "regime_summary_outputs"
DATABASE_NAME = "database/options.db"
DATABASE_PATH = DATABASE_NAME  # Keep alias for database_manager.py compatibility