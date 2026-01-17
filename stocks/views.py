from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Stock, Watchlist, StockPrice
from .tasks import fetch_stock_data
from .utils import verify_ticker
import json

@login_required
def dashboard(request):
    if request.method == 'POST':
        raw_ticker = request.POST.get('ticker', '').strip()
        market = request.POST.get('market', 'US')

        if raw_ticker:
            try:
                # 1. Verify before saving
                is_valid, formatted_ticker, info = verify_ticker(raw_ticker, market)

                if not is_valid:
                    messages.error(request, f'找不到股票代號 {raw_ticker} ({market})，請確認輸入是否正確。')
                    return redirect('dashboard')

                # 2. Update or Create Stock with info
                stock, created = Stock.objects.get_or_create(ticker=formatted_ticker)

                # Update basic info if available
                if info:
                    if not stock.name or stock.name == '':
                         stock.name = info.get('longName') or info.get('shortName') or ''
                    stock.market = market
                    
                    # Auto-populate Chinese name for TW stocks
                    if '.TW' in formatted_ticker and not stock.short_name:
                        from .data_sources import get_tw_stock_name
                        cn_name = get_tw_stock_name(formatted_ticker)
                        if cn_name:
                            stock.short_name = cn_name
                    
                    stock.save()

                if created:
                    # Trigger the background task to fetch data
                    fetch_stock_data(formatted_ticker)
                    messages.info(request, f'股票 {formatted_ticker} 已加入並排程抓取資料。')

                # Check if we need to refresh data anyway
                if not created and not stock.prices.exists():
                     fetch_stock_data(formatted_ticker)

                # 3. Add to Watchlist
                Watchlist.objects.get_or_create(user=request.user, stock=stock)
                messages.success(request, f'已將 {formatted_ticker} 加入您的追蹤清單。')

            except Exception as e:
                messages.error(request, f'加入追蹤清單時發生錯誤: {e}')

        return redirect('dashboard')

    user_watchlist_qs = Watchlist.objects.filter(user=request.user).select_related('stock').order_by('-id')

    # Pagination
    paginator = Paginator(user_watchlist_qs, 9) # 9 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- REAL DATA FETCHING for current page ---
    stock_data_for_chart = {}
    loading_stocks = set()  # Track stocks that are still loading
    
    for item in page_obj:
        # Calculate Trading Status
        item.stock.is_trading = is_market_open(item.stock.market)

        # Fetch prices from DB (limit to last 365 days or reasonable amount for sparkline/chart)
        prices_qs = StockPrice.objects.filter(stock=item.stock).order_by('date')

        prices_list = []
        for price in prices_qs:
            prices_list.append({
                'date': price.date.strftime('%Y-%m-%d'),
                'open': float(price.open),
                'high': float(price.high),
                'low': float(price.low),
                'close': float(price.close),
            })

        if prices_list:
             stock_data_for_chart[item.stock.ticker] = prices_list
             
             # Generate Sparkline SVG Path (Server-side)
             # Use last 20 points for trend
             recent_closes = [p['close'] for p in prices_list[-20:]]
             if len(recent_closes) > 1:
                 min_price = min(recent_closes)
                 max_price = max(recent_closes)
                 price_range = max_price - min_price if max_price != min_price else 1
                 
                 # SVG Dimensions: 100x40
                 width = 100
                 height = 40
                 step_x = width / (len(recent_closes) - 1)
                 
                 path_cmds = []
                 for i, price in enumerate(recent_closes):
                     x = i * step_x
                     # Invert Y because SVG 0 is top
                     y = height - ((price - min_price) / price_range * height)
                     # Add spacing margin (5px)
                     y = 5 + (y * 0.8) 
                     
                     cmd = "M" if i == 0 else "L"
                     path_cmds.append(f"{cmd} {x:.1f} {y:.1f}")
                 
                 item.sparkline_svg = " ".join(path_cmds)
             else:
                 item.sparkline_svg = "M 0 20 L 100 20" # Flat line if not enough data
        else:
            # Stock has no price data yet - mark as loading
            loading_stocks.add(item.stock.ticker)
            item.sparkline_svg = "M 0 20 L 100 20"

    context = {
        'watchlist': page_obj, # Pass page_obj as watchlist for iteration
        'stock_data_json': json.dumps(stock_data_for_chart),
        'loading_stocks_json': json.dumps(list(loading_stocks)),
    }
    return render(request, 'dashboard.html', context)

