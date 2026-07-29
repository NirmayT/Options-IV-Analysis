# Options Implied Volatility Analysis

## Overview

This project is a Python-based options analysis pipeline focused on **JPMorgan Chase (JPM)** and the **Financial Select Sector SPDR Fund (XLF)**.

It collects call-option data from Yahoo Finance, checks the quality of the quotes, calculates theoretical option prices, estimates implied volatility, stores the results in a SQLite database, and creates charts for further analysis.

The project was built to answer a practical question:

> How do option prices and implied volatility differ between JPM and XLF, and how might those patterns change across different market conditions?

The project is still being improved. The current version provides the full data and analysis pipeline, while future updates will strengthen the treatment of expiries, interest rates, dividends, liquidity, and market-regime comparisons.

## What the Project Does

The pipeline follows these steps:

1. Downloads call-option chains for JPM and XLF.
2. Calculates the midpoint between each option's bid and ask prices.
3. Checks for missing, invalid, duplicate, expired, or unusable records.
4. Calculates a theoretical call price using the Black-Scholes model.
5. Estimates implied volatility using a custom bisection solver.
6. Reprices each option using the estimated volatility to test solver accuracy.
7. Calculates pricing differences, volatility differences, and moneyness measures.
8. Connects option observations with VIX data to classify market conditions.
9. Stores raw, cleaned, and analyzed data in SQLite.
10. Creates research and validation charts.

## Key Learning Outcomes

This project demonstrates practical experience with:

- Building a complete financial-data pipeline from collection to visualization
- Working with live option-chain data and bid-ask quotes
- Implementing Black-Scholes pricing rather than relying only on a library function
- Building and testing a custom implied-volatility solver
- Separating invalid data from unusual but potentially useful market observations
- Storing raw, cleaned, and analyzed results in SQL
- Using validation charts to identify model and data-quality issues
- Communicating preliminary findings without overstating the conclusions

## Why JPM and XLF?

JPM represents a single large financial institution, while XLF represents a broader group of financial companies.

Comparing them can help show whether option pricing for an individual bank behaves differently from option pricing for the wider financial sector.

## Project Structure

```text
Options-IV-Analysis/
├── main.py                    # Runs the full pipeline
├── config.py                  # Stores tickers, thresholds, and settings
├── market_data.py             # Downloads and prepares option-chain data
├── data_validation.py         # Checks and cleans raw market data
├── black_scholes.py           # Calculates theoretical call prices
├── implied_volatility.py      # Estimates implied volatility
├── analytics.py               # Creates pricing and volatility measures
├── analytics_validation.py    # Checks calculated outputs
├── regime_analysis.py         # Adds VIX regimes and smile measures
├── database_manager.py        # Creates and manages SQLite tables
├── visualization.py           # Creates research and validation charts
├── utils.py                   # Contains reusable helper functions
├── database/                  # Stores the SQLite database
└── plots/                     # Stores generated charts
```

## Main Methods

### Black-Scholes Pricing

The project uses the Black-Scholes model to estimate the theoretical value of a European call option.

The model uses:

- Current price of the underlying security
- Option strike price
- Time remaining until expiry
- Risk-free interest rate
- Volatility

In the current version, Yahoo Finance implied volatility is used to calculate the theoretical price. The result is compared with the market midpoint.

### Implied Volatility Solver

The project also includes a custom bisection solver.

Instead of accepting Yahoo Finance's implied volatility directly, the solver searches for the volatility that makes the Black-Scholes price match the option's market midpoint as closely as possible.

Bisection was selected because it is simple and stable. It repeatedly narrows the possible volatility range until the estimated option price is close to the observed market price.

### Solver Validation

After estimating implied volatility, the project puts that value back into the Black-Scholes model.

It then compares:

```text
Observed market midpoint
vs.
Price reconstructed from calculated implied volatility
```

A small difference suggests that the solver worked correctly. Large differences are reported for review.

### Market Regimes

The project uses the VIX as a broad measure of market uncertainty.

Market conditions are grouped as:

- **Calm:** VIX below 20
- **Normal:** VIX from 20 to below 30
- **Stressed:** VIX of 30 or higher
- **Unknown:** VIX data could not be matched to the option observation

This framework is designed to support comparisons of implied volatility across different market environments.

## Data Quality Checks

Before calculations are performed, the project checks for:

