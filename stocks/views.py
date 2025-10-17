from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Stock, Watchlist
import random
from datetime import date, timedelta
import json

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
        # Generate fake price data for the last 365 days
        prices = []
        current_price = random.uniform(50, 700)
        for i in range(365):
            current_date = date.today() - timedelta(days=i)
            open_price = round(current_price, 2)
            high_price = round(open_price * random.uniform(1.0, 1.05), 2)
            low_price = round(open_price * random.uniform(0.95, 1.0), 2)
            close_price = round(random.uniform(low_price, high_price), 2)
            prices.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
            })
            current_price = close_price * random.uniform(0.98, 1.02)

        # Reverse the list so it's in chronological order for the chart
        stock_data_for_chart[item.stock.ticker] = prices[::-1]

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