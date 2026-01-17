from FinMind.data import DataLoader
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from django.utils import timezone

def get_tw_revenue_finmind(ticker):
    """
    從 FinMind 取得台股月營收
    Args:
        ticker (str): 台股代號 (e.g. '2330.TW' or '2330')
    Returns:
        float: 最近一月的營收 (若無則回傳 None)
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        # 抓取最近 6 個月的資料，確保有數據
        start_date = (timezone.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        df = api.taiwan_stock_month_revenue(
            stock_id=stock_id,
            start_date=start_date
        )
        
        if not df.empty:
            # FinMind 回傳的 revenue 單位通常是元
            latest = df.iloc[-1]
            revenue = latest.get('revenue')
            date_str = latest.get('date')
            print(f"[FinMind] {ticker} revenue: {revenue} ({date_str})")
            return revenue
            
    except Exception as e:
        print(f"[FinMind] Error fetching revenue for {ticker}: {e}")
    
    return None

def get_earnings_date_multi_source(ticker, yf_info=None):
    """
    嘗試從多個來源取得下次財報日，並選擇最新的未來日期
    """
    candidates = []
    today = timezone.now()

    # 1. yfinance Calendar
    try:
        yf_ticker = yf.Ticker(ticker)
        cal = yf_ticker.calendar
        if cal and 'Earnings Date' in cal and cal['Earnings Date']:
            for ed in cal['Earnings Date']:
                if hasattr(ed, 'year'):
                    # 建立 timezone-aware datetime
                    dt = timezone.make_aware(datetime.combine(ed, datetime.min.time()))
                    candidates.append(('yfinance_calendar', dt))
    except Exception as e:
        print(f"Error fetching yfinance calendar for {ticker}: {e}")

    # 2. yfinance Info (earningsTimestamp)
    if yf_info:
        ts = yf_info.get('earningsTimestamp') or yf_info.get('earningsTimestampStart')
        if ts:
            try:
                # 使用 timezone-aware datetime
                dt = timezone.make_aware(datetime.fromtimestamp(ts))
                candidates.append(('yfinance_info', dt))
            except:
                pass

    # Filter for future dates only, unless all are past
    future_candidates = [x for x in candidates if x[1] >= today]
    
    if future_candidates:
        future_candidates.sort(key=lambda x: x[1]) # Closest future date
        source, date = future_candidates[0]
        print(f"[{source}] Found future earnings date for {ticker}: {date}")
        return date
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True) # Latest past date
        source, date = candidates[0]
        print(f"[{source}] Found past earnings date for {ticker}: {date}")
        return date
        
    return None

def get_tw_stock_name(ticker):
    """
    從 FinMind 取得台股中文簡稱
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        df = api.taiwan_stock_info()
        
        if not df.empty:
            row = df[df['stock_id'] == stock_id]
            if not row.empty:
                name = row.iloc[0]['stock_name']
                print(f"[FinMind] Found name for {ticker}: {name}")
                return name
    except Exception as e:
        print(f"[FinMind] Error fetching name for {ticker}: {e}")
    return None
