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

    user_watchlist_qs = Watchlist.objects.filter(user=request.user).select_related('stock')

    # Pagination
    paginator = Paginator(user_watchlist_qs, 9) # 9 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- REAL DATA FETCHING for current page ---
    stock_data_for_chart = {}
    for item in page_obj:
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

    context = {
        'watchlist': page_obj, # Pass page_obj as watchlist for iteration
        'stock_data_json': json.dumps(stock_data_for_chart)
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

import yfinance as yf

@login_required
def stock_detail(request, ticker):
    stock = get_object_or_404(Stock, ticker=ticker)

    # Fetch latest price
    latest_price = stock.prices.first() # ordering is -date

    # Historical data for chart
    prices_qs = stock.prices.all().order_by('date')
    prices_list = []
    for price in prices_qs:
        prices_list.append({
            'date': price.date.strftime('%Y-%m-%d'),
            'open': float(price.open),
            'high': float(price.high),
            'low': float(price.low),
            'close': float(price.close),
        })

    # Recent Trading Activity (Last 5 days, reversed for table)
    recent_prices = prices_qs.order_by('-date')[:5]

    # Fetch News Live (MVP)
    news_items = []
    try:
        yf_ticker = yf.Ticker(stock.ticker)
        raw_news = yf_ticker.news
        # Limit to 5 items
        for item in raw_news[:5]:
            # Handle nested 'content' structure or flat structure
            data = item.get('content', item)

            news_items.append({
                'title': data.get('title'),
                'summary': data.get('summary') or data.get('description', ''),
                'link': data.get('clickThroughUrl') or data.get('canonicalUrl') or data.get('link'),
                'publisher': data.get('provider', {}).get('displayName') if isinstance(data.get('provider'), dict) else str(data.get('provider', ''))
            })
    except Exception as e:
        print(f"Error fetching news for {stock.ticker}: {e}")

    context = {
        'stock': stock,
        'latest_price': latest_price,
        'recent_prices': recent_prices,
        'stock_data_json': json.dumps(prices_list),
        'news_items': news_items
    }
    return render(request, 'stock_detail.html', context)
