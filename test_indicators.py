
from FinMind.data import DataLoader
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def test_finmind_available_datasets():
    """列出 FinMind 可用的資料集"""
    print("--- FinMind 可用資料集 ---")
    api = DataLoader()
    # 嘗試列出所有可能的 API
    methods = [m for m in dir(api) if m.startswith('taiwan_stock')]
    print("Taiwan Stock related methods:")
    for m in methods:
        print(f"  - {m}")

def test_yfinance_info(ticker="AAPL"):
    """測試 yfinance info 中有哪些指標"""
    print(f"--- yfinance info for {ticker} ---")
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # 常見的領先/落後指標欄位
    interesting_keys = [
        'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook',
        'priceToSalesTrailing12Months', 'enterpriseToRevenue', 'enterpriseToEbitda',
        'profitMargins', 'operatingMargins', 'grossMargins',
        'returnOnAssets', 'returnOnEquity',
        'revenueGrowth', 'earningsGrowth', 'earningsQuarterlyGrowth',
        'debtToEquity', 'currentRatio', 'quickRatio',
        'freeCashflow', 'operatingCashflow',
        'bookValue', 'beta', 'recommendationMean', 'targetMeanPrice',
    ]
    
    print("Available indicators:")
    for key in interesting_keys:
        val = info.get(key)
        if val is not None:
            print(f"  {key}: {val}")

def test_finmind_per_pbr(stock_id="2330"):
    """測試 FinMind PE/PB 比率"""
    print(f"--- FinMind PE/PB for {stock_id} ---")
    api = DataLoader()
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    try:
        df = api.taiwan_stock_per_pbr(
            stock_id=stock_id,
            start_date=start_date
        )
        if not df.empty:
            print(df.tail())
            print("Columns:", df.columns.tolist())
    except Exception as e:
        print(f"Error: {e}")

def test_finmind_dividend(stock_id="2330"):
    """測試 FinMind 股利資料"""
    print(f"--- FinMind Dividend for {stock_id} ---")
    api = DataLoader()
    start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')
    try:
        df = api.taiwan_stock_dividend(
            stock_id=stock_id,
            start_date=start_date
        )
        if not df.empty:
            print(df.tail())
            print("Columns:", df.columns.tolist())
    except Exception as e:
        print(f"Error: {e}")

def test_finmind_margin_trading(stock_id="2330"):
    """測試 FinMind 融資融券資料（領先指標）"""
    print(f"--- FinMind Margin Trading for {stock_id} ---")
    api = DataLoader()
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    try:
        df = api.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_id,
            start_date=start_date
        )
        if not df.empty:
            print(df.tail())
            print("Columns:", df.columns.tolist())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_finmind_available_datasets()
    print("\n")
    test_yfinance_info()
    print("\n")
    test_finmind_per_pbr()
    print("\n")
    test_finmind_dividend()
    print("\n")
    test_finmind_margin_trading()
