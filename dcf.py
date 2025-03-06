import yfinance as yf
import pandas as pd
import logging
from datetime import datetime
import numpy as np
import statsmodels.api as sm
import random  
import os 
import time

session_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(1000, 9999))

log_filename = f'log/{session_id}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print(f"Logging to {log_filename}")

# Function to get all tickers tickers
def get_exchange_tickers():
    file_path = 'ranking/dow30_ranking.csv'

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return pd.DataFrame()  
    
    return pd.read_csv(file_path)

exchange_df = get_exchange_tickers()

if 'Symbol' in exchange_df.columns:
    exchange_tickers = exchange_df['Symbol'].tolist()
else:
    print("Error: 'Symbol' column not found in CSV file!")
    exchange_tickers = []

print("Loaded Tickers:", exchange_tickers)

# Create an empty DataFrame to store results
result_df_s = pd.DataFrame(columns=['Ticker', 'WACC', 'Total_Present_Value', 'AAGR', 
                                    'Current_Market_Cap', 'Intrinsic_Value_Per_Share', 
                                    'Current_Stock_Price', 'Undervalue_Overvalue', 'Rank'])

results_list = []

def get_historical_close(ticker):
    end_date = datetime.today().strftime('%Y-%m-%d')
    df = yf.download(
        tickers=ticker,
        start='2000-01-01',
        end=end_date,
        group_by='column'  
    )

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(col).strip() for col in df.columns.values]

    close_col = [c for c in df.columns if c == f"Close_{ticker}"]
    if not close_col:
        print(f"Error: 'Close_{ticker}' not found in columns for {ticker}:", df.columns)
        return pd.Series()

    historical_data = df[close_col[0]].dropna()
    return historical_data

def calculate_avg_growth_rate(ticker_symbol):
    total_growth_rate = 0
    count_tickers = 0

    if isinstance(ticker_symbol, str):
        ticker_symbol = [ticker_symbol]

    for ticker in ticker_symbol:
        try:
            # 1 Get historical close data 
            end_date = datetime.today().strftime('%Y-%m-%d')
            df = yf.download(ticker, start='2000-01-01', end=end_date, group_by='column')
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(col).strip() for col in df.columns.values]

            close_cols = [c for c in df.columns if c.startswith(f"Close_{ticker}")]
            if not close_cols:
                print(f"Skipping {ticker}: No 'Close_{ticker}' column found in {df.columns}")
                continue

            historical_data = df[close_cols[0]].dropna()

            # 2 Check for valid data
            if historical_data.empty:
                print(f"Skipping {ticker}: Data is empty.")
                continue
            elif historical_data.isnull().all():
                print(f"Skipping {ticker}: All values are NaN.")
                continue
            elif len(historical_data.dropna()) < 25:
                print(f"Skipping {ticker}: Less than 25 valid rows.")
                continue

            # 3 Calculate monthly returns
            returns = historical_data.resample('M').ffill().pct_change()
            if returns.dropna().empty:
                print(f"Skipping {ticker}: monthly returns are empty.")
                continue

            # 4 Calculate average growth rate for the past 120 months (10 years)
            avg_growth_rate = returns.tail(120).mean()
            if pd.isna(avg_growth_rate) or avg_growth_rate == 0:
                print(f"Skipping {ticker}: invalid growth rate.")
                continue

            # 5 Add absolute value of growth rate to total
            total_growth_rate += abs(avg_growth_rate)
            count_tickers += 1

        except Exception as e:
            print(f"Failed to fetch data for {ticker}: {e}")
            continue

    # 6 Final average growth rate
    if count_tickers > 0:
        return round(total_growth_rate / count_tickers, 5)
    else:
        return None

