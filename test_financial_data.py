
from FinMind.data import DataLoader
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def test_finmind_revenue(stock_id="2330"):
    print(f"--- Testing FinMind Revenue for {stock_id} ---")
    api = DataLoader()
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    try:
        df = api.taiwan_stock_month_revenue(
            stock_id=stock_id,
            start_date=start_date
        )
        if not df.empty:
            print(df.tail())
            print("Columns:", df.columns)
        else:
            print("No revenue data found.")
    except Exception as e:
        print(f"Error: {e}")

def test_finmind_financials(stock_id="2330"):
    print(f"--- Testing FinMind Financial Statements for {stock_id} ---")
    api = DataLoader()
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
    try:
        # Check if financial statement API exists and works
        # Common endpoint for FinMind is taiwan_stock_financial_statement
        df = api.taiwan_stock_financial_statement(
            stock_id=stock_id,
            start_date=start_date
        )
        if not df.empty:
            print(df.tail())
            print("Columns:", df.columns)
            # Filter for Income Statement related terms if possible
            # Income Statement usually includes "Revenue", "Gross Profit", "Operating Income", "Net Income"
            # In Taiwan reports, look for "營業收入", "營業利益", "本期淨利" etc.
            unique_types = df['type'].unique() if 'type' in df.columns else []
            print("Types found:", unique_types[:10])
        else:
            print("No financial statement data found.")
    except Exception as e:
        print(f"Error: {e}")

def test_yfinance_financials(ticker="AAPL"):
    print(f"--- Testing yfinance Financials for {ticker} ---")
    try:
        stock = yf.Ticker(ticker)
        print("Income Statement (Annual):")
        print(stock.financials.head())
        print("Income Statement (Quarterly):")
        print(stock.quarterly_financials.head())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_finmind_revenue()
    test_finmind_financials()
    test_yfinance_financials()