@login_required
def remove_from_watchlist(request, stock_id):
    try:
        stock = Stock.objects.get(id=stock_id)
        Watchlist.objects.filter(user=request.user, stock=stock).delete()
        messages.success(request, f'已將 {stock.ticker} 從您的追蹤清單中移除。')
    except Stock.DoesNotExist:
        messages.error(request, '找不到該股票。')
    except Exception as e:
        messages.error(request, f'移除時發生錯誤: {e}')

    return redirect('dashboard')

@login_required
def refresh_all_stocks(request):
    """
    Manually triggers an update for all stocks in the database.
    Now also ensures they are scheduled for hourly updates.
    """
    if request.method == 'POST' or request.method == 'GET':
        # FIX: Only update stocks in the requesting user's watchlist
        # Check models.py: stock = models.ForeignKey(..., related_name='watchers')
        user_stocks = Stock.objects.filter(watchers__user=request.user).distinct()
        count = user_stocks.count()
        
        for stock in user_stocks:
            # Schedule to run immediately (0) and repeat every hour (3600 seconds)
            fetch_stock_data(stock.ticker, schedule=0, repeat=3600)

        messages.success(request, f'已開始更新您的 {count} 支追蹤股票，並設定為每小時自動更新。')
    
    return redirect('dashboard')

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from deep_translator import GoogleTranslator
from django.http import JsonResponse
import feedparser
import time
import requests

# Helper for Market Open Status
def is_market_open(market):
    now = datetime.now(pytz.utc)
    
    if market == 'US':
        # US: 09:30 - 16:00 ET (UTC-5 or UTC-4)
        tz = pytz.timezone('US/Eastern')
        now_local = now.astimezone(tz)
        if now_local.weekday() >= 5: return False # Weekend
        start = now_local.replace(hour=9, minute=30, second=0, microsecond=0)
        end = now_local.replace(hour=16, minute=0, second=0, microsecond=0)
        return start <= now_local <= end
    elif market == 'TW':
        # TW: 09:00 - 13:30 MST (UTC+8)
        tz = pytz.timezone('Asia/Taipei')
        now_local = now.astimezone(tz)
        if now_local.weekday() >= 5: return False
        start = now_local.replace(hour=9, minute=0, second=0, microsecond=0)
        end = now_local.replace(hour=13, minute=30, second=0, microsecond=0)
        return start <= now_local <= end
    return False

@login_required
def stock_detail(request, ticker):
    stock = get_object_or_404(Stock, ticker=ticker)
    
    # Fast render: Basic DB data
    latest_price = stock.prices.order_by('-date').first()
    recent_prices = stock.prices.order_by('-date')[:5]
    
    # --- Emergency Fix: Clean Dirty DB Description on Load ---
    if stock.description:
        def is_chinese(text):
            return any('\u4e00' <= char <= '\u9fff' for char in text)

        raw_desc = stock.description
        paragraphs = [p.strip() for p in raw_desc.split('\n') if p.strip()]
        
        # Check if we have mixed content (Dirty)
        has_chinese = any(is_chinese(p) for p in paragraphs)
        if has_chinese:
             # Filter out non-Chinese paragraphs to remove the English duplication
             cn_paragraphs = [p for p in paragraphs if is_chinese(p)]
             clean_desc = "\n\n".join(cn_paragraphs)
             
             # If we actually changed something (length reduced), Update DB
             if len(clean_desc) < len(raw_desc):
                  stock.description = clean_desc
                  stock.save()
                  print(f"cleaned description for {stock.ticker}")
    # ---------------------------------------------------------

    context = {
        'stock': stock,
        'latest_price': latest_price, # Restore this
        'recent_prices': recent_prices, # For the table
        'page_title': f"{stock.ticker} - 詳細資訊",
        'is_trading': is_market_open(stock.market)
    }
    return render(request, 'stock_detail.html', context)

