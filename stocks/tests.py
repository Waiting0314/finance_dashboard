from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, date
import pandas as pd
import numpy as np
from .models import Stock, StockPrice
from .tasks import fetch_stock_data_sync

class StockTasksTest(TestCase):
    def setUp(self):
        self.ticker = "TEST.TW"

    @patch('yfinance.download')
    @patch('yfinance.Ticker')
    def test_fetch_stock_data_creates_records(self, mock_ticker, mock_download):
        # Mock Ticker info
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {
            'longName': 'Test Company',
            'currentPrice': 100,
            'regularMarketPreviousClose': 90
        }
        mock_ticker_instance.financials = pd.DataFrame()
        mock_ticker_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance

        # Mock DataFrame
        dates = [date(2023, 1, 1), date(2023, 1, 2)]
        data = {
            'Open': [100.0, 102.0],
            'High': [105.0, 106.0],
            'Low': [99.0, 101.0],
            'Close': [101.0, 105.0],
            'Volume': [1000, 2000]
        }
        df = pd.DataFrame(data, index=pd.to_datetime(dates))
        mock_download.return_value = df

        # Run task
        fetch_stock_data_sync(self.ticker)

        # Verify Stock created
        stock = Stock.objects.get(ticker=self.ticker)
        self.assertEqual(stock.name, 'Test Company')

        # Verify StockPrice created
        prices = StockPrice.objects.filter(stock=stock).order_by('date')
        self.assertEqual(prices.count(), 2)
        self.assertEqual(prices[0].date, date(2023, 1, 1))
        self.assertEqual(prices[0].close, 101.0)
        self.assertEqual(prices[1].date, date(2023, 1, 2))
        self.assertEqual(prices[1].close, 105.0)

    @patch('yfinance.download')
    @patch('yfinance.Ticker')
    def test_fetch_stock_data_updates_existing(self, mock_ticker, mock_download):
        # Mock Ticker info
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {}
        mock_ticker_instance.financials = pd.DataFrame()
        mock_ticker_instance.balance_sheet = pd.DataFrame()
        mock_ticker.return_value = mock_ticker_instance

        # Create initial data
        stock = Stock.objects.create(ticker=self.ticker, name="Old Name")
        StockPrice.objects.create(
            stock=stock,
            date=date(2023, 1, 1),
            open=100, high=100, low=100, close=100, volume=100
        )

        # Mock DataFrame with updated data for same date
        dates = [date(2023, 1, 1)]
        data = {
            'Open': [200.0],
            'High': [200.0],
            'Low': [200.0],
            'Close': [200.0],
            'Volume': [200]
        }
        df = pd.DataFrame(data, index=pd.to_datetime(dates))
        mock_download.return_value = df

        # Run task
        fetch_stock_data_sync(self.ticker)

        # Verify update
        price = StockPrice.objects.get(stock=stock, date=date(2023, 1, 1))
        self.assertEqual(price.close, 200.0)
        self.assertEqual(price.volume, 200)
