import os
import django
import json
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_dashboard.settings')
django.setup()

from stocks.models import Stock, StockPrice, Watchlist
from django.contrib.auth import get_user_model
import datetime

def generate_style_verification_html():
    print("Generating Light Theme Verification HTML...")

    # Ensure user and stock
    User = get_user_model()
    user, _ = User.objects.get_or_create(username='light_user', email='light@test.com')
    stock, _ = Stock.objects.get_or_create(
        ticker='LIGHT.CORP',
        defaults={
            'name': 'Light Theme Inc.',
            'market': 'US',
            'description': 'A company dedicated to reducing visual pressure with calm design.',
            'sector': 'Design',
            'pe_ratio': 18.5,
            'eps': 3.12,
            'beta': 0.85,
            'market_cap': 8000000000,
            'dividend_yield': 0.031,
            'roe': 0.20,
            'profit_margin': 0.15,
            'price_to_book': 3.2
        }
    )

    # Create price history
    if not stock.prices.exists():
        today = datetime.date.today()
        for i in range(30):
            d = today - datetime.timedelta(days=30-i)
            StockPrice.objects.create(
                stock=stock, date=d,
                open=150+i, high=155+i, low=148+i, close=153+i, volume=50000
            )

    # Mock Request
    request = RequestFactory().get(f'/stock/{stock.ticker}/')
    request.user = user

    # Mock News
    news_items = [
        {
            'title': 'Light Theme Inc. Reduces Eye Strain for Users',
            'summary': 'New interface update brings pastel colors and clean typography.',
            'link': '#',
            'publisher': 'UXDaily'
        },
        {
            'title': 'Market Recap: Why Light Designs are Trending',
            'summary': 'Users prefer lower contrast interfaces for long-term usage.',
            'link': '#',
            'publisher': 'TechTrends'
        }
    ]

    # View Logic (simplified)
    latest_price = stock.prices.first()
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

    # Mock recent prices (last 5)
    recent_prices = stock.prices.all().order_by('-date')[:5]

    context = {
        'stock': stock,
        'latest_price': latest_price,
        'recent_prices': recent_prices,
        'stock_data_json': json.dumps(prices_list),
        'news_items': news_items
    }

    html = render_to_string('stock_detail.html', context, request=request)

    output_path = 'verify_light_theme.html'
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"Generated {output_path}")

if __name__ == "__main__":
    generate_style_verification_html()
