from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from .models import Stock, Watchlist
import random
from datetime import date, timedelta
import json

def get_chart_data(ticker):
    """
    Generates deterministic dummy stock data for the given ticker.
    Caches the result for 24 hours.
    """
    # Create a unique cache key based on the ticker and today's date
    cache_key = f'chart_data_{ticker}_{date.today()}'

    # Try to get data from cache
    data = cache.get(cache_key)
    if data:
        return data

    # If not in cache, generate data deterministically
    # Use ticker as seed for reproducibility
    # Using hash(ticker) is okay, but for more stability across restarts/python versions,
    # we could use something more stable, but for this simple fake data, hash or just string seed is fine.
    # Python's random.seed() handles strings.
    rng = random.Random(f"{ticker}_{date.today()}")

    prices = []
    current_price = rng.uniform(50, 700)

    for i in range(365):
        current_date = date.today() - timedelta(days=i)
        open_price = round(current_price, 2)
        high_price = round(open_price * rng.uniform(1.0, 1.05), 2)
        low_price = round(open_price * rng.uniform(0.95, 1.0), 2)
        close_price = round(rng.uniform(low_price, high_price), 2)
        prices.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
        })
        current_price = close_price * rng.uniform(0.98, 1.02)

    # Reverse the list so it's in chronological order for the chart
    data = prices[::-1]

    # Cache the result for 24 hours (86400 seconds)
    cache.set(cache_key, data, 86400)

    return data

@login_required
def dashboard(request):
    if request.method == 'POST':
        ticker = request.POST.get('ticker', '').upper()
        if ticker:
            try:
                stock, created = Stock.objects.get_or_create(ticker=ticker)
                if created:
                    # In a real scenario, you'd trigger the background task here.
                    # fetch_stock_data.delay(ticker)
                    messages.info(request, f'股票 {ticker} 不在我們的資料庫中，已將其加入並排程抓取資料。')

                Watchlist.objects.get_or_create(user=request.user, stock=stock)
                messages.success(request, f'已將 {ticker} 加入您的追蹤清單。')

            except Exception as e:
                messages.error(request, f'加入追蹤清單時發生錯誤: {e}')

        return redirect('dashboard')

    user_watchlist = Watchlist.objects.filter(user=request.user)

    # --- DUMMY DATA GENERATION ---
    stock_data_for_chart = {}
    for item in user_watchlist:
        stock_data_for_chart[item.stock.ticker] = get_chart_data(item.stock.ticker)

    context = {
        'watchlist': user_watchlist,
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
