from background_task import background
from .models import Stock, StockPrice
import yfinance as yf
import pandas as pd
from datetime import datetime

@background(schedule=0) # Run immediately
def fetch_stock_data(ticker):
    """
    Background task wrapper for fetching stock data.
    """
    fetch_stock_data_sync(ticker)

def fetch_stock_data_sync(ticker):
    """
    Fetches historical stock data from yfinance and saves it to the database.
    (Synchronous version for testing and easier calling)
    """
    print(f"Fetching data for {ticker}...")
    try:
        stock_obj, created = Stock.objects.get_or_create(ticker=ticker)
        if created:
            print(f"Created new stock entry for {ticker}")

        # Download historical data
        stock_data = yf.download(ticker, period="5y", progress=False)

        if stock_data.empty:
            print(f"No data found for {ticker}. It might be delisted or an invalid ticker.")
            return

        # Handle MultiIndex columns (common in newer yfinance versions)
        # Structure is usually (Price, Ticker) e.g. ('Open', 'AAPL')
        if isinstance(stock_data.columns, pd.MultiIndex):
            if stock_data.columns.nlevels == 2:
                # Drop the Ticker level to flatten to ('Open', 'High', etc.)
                stock_data.columns = stock_data.columns.droplevel(1)

        # Fetch extended info if missing (Description, Sector, EPS, PE)
        # This might be slow, so we could move it to a separate task or check if it's needed
        try:
            # Re-fetch ticker object
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # Update stock fields if they are empty
            updated = False
            if not stock_obj.description and info.get('longBusinessSummary'):
                stock_obj.description = info.get('longBusinessSummary')
                updated = True
            if not stock_obj.sector and info.get('sector'):
                stock_obj.sector = info.get('sector')
                updated = True
            if not stock_obj.pe_ratio and info.get('trailingPE'):
                stock_obj.pe_ratio = info.get('trailingPE')
                updated = True
            if not stock_obj.eps and info.get('trailingEps'):
                stock_obj.eps = info.get('trailingEps')
                updated = True

            # New Indicators (Always update if available, or check if empty. Let's update if available to keep fresh)
            # Actually for MVP let's just populate if missing or update.
            # beta, market_cap, dividend_yield, roe, profit_margin, price_to_book

            if info.get('beta') and stock_obj.beta != info.get('beta'):
                 stock_obj.beta = info.get('beta')
                 updated = True

            if info.get('marketCap') and stock_obj.market_cap != info.get('marketCap'):
                 stock_obj.market_cap = info.get('marketCap')
                 updated = True

            if info.get('dividendYield') and stock_obj.dividend_yield != info.get('dividendYield'):
                 stock_obj.dividend_yield = info.get('dividendYield')
                 updated = True

            # Populate new financial fields
            if info.get('beta') and stock_obj.beta != info.get('beta'):
                 stock_obj.beta = info.get('beta')
                 updated = True

            if info.get('marketCap') and stock_obj.market_cap != info.get('marketCap'):
                 stock_obj.market_cap = info.get('marketCap')
                 updated = True

            if info.get('dividendYield') and stock_obj.dividend_yield != info.get('dividendYield'):
                 stock_obj.dividend_yield = info.get('dividendYield')
                 updated = True
            
            # Profitability
            if info.get('returnOnEquity') and stock_obj.roe != info.get('returnOnEquity'):
                 stock_obj.roe = info.get('returnOnEquity')
                 updated = True
            if info.get('returnOnAssets') and stock_obj.roa != info.get('returnOnAssets'):
                 stock_obj.roa = info.get('returnOnAssets')
                 updated = True
            if info.get('grossMargins') and stock_obj.gross_margin != info.get('grossMargins'):
                 stock_obj.gross_margin = info.get('grossMargins')
                 updated = True
            if info.get('operatingMargins') and stock_obj.operating_margin != info.get('operatingMargins'):
                 stock_obj.operating_margin = info.get('operatingMargins')
                 updated = True
            if info.get('profitMargins') and stock_obj.profit_margin != info.get('profitMargins'):
                 stock_obj.profit_margin = info.get('profitMargins')
                 updated = True

            # Solvency & Structure
            if info.get('debtToEquity') and stock_obj.debt_to_equity != info.get('debtToEquity'):
                 stock_obj.debt_to_equity = info.get('debtToEquity')
                 updated = True
            if info.get('quickRatio') and stock_obj.quick_ratio != info.get('quickRatio'):
                 stock_obj.quick_ratio = info.get('quickRatio')
                 updated = True

            # Valuation
            if info.get('priceToBook') and stock_obj.price_to_book != info.get('priceToBook'):
                 stock_obj.price_to_book = info.get('priceToBook')
                 updated = True

            # Cash Flow
            if info.get('freeCashflow') and stock_obj.free_cash_flow != info.get('freeCashflow'):
                 stock_obj.free_cash_flow = info.get('freeCashflow')
                 updated = True

            # Fallback Calculation for Missing Ratios (e.g. for Financial Sector)
            if len(stock_data) > 0: # Ensure we accessed the ticker successfully
                try:
                    financials = ticker_obj.financials
                    balance_sheet = ticker_obj.balance_sheet
                    
                    if not financials.empty and not balance_sheet.empty:
                        # Get latest data (column 0)
                        latest_date = financials.columns[0]
                        bs_latest_date = balance_sheet.columns[0]
                        
                        # Helper to safely get value
                        def get_val(df, key):
                            try:
                                return df.loc[key].iloc[0]
                            except:
                                return None

                        net_income = get_val(financials, 'Net Income')
                        total_revenue = get_val(financials, 'Total Revenue')
                        total_assets = get_val(balance_sheet, 'Total Assets')
                        stockholders_equity = get_val(balance_sheet, 'Stockholders Equity')
                        total_debt = get_val(balance_sheet, 'Total Debt')

                        # Calculate ROE
                        if not stock_obj.roe and net_income and stockholders_equity:
                            stock_obj.roe = net_income / stockholders_equity
                            updated = True
                        
                        # Calculate ROA
                        if not stock_obj.roa and net_income and total_assets:
                            stock_obj.roa = net_income / total_assets
                            updated = True
                            
                        # Calculate Net Margin
                        if not stock_obj.profit_margin and net_income and total_revenue:
                            stock_obj.profit_margin = net_income / total_revenue
                            updated = True
                            
                        # Calculate Debt/Equity
                        if not stock_obj.debt_to_equity and total_debt and stockholders_equity:
                            stock_obj.debt_to_equity = (total_debt / stockholders_equity) * 100 # usually a percentage-like number like 150
                            updated = True

                except Exception as e:
                    print(f"Error calculating fallback ratios for {ticker}: {e}")

            # Localized Name (TW Stocks)
            if '.TW' in ticker and not stock_obj.short_name:
                try:
                    from .data_sources import get_tw_stock_name
                    cname = get_tw_stock_name(ticker)
                    if cname:
                        stock_obj.short_name = cname
                        updated = True
                except Exception as e:
                    print(f"Error fetching FinMind name: {e}")

            # Financial Data
            # For TW stocks, try FinMind first for Revenue
            if '.TW' in ticker:
                try:
                    from .data_sources import get_tw_revenue_finmind
                    fm_rev = get_tw_revenue_finmind(ticker)
                    if fm_rev:
                        stock_obj.last_revenue = fm_rev
                        updated = True
                except Exception as e:
                    print(f"Error fetching FinMind revenue: {e}")
            
            # Fallback to yfinance revenue if empty
            if not stock_obj.last_revenue and info.get('totalRevenue'):
                stock_obj.last_revenue = info.get('totalRevenue')
                updated = True
            
            # Earnings Date logic - Multi-source
            try:
                from .data_sources import get_earnings_date_multi_source
                earnings_dt = get_earnings_date_multi_source(ticker, info)
                if earnings_dt:
                    stock_obj.next_earnings_date = earnings_dt
                    updated = True
            except Exception as e:
                print(f"Error fetching earnings date: {e}")
                # Fallback to old logic if error
                from django.utils import timezone
                earnings_ts = info.get('earningsTimestamp') or info.get('earningsTimestampStart')
                if earnings_ts:
                    try:
                        stock_obj.next_earnings_date = timezone.make_aware(datetime.fromtimestamp(earnings_ts))
                        updated = True
                    except:
                        pass

            if updated:
                stock_obj.save()
                print(f"Updated metadata for {ticker}")

        except Exception as e:
            print(f"Error fetching metadata for {ticker}: {e}")

        # Iterate over the downloaded data and save it
        latest_row = None
        previous_close = None

        if len(stock_data) >= 1:
             latest_row = stock_data.iloc[-1]
             if len(stock_data) >= 2:
                 previous_close = stock_data.iloc[-2]['Close']

        for index, row in stock_data.iterrows():
            if isinstance(index, pd.Timestamp):
                date = index.date()
                StockPrice.objects.update_or_create(
                    stock=stock_obj,
                    date=date,
                    defaults={
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }
                )
        
        # Update Real-time stats on Stock model
        # Try to use yfinance info for more up-to-date price/change first
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Use currentPrice or regularMarketPrice
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close_info = info.get('regularMarketPreviousClose')

            if current_price:
                 stock_obj.last_price = current_price
                 
                 if previous_close_info:
                     change = current_price - previous_close_info
                     if previous_close_info != 0:
                         change_pct = (change / previous_close_info) * 100
                     else:
                         change_pct = 0
                     
                     stock_obj.change = change
                     stock_obj.change_percent = change_pct
            elif latest_row is not None:
                # Fallback to dataframe if info is missing
                current_close = float(latest_row['Close'])
                stock_obj.last_price = current_close
                
                if previous_close is not None:
                    prev_close = float(previous_close)
                    change = current_close - prev_close
                    if prev_close != 0:
                        change_pct = (change / prev_close) * 100
                    else:
                        change_pct = 0
                    
                    stock_obj.change = change
                    stock_obj.change_percent = change_pct

        except Exception as e:
            print(f"Error updating stats from info for {ticker}: {e}")
            # Fallback to dataframe logic if info fetch fails completely
            if latest_row is not None:
                current_close = float(latest_row['Close'])
                stock_obj.last_price = current_close
                
                if previous_close is not None:
                    prev_close = float(previous_close)
                    change = current_close - prev_close
                    if prev_close != 0:
                        change_pct = (change / prev_close) * 100
                    else:
                        change_pct = 0
                    
                    stock_obj.change = change
                    stock_obj.change_percent = change_pct
            
        # Check for name update if still default or empty
        if not stock_obj.name:
             try:
                 ticker_obj = yf.Ticker(ticker)
                 info = ticker_obj.info
                 stock_obj.name = info.get('longName') or info.get('shortName') or ticker
             except:
                 pass
        
        stock_obj.save()
        print(f"Updated price stats for {ticker}: {stock_obj.last_price} ({stock_obj.change_percent}%)")

        print(f"Successfully updated data for {ticker}")
        
        # === 財務警示檢查 ===
        check_financial_alerts(stock_obj)

        # === 新聞抓取與情緒分析 (GPU) ===
        try:
             fetch_news_and_analyze(stock_obj)
        except Exception as e:
             print(f"Error fetching news for {ticker}: {e}")

    except Exception as e:
        print(f"An error occurred while fetching data for {ticker}: {e}")


