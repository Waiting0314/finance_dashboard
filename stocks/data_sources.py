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


def get_tw_institutional_investors(ticker, days=60):
    """
    從 FinMind 取得台股個股三大法人買賣超資料
    Args:
        ticker (str): 台股代號 (e.g. '2330.TW' or '2330')
        days (int): 抓取天數
    Returns:
        list: [{date, foreign_net, trust_net, dealer_net}, ...] 或空陣列
              數值單位為「股」，前端需自行轉換為「張」(除以1000)
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        start_date = (timezone.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        print(f"[FinMind] Fetching institutional investors for {stock_id} from {start_date}")
        
        df = api.taiwan_stock_institutional_investors(
            stock_id=stock_id,
            start_date=start_date
        )
        
        if df.empty:
            print(f"[FinMind] No institutional investor data for {ticker}")
            return []
        
        # 將資料 pivot 成每日三大法人淨買賣超格式
        result = []
        for date in sorted(df['date'].unique()):
            day_data = df[df['date'] == date]
            entry = {'date': str(date), 'foreign_net': 0, 'trust_net': 0, 'dealer_net': 0}
            
            for _, row in day_data.iterrows():
                name = row['name']
                net = int(row['buy']) - int(row['sell'])
                
                # 外資及陸資
                if 'Foreign' in name:
                    entry['foreign_net'] += net
                # 投信
                elif 'Investment_Trust' in name:
                    entry['trust_net'] += net
                # 自營商（包含自行買賣和避險）
                elif 'Dealer' in name:
                    entry['dealer_net'] += net
            
            result.append(entry)
        
        print(f"[FinMind] Got {len(result)} days of institutional investor data for {ticker}")
        return result
        
    except Exception as e:
        print(f"[FinMind] Error fetching institutional investors for {ticker}: {e}")
        return []


# ============================================================
# 台股多來源資料擷取
# ============================================================

def get_tw_per_pbr_finmind(ticker, days=365):
    """
    從 FinMind 取得台股 PE/PB/殖利率
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        start_date = (timezone.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = api.taiwan_stock_per_pbr(
            stock_id=stock_id,
            start_date=start_date
        )
        
        if not df.empty:
            result = []
            for _, row in df.iterrows():
                result.append({
                    'date': str(row['date']),
                    'pe': float(row['PER']) if pd.notna(row['PER']) else None,
                    'pb': float(row['PBR']) if pd.notna(row['PBR']) else None,
                    'dividend_yield': float(row['dividend_yield']) if pd.notna(row['dividend_yield']) else None,
                    'source': 'finmind'
                })
            print(f"[FinMind] Got {len(result)} PE/PB records for {ticker}")
            return result
    except Exception as e:
        print(f"[FinMind] Error fetching PE/PB for {ticker}: {e}")
    return []


def get_tw_per_pbr_twse(ticker):
    """
    從 TWSE 證交所取得台股 PE/PB/殖利率（備援來源）
    """
    import requests
    
    try:
        stock_id = ticker.replace('.TW', '')
        url = f"https://www.twse.com.tw/exchangeReport/BWIBBU?response=json&stockNo={stock_id}"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('stat') == 'OK' and data.get('data'):
            result = []
            for row in data['data']:
                # 日期格式轉換（民國年）
                date_str = row[0]  # 例如 "115年01月27日"
                try:
                    parts = date_str.replace('年', '-').replace('月', '-').replace('日', '').split('-')
                    year = int(parts[0]) + 1911
                    month = int(parts[1])
                    day = int(parts[2])
                    date = f"{year}-{month:02d}-{day:02d}"
                except:
                    continue
                
                result.append({
                    'date': date,
                    'dividend_yield': float(row[1]) if row[1] != '--' else None,
                    'pe': float(row[3]) if row[3] != '--' else None,
                    'pb': float(row[4]) if row[4] != '--' else None,
                    'source': 'twse'
                })
            print(f"[TWSE] Got {len(result)} PE/PB records for {ticker}")
            return result
    except Exception as e:
        print(f"[TWSE] Error fetching PE/PB for {ticker}: {e}")
    return []


def get_tw_monthly_revenue_finmind(ticker, months=12):
    """
    從 FinMind 取得台股月營收歷史資料
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        start_date = (timezone.now() - timedelta(days=months*31)).strftime('%Y-%m-%d')
        
        df = api.taiwan_stock_month_revenue(
            stock_id=stock_id,
            start_date=start_date
        )
        
        if not df.empty:
            result = []
            for _, row in df.iterrows():
                result.append({
                    'date': str(row['date']),
                    'year': int(row['revenue_year']),
                    'month': int(row['revenue_month']),
                    'revenue': int(row['revenue']),
                    'source': 'finmind'
                })
            print(f"[FinMind] Got {len(result)} monthly revenue records for {ticker}")
            return result
    except Exception as e:
        print(f"[FinMind] Error fetching monthly revenue for {ticker}: {e}")
    return []


def get_tw_margin_trading_finmind(ticker, days=90):
    """
    從 FinMind 取得台股融資融券資料（領先指標）
    """
    try:
        api = DataLoader()
        stock_id = ticker.replace('.TW', '')
        start_date = (timezone.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = api.taiwan_stock_margin_purchase_short_sale(
            stock_id=stock_id,
            start_date=start_date
        )
        
        if not df.empty:
            result = []
            for _, row in df.iterrows():
                result.append({
                    'date': str(row['date']),
                    'margin_balance': int(row['MarginPurchaseTodayBalance']),
                    'short_balance': int(row['ShortSaleTodayBalance']),
                    'source': 'finmind'
                })
            print(f"[FinMind] Got {len(result)} margin trading records for {ticker}")
            return result
    except Exception as e:
        print(f"[FinMind] Error fetching margin trading for {ticker}: {e}")
    return []


# ============================================================
# 美股多來源資料擷取
# ============================================================

def get_us_key_metrics_yfinance(ticker):
    """
    從 yfinance 取得美股關鍵指標
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        metrics = {
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'roe': info.get('returnOnEquity'),
            'roa': info.get('returnOnAssets'),
            'profit_margin': info.get('profitMargins'),
            'operating_margin': info.get('operatingMargins'),
            'gross_margin': info.get('grossMargins'),
            'debt_to_equity': info.get('debtToEquity'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'free_cash_flow': info.get('freeCashflow'),
            'beta': info.get('beta'),
            'analyst_target': info.get('targetMeanPrice'),
            'recommendation': info.get('recommendationMean'),
            'source': 'yfinance'
        }
        
        print(f"[yfinance] Got key metrics for {ticker}")
        return metrics
    except Exception as e:
        print(f"[yfinance] Error fetching key metrics for {ticker}: {e}")
    return {}


def get_us_financials_sec_edgar(ticker):
    """
    從 SEC EDGAR 取得美股財務數據（備援來源）
    """
    import requests
    
    # CIK 對照表（常見股票）
    cik_map = {
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'GOOGL': '0001652044',
        'GOOG': '0001652044',
        'AMZN': '0001018724',
        'TSLA': '0001318605',
        'META': '0001326801',
        'NVDA': '0001045810',
    }
    
    cik = cik_map.get(ticker.upper())
    if not cik:
        print(f"[SEC EDGAR] CIK not found for {ticker}")
        return {}
    
    try:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        headers = {'User-Agent': 'finance-dashboard/1.0 (contact@example.com)'}
        
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            facts = data.get('facts', {}).get('us-gaap', {})
            
            def get_latest_value(metric_name):
                if metric_name in facts:
                    units = facts[metric_name].get('units', {})
                    for unit_type, values in units.items():
                        if values:
                            return values[-1].get('val')
                return None
            
            metrics = {
                'revenue': get_latest_value('Revenues') or get_latest_value('RevenueFromContractWithCustomerExcludingAssessedTax'),
                'net_income': get_latest_value('NetIncomeLoss'),
                'eps': get_latest_value('EarningsPerShareBasic'),
                'assets': get_latest_value('Assets'),
                'liabilities': get_latest_value('Liabilities'),
                'stockholders_equity': get_latest_value('StockholdersEquity'),
                'source': 'sec_edgar'
            }
            
            print(f"[SEC EDGAR] Got financial data for {ticker}")
            return metrics
    except Exception as e:
        print(f"[SEC EDGAR] Error fetching data for {ticker}: {e}")
    return {}


def get_us_metrics_alpha_vantage(ticker):
    """
    從 Alpha Vantage 取得美股關鍵指標（第三來源）
    """
    import requests
    import os
    
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', '')
    if not api_key:
        print("[Alpha Vantage] API key not configured")
        return {}
    
    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if 'Symbol' in data:
            metrics = {
                'pe_ratio': float(data.get('PERatio', 0)) or None,
                'peg_ratio': float(data.get('PEGRatio', 0)) or None,
                'price_to_book': float(data.get('BookValue', 0)) or None,
                'roe': float(data.get('ReturnOnEquityTTM', 0)) or None,
                'roa': float(data.get('ReturnOnAssetsTTM', 0)) or None,
                'profit_margin': float(data.get('ProfitMargin', 0)) or None,
                'operating_margin': float(data.get('OperatingMarginTTM', 0)) or None,
                'gross_margin': float(data.get('GrossProfitTTM', 0)) or None,
                'eps': float(data.get('EPS', 0)) or None,
                'beta': float(data.get('Beta', 0)) or None,
                'analyst_target': float(data.get('AnalystTargetPrice', 0)) or None,
                'source': 'alpha_vantage'
            }
            print(f"[Alpha Vantage] Got metrics for {ticker}")
            return metrics
    except Exception as e:
        print(f"[Alpha Vantage] Error fetching data for {ticker}: {e}")
    return {}


# ============================================================
# 多來源驗證邏輯
# ============================================================

def validate_and_merge_metrics(primary_data, backup_data, tolerance=0.05):
    """
    驗證並合併多來源資料
    若兩來源差異超過容忍度則記錄警告
    """
    import logging
    logger = logging.getLogger(__name__)
    
    warnings = []
    merged = {}
    
    for key in set(list(primary_data.keys()) + list(backup_data.keys())):
        if key == 'source':
            continue
            
        primary_val = primary_data.get(key)
        backup_val = backup_data.get(key)
        
        if primary_val is not None and backup_val is not None:
            try:
                p = float(primary_val)
                b = float(backup_val)
                if p != 0 and b != 0:
                    diff = abs(p - b) / max(abs(p), abs(b))
                    if diff > tolerance:
                        warnings.append(f"{key}: 差異 {diff:.2%} (主: {p}, 備: {b})")
            except (TypeError, ValueError):
                pass
        
        # 優先使用主要來源，若無則使用備援
        merged[key] = primary_val if primary_val is not None else backup_val
    
    if warnings:
        logger.warning(f"多來源資料差異警告: {warnings}")
        print(f"[驗證警告] {warnings}")
    
    merged['validation_warnings'] = warnings
    return merged