- Missing bid or ask prices
- Negative prices or strikes
- Bid prices above ask prices
- Duplicate option records
- Expired contracts
- Contracts with both bid and ask equal to zero
- Zero volume or open interest

The project separates unusable records from unusual but potentially useful observations. For example, an invalid price may be removed, while a high implied-volatility observation may be kept for further review.

## Database Design

The project uses SQLite and stores data at several stages:

- **Raw options:** Original market snapshot
- **Cleaned options:** Records that pass the market-data checks
- **Options analytics:** Contract-level pricing and volatility results
- **Regime analysis:** Volatility-smile and skew measures by snapshot and expiry
- **Regime summary:** Higher-level results by ticker and market condition

Keeping these stages separate makes it easier to trace an observation from its original market quote to the final analysis.

## Output Charts

The pipeline can create:

- Volatility-smile charts for JPM and XLF
- Volatility-smile comparisons across market regimes
- Calculated implied volatility versus Yahoo Finance implied volatility
- Black-Scholes pricing-error distribution
- Implied-volatility reconstruction-error distribution
- Average implied volatility by ticker and market regime
- Downside call-skew comparisons

Charts are saved to the `plots/` directory.

## Current Results

The first completed run confirms that the pipeline can collect option quotes, clean market data, calculate theoretical prices, estimate implied volatility, store contract-level results, and generate analytical outputs from a single workflow.

For much of the initial JPM sample, the custom implied-volatility estimates move in the same general direction as Yahoo Finance's reported values. The results also contain outliers, showing that the analysis is sensitive to quote quality, time to expiry, and the model's current simplifying assumptions.

The reconstruction test provides a second check on the solver by comparing the observed option midpoint with the price rebuilt from calculated implied volatility. Many contracts produce relatively small differences, while a smaller group has larger errors that require further review.

The current output should be treated as a proof of concept rather than a final market conclusion. XLF is not appearing consistently in the processed results, and the visualization layer is being reviewed before charts are published in this README. The available sample also does not yet support a complete comparison across calm, normal, and stressed VIX regimes.

## Current Limitations

The main limitations are:

- XLF is not yet appearing consistently in the final analyzed dataset, and the pipeline is being checked stage by stage to identify where those records are lost.
- The visualization module is being stabilized before charts are included in the README.
- The current data collection focuses on the nearest available expiry.
- The risk-free rate is currently a fixed project setting.
- Dividend yield is not yet included in the Black-Scholes calculation.
- Some option quotes may be stale or have wide bid-ask spreads.
- The current results do not yet contain enough observations across all VIX regimes.
- Moneyness and wing labels need to be made fully consistent before final skew conclusions are drawn.
- The project currently analyzes calls only, so lower-strike calls are not the same as directly analyzing downside put protection.
- Yahoo Finance is convenient for research, but its data may differ from professional market-data sources.

These limitations are documented to avoid overstating the findings.

## Planned Improvements

The next improvements are:

1. Collect several expiries within a selected range of days to expiry.
2. Use a short-term Treasury yield as a changing risk-free-rate estimate.
3. Include dividend yield in the Black-Scholes model.
4. Add clearer solver-convergence flags and failure reasons.
5. Improve filters for wide spreads and low-liquidity contracts.
6. Standardize the moneyness definition across calculations and charts.
7. Improve the date matching between option snapshots and VIX observations.
8. Collect more historical snapshots across calm, normal, and stressed markets.
9. Compare results across both moneyness and time to expiry.
10. Add put options for a more direct study of downside protection.

## Installation

Clone the repository:

```bash
git clone https://github.com/NirmayT/Options-IV-Analysis
cd Options-IV-Analysis
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
pip install pandas numpy scipy yfinance sqlalchemy matplotlib seaborn
```

## Running the Project

Run the full pipeline from the project directory:

```bash
python main.py
```

If successful, the program will:

- Create or connect to the SQLite database
- Download a new options snapshot
- Validate and clean the data
- Calculate option-pricing and volatility measures
- Save the results
- Generate charts in the `plots/` directory

## Tools Used

- Python
- pandas
- NumPy
- SciPy
- yfinance
- SQLAlchemy
- SQLite
- Matplotlib
- Seaborn

## Disclaimer

This project is for educational and research purposes only. It is not investment advice, a trading recommendation, or a production pricing system. Market data may be delayed, incomplete, or revised, and the model relies on simplifying assumptions.