def check_financial_alerts(stock):
    """
    檢查財務指標是否有異常，並更新 alert_message
    """
    alerts = []
    
    # 1. 負債權益比 > 200% 高槓桿風險
    if stock.debt_to_equity and stock.debt_to_equity > 200:
        alerts.append(f"⚠️ 高財務槓桿：負債權益比達 {stock.debt_to_equity:.1f}%，顯示公司債務壓力較大")
    
    # 2. 速動比率 < 0.5 短期償債能力不足
    if stock.quick_ratio and stock.quick_ratio < 0.5:
        alerts.append(f"⚠️ 流動性風險：速動比率僅 {stock.quick_ratio:.2f}，短期償債能力可能不足")
    
    # 3. ROE 為負值
    if stock.roe and stock.roe < 0:
        roe_pct = stock.roe * 100
        alerts.append(f"⚠️ 獲利警訊：ROE 為 {roe_pct:.2f}%，公司股東權益報酬呈現虧損")
    
    # 4. 自由現金流為負
    if stock.free_cash_flow and stock.free_cash_flow < 0:
        fcf_billions = stock.free_cash_flow / 1_000_000_000
        alerts.append(f"⚠️ 現金流警訊：自由現金流為負 ({fcf_billions:.2f}B)，可能影響股利發放或再投資能力")
    
    # 5. 本益比過高 (> 50)
    if stock.pe_ratio and stock.pe_ratio > 50:
        alerts.append(f"⚠️ 估值偏高：本益比達 {stock.pe_ratio:.1f}，回本年限較長，需確認成長性是否支撐")
    
    # 6. 營業利益率為負
    if stock.operating_margin and stock.operating_margin < 0:
        op_margin_pct = stock.operating_margin * 100
        alerts.append(f"⚠️ 本業虧損：營業利益率為 {op_margin_pct:.2f}%，本業經營處於虧損狀態")
    
    # 7. Beta 過高 (> 2) 波動風險
    if stock.beta and stock.beta > 2:
        alerts.append(f"⚠️ 高波動風險：Beta 值達 {stock.beta:.2f}，股價波動遠大於大盤")
    
    # 更新 alert_message
    if alerts:
        stock.alert_message = "\n".join(alerts)
        print(f"[Alert] {stock.ticker} 有 {len(alerts)} 項財務警示")
    else:
        stock.alert_message = ""
    
    stock.save(update_fields=['alert_message'])

    print(f"[Fetch] {stock.ticker} 資料更新完成")


