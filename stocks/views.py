from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Stock, Watchlist, StockPrice
from .tasks import fetch_stock_data
import json

@login_required
def dashboard(request):
    if request.method == 'POST':
        ticker = request.POST.get('ticker', '').upper()
        if ticker:
            try:
                stock, created = Stock.objects.get_or_create(ticker=ticker)
                if created:
                    # Trigger the background task to fetch data
                    fetch_stock_data(ticker)
                    messages.info(request, f'股票 {ticker} 不在我們的資料庫中，已將其加入並排程抓取資料。')

                # Check if we need to refresh data anyway (e.g. if it's old)
                # For MVP, we might rely on periodic tasks or just trigger on add
                if not created and not stock.prices.exists():
                     fetch_stock_data(ticker)

                Watchlist.objects.get_or_create(user=request.user, stock=stock)
                messages.success(request, f'已將 {ticker} 加入您的追蹤清單。')

            except Exception as e:
                messages.error(request, f'加入追蹤清單時發生錯誤: {e}')

        return redirect('dashboard')

    user_watchlist = Watchlist.objects.filter(user=request.user)

    # --- REAL DATA FETCHING ---
    stock_data_for_chart = {}
    for item in user_watchlist:
        # Fetch prices from DB
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