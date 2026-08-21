import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from black_scholes import black_scholes_call
from implied_volatility import calculate_implied_volatility


def test_dividend_lowers_call_price():
    no_div = black_scholes_call(100, 100, 30, 0.20, 0.04, 0.0)
    with_div = black_scholes_call(100, 100, 30, 0.20, 0.04, 0.03)
    assert with_div < no_div


def test_iv_round_trip():
    price = black_scholes_call(100, 100, 30, 0.25, 0.04, 0.02)
    iv = calculate_implied_volatility(100, 100, 30, price, 0.04, 0.02)
    assert abs(iv - 0.25) < 0.001


def test_impossible_price_returns_nan():
    iv = calculate_implied_volatility(100, 100, 30, 999, 0.04, 0.0)
    assert np.isnan(iv)
