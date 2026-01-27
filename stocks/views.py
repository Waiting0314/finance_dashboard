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

    # === 分頁數量與排序參數處理 ===
    per_page = request.GET.get('per_page', '10')
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 50]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    sort_by = request.GET.get('sort_by', 'id')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # 定義可排序欄位映射
    sort_field_mapping = {
        'ticker': 'stock__ticker',
        'name': 'stock__name',
        'change_percent': 'stock__change_percent',
        'last_price': 'stock__last_price',
        'id': 'id'
    }
    
    order_field = sort_field_mapping.get(sort_by, 'id')
    if sort_order == 'desc':
        order_field = f'-{order_field}'
    
    user_watchlist_qs = Watchlist.objects.filter(user=request.user).select_related('stock').order_by(order_field)

    # Pagination - 使用動態 per_page
    paginator = Paginator(user_watchlist_qs, per_page)
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
        # 分頁與排序參數
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_order': sort_order,
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

    # 2. News Handling - 從 DB 讀取
    from .models import StockNews
    
    # 取出 50 筆最新新聞
    db_news = StockNews.objects.filter(stock=stock).order_by('-pub_date')[:50]
    
    news_list = []
    if db_news.exists():
        for n in db_news:
            news_list.append({
                'title': n.title,
                'link': n.link,
                'publisher': n.publisher or 'Unknown',
                'date': n.pub_date.strftime('%Y-%m-%d %H:%M'),
                'timestamp': n.pub_date.timestamp(),
                'sentiment': n.sentiment,
                'source': 'DB'
            })
    else:
        # 如果 DB 沒資料，可能是新加入的股票還沒跑完 Task
        # Trigger task async if not running? 
        # (Usually fetch_stock_data triggers on creation, so just wait)
        print(f"No news in DB for {ticker}")
        pass

    # (移除原本的即時抓取與情緒分析代碼)


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

    # 4. 三大法人資料（僅台股）
    institutional_data = None  # None 表示此市場不支援
    if stock.ticker.endswith('.TW'):
        from .data_sources import get_tw_institutional_investors
        institutional_data = get_tw_institutional_investors(stock.ticker, days=60)

    # 5. 財務數據（多來源）
    financial_data = {
        'monthly_revenue': [],
        'per_pbr': [],
        'margin_trading': [],
        'key_metrics': {},
        'data_sources': []
    }
    
    if stock.ticker.endswith('.TW'):
        # 台股財務數據
        from .data_sources import (
            get_tw_monthly_revenue_finmind,
            get_tw_per_pbr_finmind,
            get_tw_per_pbr_twse,
            get_tw_margin_trading_finmind,
            validate_and_merge_metrics
        )
        
        # 月營收
        revenue_data = get_tw_monthly_revenue_finmind(stock.ticker, months=24)
        if revenue_data:
            financial_data['monthly_revenue'] = revenue_data
            financial_data['data_sources'].append('finmind_revenue')
        
        # PE/PB（雙來源驗證）
        per_pbr_finmind = get_tw_per_pbr_finmind(stock.ticker, days=365)
        per_pbr_twse = get_tw_per_pbr_twse(stock.ticker)
        
        # 合併資料（優先使用 FinMind，TWSE 作為補充）
        if per_pbr_finmind:
            financial_data['per_pbr'] = per_pbr_finmind[-90:]  # 最近 90 天
            financial_data['data_sources'].append('finmind_perpbr')
        elif per_pbr_twse:
            financial_data['per_pbr'] = per_pbr_twse
            financial_data['data_sources'].append('twse_perpbr')
        
        # 如果兩個來源都有資料，驗證最新一筆
        if per_pbr_finmind and per_pbr_twse:
            latest_fm = per_pbr_finmind[-1] if per_pbr_finmind else {}
            latest_twse = per_pbr_twse[-1] if per_pbr_twse else {}
            validation = validate_and_merge_metrics(latest_fm, latest_twse)
            if validation.get('validation_warnings'):
                financial_data['validation_warnings'] = validation['validation_warnings']
        
        # 融資融券（領先指標）
        margin_data = get_tw_margin_trading_finmind(stock.ticker, days=90)
        if margin_data:
            financial_data['margin_trading'] = margin_data
            financial_data['data_sources'].append('finmind_margin')
    
    else:
        # 美股財務數據
        from .data_sources import (
            get_us_key_metrics_yfinance,
            get_us_financials_sec_edgar,
            get_us_metrics_alpha_vantage,
            validate_and_merge_metrics
        )
        
        # yfinance 關鍵指標
        yf_metrics = get_us_key_metrics_yfinance(stock.ticker)
        if yf_metrics:
            financial_data['key_metrics'] = yf_metrics
            financial_data['data_sources'].append('yfinance')
        
        # SEC EDGAR 財務數據（備援驗證）
        sec_data = get_us_financials_sec_edgar(stock.ticker)
        if sec_data and sec_data.get('revenue'):
            financial_data['sec_edgar'] = sec_data
            financial_data['data_sources'].append('sec_edgar')
        
        # Alpha Vantage（第三來源）
        av_metrics = get_us_metrics_alpha_vantage(stock.ticker)
        if av_metrics and av_metrics.get('pe_ratio'):
            # 驗證 yfinance vs Alpha Vantage
            if yf_metrics:
                validation = validate_and_merge_metrics(yf_metrics, av_metrics)
                if validation.get('validation_warnings'):
                    financial_data['validation_warnings'] = validation['validation_warnings']
            financial_data['data_sources'].append('alpha_vantage')

    return JsonResponse({
        'intraday_data': intraday_data,
        'historical_data': stock_data_list,
        'news': news_list,
        'description': description_zh,
        'current_price': stock_data_list[-1][2] if stock_data_list else 0,
        'prev_close': stock_data_list[-2][2] if len(stock_data_list) > 1 else 0,
        'institutional_investors': institutional_data,
        'financial_data': financial_data,
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