@login_required
def stock_detail_api(request, ticker):
    """
    API endpoint to fetch heavy data (Chart, News, Translation) asynchronously.
    """
    stock = get_object_or_404(Stock, ticker=ticker)
    
    # 1. Fetch Data from Yahoo Finance
    yf_ticker = yf.Ticker(stock.ticker)
    
    # Intraday (1d, 5m)
    hist_intraday = yf_ticker.history(period="1d", interval="5m")
    intraday_data = []
    if not hist_intraday.empty:
        # localized timestamps to string
        for index, row in hist_intraday.iterrows():
             close_val = row['Close']
             if pd.isna(close_val): 
                 close_val = None
             
             intraday_data.append([
                 row.name.strftime('%H:%M'),
                 close_val
             ])

    # Historical (5y) - Used for Candle + RSI
    hist_5y = yf_ticker.history(period="5y")
    stock_data_list = []
    if not hist_5y.empty:
        for index, item in hist_5y.iterrows():
            def san(val):
                return None if pd.isna(val) else val

            stock_data_list.append([
                item.name.strftime('%Y-%m-%d'),
                san(item['Open']),
                san(item['Close']),
                san(item['Low']),
                san(item['High']),
                san(item['Volume'])
            ])

    # 2. News Handling
    news_list = []
    translator = GoogleTranslator(source='auto', target='zh-TW')

    # A. Fetch from Yahoo Finance
    try:
        raw_news = yf_ticker.news
        if raw_news:
            for item in raw_news[:3]:
                # Access the actual data payload
                data = item.get('content', item)
                
                title = data.get('title', '')
                if not title: continue
                
                link = data.get('link', data.get('clickThroughUrl', {}).get('url', '#'))
                
                # Check for duplication
                if any(n['link'] == link for n in news_list): continue

                publisher = 'Unknown'
                if 'provider' in data and isinstance(data['provider'], dict):
                     publisher = data['provider'].get('displayName', 'Unknown')
                elif 'publisher' in data:
                     publisher = data['publisher']
                
                pub_time = data.get('providerPublishTime', data.get('pubDate', None))
                
                date_str = ""
                timestamp = 0
                if pub_time:
                    try:
                        if isinstance(pub_time, (int, float)):
                            timestamp = pub_time
                            dt = datetime.fromtimestamp(pub_time)
                        else:
                            dt = pd.to_datetime(pub_time)
                            timestamp = dt.timestamp()
                        date_str = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception as e:
                        pass
                
                # Simple Translate
                try:
                    title_zh = translator.translate(title)
                except:
                    title_zh = title

                news_list.append({
                    'title': title_zh,
                    'link': link,
                    'publisher': publisher,
                    'date': date_str,
                    'timestamp': timestamp,
                    'source': 'Yahoo'
                })
    except Exception as e:
        print(f"Error fetching YF news: {e}")
        
    # B. Fetch from Google News RSS
    try:
        # Simplify query logic
        query_ticker = stock.ticker.replace('.TW', '')
        if stock.market == 'TW':
            query = f"{query_ticker} 股價 新聞"
        else:
            query = f"{query_ticker} stock news technology"
            
        encoded_query = requests.utils.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:5]: 
             if any(n['link'] == entry.link for n in news_list): continue
             
             timestamp = 0
             date_str = ""
             if hasattr(entry, 'published_parsed'):
                 timestamp = time.mktime(entry.published_parsed)
                 dt = datetime.fromtimestamp(timestamp)
                 date_str = dt.strftime('%Y-%m-%d %H:%M')
             
             publisher = entry.source.title if hasattr(entry, 'source') else 'Google News'
             
             news_list.append({
                'title': entry.title,
                'link': entry.link,
                'publisher': publisher,
                'date': date_str,
                'timestamp': timestamp,
                'source': 'GoogleRSS'
             })
             
    except Exception as e:
         print(f"Error fetching RSS: {e}")

    # Sort
    news_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    news_list = news_list[:10]

    # 3. Description Handling (Robust Cleaning)
    description_zh = "暫無描述"
    
    # helper to check if text is chinese
    def is_chinese(text):
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    try:
        # Prefer fresh YF data if available
        raw_desc = None
        try:
            info = yf_ticker.info
            raw_desc = info.get('longBusinessSummary') or info.get('description')
        except:
            pass
        
        if not raw_desc:
            raw_desc = stock.description

        if raw_desc:
             # Strategy: Split by newlines. If we have Chinese paragraphs, use them. 
             # If strictly English, translate.
             
             paragraphs = [p.strip() for p in raw_desc.split('\n') if p.strip()]
             cn_paragraphs = [p for p in paragraphs if is_chinese(p)]
             
             if cn_paragraphs:
                 # We have Chinese parts. Assume these are the translations.
                 # Filter out strictly English parts to avoid duplication.
                 description_zh = "\n\n".join(cn_paragraphs)
             else:
                 # No Chinese found. Needs translation.
                 translator = GoogleTranslator(source='auto', target='zh-TW')
                 limit = 4999
                 if len(raw_desc) > limit:
                      description_zh = translator.translate(raw_desc[:limit])
                 else:
                      description_zh = translator.translate(raw_desc)

    except Exception as e:
        print(f"Error handling description: {e}")
        description_zh = stock.description if stock.description else "暫無描述"

    return JsonResponse({
        'intraday_data': intraday_data,
        'historical_data': stock_data_list,
        'news': news_list,
        'description': description_zh,
        'current_price': stock_data_list[-1][2] if stock_data_list else 0, # Approximate from history if needed
        'prev_close': stock_data_list[-2][2] if len(stock_data_list) > 1 else 0
    })

