
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from .models import Stock, Watchlist
from django.urls import reverse
from datetime import date
from django.core.cache import cache

User = get_user_model()

class StocksViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.stock = Stock.objects.create(ticker='2330.TW', name='TSMC')
        self.watchlist_item = Watchlist.objects.create(user=self.user, stock=self.stock)
        self.client.login(username='testuser', password='password')
        cache.clear()

    def test_dashboard_view_status_code(self):
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_view_context(self):
        url = reverse('dashboard')
        response = self.client.get(url)
        self.assertIn('watchlist', response.context)
        self.assertIn('stock_data_json', response.context)

        # Verify data is present in JSON
        stock_data = response.context['stock_data_json']
        self.assertIn('2330.TW', stock_data)

    def test_add_to_watchlist(self):
        url = reverse('dashboard')
        response = self.client.post(url, {'ticker': '2317.TW'})
        self.assertEqual(Stock.objects.count(), 2)
        self.assertTrue(Watchlist.objects.filter(user=self.user, stock__ticker='2317.TW').exists())

    def test_remove_from_watchlist(self):
        url = reverse('remove_from_watchlist', args=[self.stock.id])
        response = self.client.get(url)
        self.assertFalse(Watchlist.objects.filter(user=self.user, stock=self.stock).exists())

    def test_caching_behavior(self):
        # Access dashboard first time (Cold cache)
        url = reverse('dashboard')
        self.client.get(url)

        cache_key = f'chart_data_2330.TW_{date.today()}'
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        self.assertEqual(len(cached_data), 365)
