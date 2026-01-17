from django.core.management.base import BaseCommand, CommandError
from stocks.tasks import fetch_stock_data

class Command(BaseCommand):
    help = 'Fetches historical stock data for a given ticker from yfinance.'

    def add_arguments(self, parser):
        parser.add_argument('tickers', nargs='+', type=str, help='The stock tickers to fetch data for (e.g., 2330.TW).')

    def handle(self, *args, **options):
        for ticker in options['tickers']:
            try:
                # Call the background task
                fetch_stock_data(ticker)
                self.stdout.write(self.style.SUCCESS(f'Successfully scheduled data fetch for ticker: "{ticker}"'))
            except Exception as e:
                raise CommandError(f'Error scheduling data fetch for ticker "{ticker}": {e}')