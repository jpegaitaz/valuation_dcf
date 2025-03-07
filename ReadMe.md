![Build Status](https://github.com/jpegaitaz/valuation_crypto/actions/workflows/codeql.yml/badge.svg)[![Codacy Badge](https://app.codacy.com/project/badge/Grade/31d4d5d3746046599dd47dc8e0a66dff)](https://app.codacy.com/gh/jpegaitaz/valuation_crypto/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

- name: Coveralls GitHub Action
  uses: coverallsapp/github-action@v2.3.6

# DCF Valuation Model

## Overview
The **DCF Valuation Model** is a Python-based implementation for evaluating the intrinsic value of stocks using the **Discounted Cash Flow (DCF) method**. It fetches financial data from **Yahoo Finance (yfinance)** and calculates various financial metrics, including the **Weighted Average Cost of Capital (WACC), Cost of Equity, Terminal Value, and Intrinsic Value per Share**. The model also determines whether a stock is **undervalued or overvalued** based on its computed intrinsic value.

## Features
- **Fetch Stock Data:** Retrieves historical stock prices and financial statements from Yahoo Finance.
- **Market Selection:** Allows users to select assets from different market indexes (Dow30, Nasdaq, S&P500, NYSE).
- **WACC Calculation:** Computes the Weighted Average Cost of Capital, incorporating cost of debt and cost of equity.
- **DCF Calculation:** Forecasts free cash flows and discounts them using WACC.
- **Intrinsic Value Estimation:** Determines the fair value per share.
- **Automated Logging:** Stores logs of each valuation session for future reference.
- **Handles API Rate Limits:** Implements retry logic to prevent failures due to request limits.

## Installation
### Prerequisites
Ensure you have **Python 3.8+** installed. Install the required dependencies:
```sh
pip install yfinance pandas numpy statsmodels
```

## Usage
### Running the Model
To run the valuation model, execute:
```sh
python dcf.py
```

### Selecting a Market
Upon execution, the program prompts the user to select a market:
```
Available Markets: Nasdaq, NYSE, SP500, Dow30
Enter the market name (e.g., Nasdaq):
```

### Querying a Stock
Users can enter a ticker symbol to retrieve its valuation:
```
Enter a ticker symbol to query a single asset (or 'q' to quit): AAPL
```

### Output Example
After processing, the model provides key valuation metrics:
```
Ticker: AAPL
WACC: 8.75%
Total Present Value: $2.3 Trillion
AAGR: 6.2%
Intrinsic Value per Share: $175.50
Current Stock Price: $160.25
Undervalued/Overvalued: +9.5%
```

## API Rate Limits & Handling
- **Automatic Retry on Rate Limits:** If Yahoo Finance restricts requests, the model waits and retries after a delay.
- **Data Integrity Checks:** Ensures sufficient historical data exists before running calculations.

## Future Enhancements
- Implement **Monte Carlo simulations** to improve valuation robustness.
- Integrate **sector & peer comparison** for relative valuation.
- Add **visualizations** for better data representation.

## Contributing
Feel free to fork this repository and contribute improvements via pull requests.

## License
This project is licensed under the **MIT License**.

