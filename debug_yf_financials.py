
import yfinance as yf
from datetime import datetime

tickers = ['2330.TW', 'AAPL']

for t in tickers:
    print(f"--- {t} ---")
    try:
        ticker = yf.Ticker(t)
        info = ticker.info
        
        # Revenue
        revenue = info.get('totalRevenue')
        print(f"Total Revenue: {revenue}")

        # Earnings Date
        # Usually checking calendar or info
        # info might have 'earningsTimestamp' or 'earningsTimestampStart'
        earnings_ts = info.get('earningsTimestamp')
        print(f"Earnings Timestamp: {earnings_ts}")
        
        if earnings_ts:
            print(f"Earnings Date: {datetime.fromtimestamp(earnings_ts)}")
        
        # Calendar
        cal = ticker.calendar
        print(f"Calendar: {cal}")

    except Exception as e:
        print(f"Error: {e}")