def calculate_cost_of_equity(ticker_symbol):
    try:
        ticker_data = yf.Ticker(ticker_symbol)

        stock_prices = yf.download(ticker_symbol, start='2022-01-01', end='2025-01-01', group_by='column')
        if isinstance(stock_prices.columns, pd.MultiIndex):
            stock_prices.columns = ['_'.join(col).strip() for col in stock_prices.columns.values]

        close_cols = [c for c in stock_prices.columns if c.startswith(f"Close_{ticker_symbol}")]
        if not close_cols:
            print(f"Error: No matching 'Close_{ticker_symbol}' column in {stock_prices.columns}")
            return None
        else:
            stock_prices = stock_prices[close_cols[0]].dropna()

        if stock_prices.empty or len(stock_prices.dropna()) < 5:
            print(f"Skipping {ticker_symbol}: Not enough valid data for weekly returns.")
            return None
        stock_returns_weekly = stock_prices.resample('W-Fri').last().pct_change().dropna()

        # Fetch 3-month T-Bill rate
        t_bill_symbol = '^IRX'
        end_date_t = datetime.today().strftime('%Y-%m-%d')
        t_bill_data_1 = yf.download(t_bill_symbol, start='2022-12-01', end=end_date_t, group_by='column')
        if isinstance(t_bill_data_1.columns, pd.MultiIndex):
            t_bill_data_1.columns = ['_'.join(col).strip() for col in t_bill_data_1.columns.values]

        tbill_close_cols = [c for c in t_bill_data_1.columns if c.startswith("Close_^IRX")]
        if not t_bill_data_1.empty and tbill_close_cols:
            t_bill_data = t_bill_data_1[tbill_close_cols[0]].dropna()
            if t_bill_data.empty:
                print(f"No non-empty 'Close_^IRX' data found. Skipping {ticker_symbol}.")
                return None
            last_tbill = float(t_bill_data.iloc[-1])
            logging.info(f"T-Bill Rate:, {last_tbill}")

            risk_free_rate = last_tbill / 100.0
            logging.info(f"Risk Free Rate:, {risk_free_rate}")

            # Calculate beta using regression against a market index
            end_date = datetime.today().strftime('%Y-%m-%d')
            market_index = yf.download('^IXIC', start='2022-01-01', end=end_date, group_by='column')
            if isinstance(market_index.columns, pd.MultiIndex):
                market_index.columns = ['_'.join(col).strip() for col in market_index.columns.values]

            ixic_close_cols = [c for c in market_index.columns if c.startswith("Close_^IXIC")]
            if not ixic_close_cols:
                print(f"Error: 'Close_^IXIC' not found in columns for Nasdaq: {market_index.columns}")
                return None
            else:
                market_index = market_index[ixic_close_cols[0]].dropna()

            if market_index.empty or len(market_index.dropna()) < 5:
                print(f"No data available for Nasdaq in the specified date range. Skipping {ticker_symbol}.")
                return None

            # Weekly returns for market index
            market_index = market_index.resample('W-Fri').last().pct_change().dropna()

            merged_data = pd.concat([stock_returns_weekly, market_index], axis=1).dropna()
            merged_data.columns = ['Stock_Returns', 'Market_Index']

            # Perform linear regression to calculate beta
            X = sm.add_constant(merged_data['Market_Index'])
            y = merged_data['Stock_Returns']

            model = sm.OLS(y, X).fit()
            beta = model.params.get('Market_Index', None)

            if beta is not None:
                # Calculate the cost of equity using the CAPM
                market_return = market_index.mean()
                cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)

                logging.info(f"This is the Cost of Equity {ticker_symbol}: {cost_of_equity:.3%}")
                risk_free_rate_percentage = risk_free_rate * 100
                logging.info(f"Above the risk-free rate ({risk_free_rate_percentage:.3f}%)")

                # cost_of_equity + free-risk rate
                total_cost_of_equity = cost_of_equity + risk_free_rate 
                total_cost_of_equity_percentage = (cost_of_equity + risk_free_rate) * 100
                logging.info(f"This is the Total Cost of Equity required by an investor to hold {ticker_symbol}: {total_cost_of_equity_percentage:.3f}%")

                return total_cost_of_equity

            else:
                print(f"Error: Market_Index not found in model.params for {ticker_symbol}.")
        else:
            print(f"No 'Close_^IRX' data available for T-Bill rate in the specified date range for {ticker_symbol}.")

    except Exception as e:
        print(f"Error processing {ticker_symbol}: {str(e)}")
        return None
    
max_attempts = 3
wait_seconds = 30  

# ----------------------------
# QUERY A SINGLE TICKER
# ----------------------------