def fetch_news_and_analyze(stock):
    """
    抓取新聞並進行情緒分析，儲存至 StockNews
    """
    print(f"[News] 開始抓取 {stock.ticker} 新聞...")
    
    import feedparser
    import requests
    import time
    from deep_translator import GoogleTranslator
    from .models import StockNews
    from datetime import timedelta
    import pytz
    
    # 計算 30 天前的時間戳
    thirty_days_ago = datetime.now() - timedelta(days=30)
    thirty_days_ago_ts = thirty_days_ago.timestamp()
    
    news_list = []
    translator = GoogleTranslator(source='auto', target='zh-TW')
    
    # 1. Yahoo Finance News
    try:
        yf_ticker = yf.Ticker(stock.ticker)
        raw_news = yf_ticker.news
        
        if raw_news:
            for item in raw_news[:25]:
                data = item.get('content', item)
                title = data.get('title', '')
                if not title: continue
                
                link = data.get('link', data.get('clickThroughUrl', {}).get('url', '#'))
                
                # Check for duplication within this batch
                if any(n['link'] == link for n in news_list): continue
                
                # Check if already exists in DB
                if StockNews.objects.filter(stock=stock, link=link).exists():
                    continue

                publisher = 'Unknown'
                if 'provider' in data and isinstance(data['provider'], dict):
                     publisher = data['provider'].get('displayName', 'Unknown')
                elif 'publisher' in data:
                     publisher = data['publisher']
                
                pub_time = data.get('providerPublishTime', data.get('pubDate', None))
                
                dt_obj = datetime.now() # Default
                timestamp = 0
                
                if pub_time:
                    try:
                        if isinstance(pub_time, (int, float)):
                            timestamp = pub_time
                            dt_obj = datetime.fromtimestamp(pub_time)
                        else:
                            dt_obj = pd.to_datetime(pub_time)
                            timestamp = dt_obj.timestamp()
                    except:
                        pass
                
                # Filter old news
                if timestamp > 0 and timestamp < thirty_days_ago_ts:
                    continue
                    
                # Store original title for sentiment analysis
                news_list.append({
                    'original_title': title,
                    'link': link,
                    'publisher': publisher,
                    'pub_date': dt_obj,
                    'source': 'Yahoo'
                })
    except Exception as e:
        print(f"[News] Error fetching Yahoo news for {stock.ticker}: {e}")

    # 2. Google RSS News
    try:
        query_ticker = stock.ticker.replace('.TW', '')
        query = ""
        
        if stock.market == 'TW':
            # 台股策略：優先使用中文簡稱，若無則用代號
            # 例如： "永豐金 新聞" 比 "2890 新聞" 準確且豐富
            if stock.short_name:
                query = f"{stock.short_name} 新聞"
            else:
                query = f"{query_ticker} 股價 新聞"
        else:
            # 美股策略：使用公司名稱 (去除 Inc/Corp 等) + Ticker + stock news
            # 去除雜訊
            clean_name = stock.name
            for suffix in [', Inc.', ' Inc.', ', Corp.', ' Corp.', ' Company', ' Ltd.', ' PLC']:
                if suffix in clean_name:
                    clean_name = clean_name.replace(suffix, '')
            
            # 使用 OR 邏輯增加廣度 (如果 Google RSS 支援 OR，通常空格是 AND)
            # 改用較為精確的組合作為 query
            query = f"{clean_name} {query_ticker} stock news"
            
        print(f"[News] Searching Google RSS with query: {query}")
            
        encoded_query = requests.utils.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"

        
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:30]:
             if any(n['link'] == entry.link for n in news_list): continue
             if StockNews.objects.filter(stock=stock, link=entry.link).exists(): continue
             
             timestamp = 0
             dt_obj = datetime.now()
             
             if hasattr(entry, 'published_parsed'):
                 timestamp = time.mktime(entry.published_parsed)
                 dt_obj = datetime.fromtimestamp(timestamp)
             
             if timestamp > 0 and timestamp < thirty_days_ago_ts:
                 continue
             
             publisher = entry.source.title if hasattr(entry, 'source') else 'Google News'
             
             news_list.append({
                'original_title': entry.title,
                'link': entry.link,
                'publisher': publisher,
                'pub_date': dt_obj,
                'source': 'GoogleRSS'
             })
             
    except Exception as e:
        print(f"[News] Error fetching RSS for {stock.ticker}: {e}")

    if not news_list:
        print(f"[News] No new news found for {stock.ticker}")
        return

    # 3. Batch Sentiment Analysis
    try:
        from .sentiment import analyze_batch
        original_titles = [n['original_title'] for n in news_list]
        print(f"[Sentiment] Analyzing {len(original_titles)} news items for {stock.ticker}...")
        sentiments = analyze_batch(original_titles) # This uses GPU if available
    except Exception as e:
        print(f"[Sentiment] Analysis failed: {e}")
        sentiments = ['neutral'] * len(news_list)

    # 4. Save to DB (with Translation)
    count = 0
    for i, item in enumerate(news_list):
        try:
            # Translate title to Traditional Chinese
            try:
                title_zh = translator.translate(item['original_title'])
            except:
                title_zh = item['original_title']
            
            # Make aware datetime
            from django.utils.timezone import make_aware
            try:
                pub_date_aware = make_aware(item['pub_date'])
            except:
                pub_date_aware = item['pub_date']

            StockNews.objects.create(
                stock=stock,
                title=title_zh,
                link=item['link'],
                publisher=item['publisher'],
                pub_date=pub_date_aware,
                sentiment=sentiments[i]
            )
            count += 1
        except Exception as e:
            print(f"[News] Error saving news item: {e}")
            continue
            
    print(f"[News] Saved {count} new news items for {stock.ticker}")