@login_required
def get_latest_price(request, ticker):
    try:
        stock = Stock.objects.get(ticker=ticker)
        
        # Try to get real-time info from yfinance directly for "Watching" status
        # Note: This might be slow if called frequently.
        # Ideally, use the DB values updated by background task, 
        # BUT user asked for "Real-time" view on detail page.
        # Let's try to fetch live just for this single call.
        yf_ticker = yf.Ticker(stock.ticker)
        info = yf_ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        previous_close = info.get('regularMarketPreviousClose')

        if current_price and previous_close:
             change = current_price - previous_close
             change_pct = (change / previous_close) * 100
             
             # Optionally update DB
             stock.last_price = current_price
             stock.change = change
             stock.change_percent = change_pct
             stock.save()

             return JsonResponse({
                 'price': current_price,
                 'change': round(change, 2),
                 'change_percent': round(change_pct, 2),
                 'timestamp': datetime.now().strftime('%H:%M:%S')
             })
        
        # Fallback to DB
        return JsonResponse({
             'price': stock.last_price,
             'change': stock.change,
             'change_percent': stock.change_percent,
             'timestamp': datetime.now().strftime('%H:%M:%S')
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_loading_status(request):
    """
    API endpoint to check if stocks have finished loading their data.
    Returns which stocks now have price data available.
    """
    import json
    
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            tickers = body.get('tickers', [])
            
            ready = []
            for ticker in tickers:
                try:
                    stock = Stock.objects.get(ticker=ticker)
                    if stock.last_price is not None or stock.prices.exists():
                        ready.append(ticker)
                except Stock.DoesNotExist:
                    pass
            
            return JsonResponse({'ready': ready, 'pending': [t for t in tickers if t not in ready]})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'POST required'}, status=405)