while True:
    single_asset = input("\nEnter a ticker symbol to query a single asset (or 'q' to quit): ").strip().upper()
    if single_asset == "Q":
        print("Exiting single ticker queries.")
        break

    attempts = 0
    while attempts < max_attempts:
        print(f"Processing TICKER: {single_asset}")
        try:
            ticker_data = yf.Ticker(single_asset)
            logging.info("Session ID: %s, Ticker: %s, Message: Starting processing TICKER.",
                         session_id, single_asset)

            raw_financials = ticker_data.financials
            if isinstance(raw_financials.columns, pd.MultiIndex):
                raw_financials.columns = ["_".join(col).strip() for col in raw_financials.columns.values]
            financials = raw_financials.T

            # Get cash flow statement
            raw_cfs = ticker_data.cashflow
            if isinstance(raw_cfs.columns, pd.MultiIndex):
                raw_cfs.columns = ["_".join(col).strip() for col in raw_cfs.columns.values]
            cash_flow_statement = raw_cfs.T

            # Get income statement
            raw_income_stmt = ticker_data.income_stmt
            if isinstance(raw_income_stmt.columns, pd.MultiIndex):
                raw_income_stmt.columns = ["_".join(col).strip() for col in raw_income_stmt.columns.values]
            income_statement = raw_income_stmt

            # Get balance sheet
            raw_balance_sheet = ticker_data.balance_sheet
            if isinstance(raw_balance_sheet.columns, pd.MultiIndex):
                raw_balance_sheet.columns = ["_".join(col).strip() for col in raw_balance_sheet.columns.values]
            balance_sheet = raw_balance_sheet

            # Current stock price
            current_stock_price = ticker_data.info.get('ask', float('nan'))
            logging.info("Session ID: %s, This is the Current Stock Price: %s", session_id, current_stock_price)
            current_stock_prices = pd.to_numeric(current_stock_price, errors='coerce')

            # Free Cash Flow Row
            free_cash_flow_row = cash_flow_statement.iloc[0:4, 0].astype(float).tolist()
            logging.info("Session ID: %s, FCF Row:\n%s", session_id, free_cash_flow_row)

            # Market Cap & Debt
            market_cap = ticker_data.info.get('marketCap', float('nan'))
            logging.info("Market Cap: %s", market_cap)
            total_debt = ticker_data.info.get('totalDebt', float('nan'))
            logging.info("Total Debt: %s", total_debt)

            # Revenue Row
            revenue_row = financials.iloc[:, 38]
            logging.info("Session ID: %s, \nRevenue Row: %s", session_id, revenue_row)
            revenue_rows = pd.to_numeric(revenue_row, errors='coerce')

            # Growth Rates
            growth_rates = [
                (revenue_rows.iloc[i] - revenue_rows.iloc[i + 1]) / abs(revenue_rows.iloc[i + 1])
                for i in range(len(revenue_rows) - 1)
            ]
            growth_rates.reverse()
            aagr = sum(growth_rates) / len(growth_rates)
            logging.info("AAGR: %s", aagr)

            # Forecast Cash Flow
            forecasted_cash_flows = [val * (1 + aagr) ** i for i, val in enumerate(free_cash_flow_row, 1)]
            logging.info("Forecasted Cash Flows: %s", forecasted_cash_flows)

            # Tax Rate
            tax_rate_row = income_statement[income_statement.index == "Tax Rate For Calcs"].iloc[:, 0:4]
            tax_rate_values = tax_rate_row.values.flatten().astype(float)
            tax_rate = np.nanmean(tax_rate_values)
            logging.info("Tax Rate: %s", tax_rate)

            # Cost of Equity
            total_cost_of_equity = calculate_cost_of_equity(single_asset)
            logging.info("Cost of Equity: %s", total_cost_of_equity)

            if total_cost_of_equity is None:
                print(f"Unable to compute Cost of Equity for {single_asset}, skipping.")
                break

            # Interest Expense
            interest_expense_row = income_statement[income_statement.index == "Interest Expense"].iloc[:, 0:4]
            total_interests_values = interest_expense_row.values.flatten().astype(float)
            total_interests_average = np.nanmean(total_interests_values)

            # 'Total Debt' Row
            total_debt_row = balance_sheet[balance_sheet.index == "Total Debt"].iloc[:, 0:4]
            total_debt_values = total_debt_row.values.flatten().astype(float)
            total_debt_average = np.nanmean(total_debt_values)

            # Cost of Debt
            cost_of_debt = total_interests_average / total_debt_average
            logging.info("Cost of Debt: %s", cost_of_debt)

            # WACC
            equity_portion = market_cap
            debt_portion = total_debt
            total_value = equity_portion + debt_portion
            wacc = (equity_portion / total_value) * total_cost_of_equity + (debt_portion / total_value) * cost_of_debt * (1 - tax_rate)
            logging.info("WACC: %s", wacc)

            # Discounted Cash Flows
            discounted_cash_flows = [cf / (1 + wacc) ** i for i, cf in enumerate(forecasted_cash_flows, 1)]
            logging.info("Discounted CF: %s", discounted_cash_flows)

            # Terminal Value & Summation
            perpetuity_growth_rate = calculate_avg_growth_rate(single_asset)
            logging.info("Perpetuity Growth Rate: %s", perpetuity_growth_rate)

            terminal_value = forecasted_cash_flows[-1] * (1 + perpetuity_growth_rate) / (wacc - perpetuity_growth_rate)
            discounted_terminal_value = terminal_value / (1 + wacc) ** 5

            total_present_value = sum(discounted_cash_flows) + discounted_terminal_value
            logging.info("Total Present Value: %s", total_present_value)

            # Outstanding Shares
            outstanding_shares = balance_sheet.loc["Ordinary Shares Number"].iloc[0]
            intrinsic_value_per_share = total_present_value / outstanding_shares
            logging.info("Intrinsic Value/Share: %s", intrinsic_value_per_share)

            # Undervalue/Overvalue
            uo_value = intrinsic_value_per_share - current_stock_prices
            logging.info("Undervalue/Overvalue: %s", uo_value)

            print(f"\nTicker: {single_asset} \n"
                  f"WACC: {wacc}, \n"
                  f"Total Present Value: {total_present_value}, \n"
                  f"AAGR: {aagr}, \n"
                  f"Intrinsic Value per Share: {intrinsic_value_per_share}, \n"
                  f"Current Stock Price: {current_stock_price}, \n"
                  f"Undervalue/Overvalue: {uo_value}\n")
            break

        except Exception as e:
            error_str = str(e)
            if "Too Many Requests" in error_str or "Rate limited" in error_str:
                attempts += 1
                print(f"Rate limit error for {single_asset} (Attempt {attempts}/{max_attempts}). Waiting {wait_seconds} seconds...")
                time.sleep(wait_seconds)
            else:
                print(f"Error processing SINGLE TICKER: {single_asset}, Error: {error_str}")
                break
    else:
        print(f"Max attempts reached for {single_asset}, skipping single asset analysis.")
