from background_task import background
from .models import Stock, StockPrice
import yfinance as yf
import pandas as pd

@background(schedule=60) # Schedule to run 60 seconds after being called
def fetch_stock_data(ticker):
    """
    Fetches historical stock data from yfinance and saves it to the database.
    """
    print(f"Fetching data for {ticker}...")
    try:
        stock_obj, created = Stock.objects.get_or_create(ticker=ticker)
        if created:
            print(f"Created new stock entry for {ticker}")

        # Download historical data
        stock_data = yf.download(ticker, period="5y", progress=False)

        if stock_data.empty:
            print(f"No data found for {ticker}. It might be delisted or an invalid ticker.")
            return

        # Handle MultiIndex columns (common in newer yfinance versions)
        # Structure is usually (Price, Ticker) e.g. ('Open', 'AAPL')
        if isinstance(stock_data.columns, pd.MultiIndex):
            if stock_data.columns.nlevels == 2:
                # Drop the Ticker level to flatten to ('Open', 'High', etc.)
                stock_data.columns = stock_data.columns.droplevel(1)

        # Iterate over the downloaded data and save it
        for index, row in stock_data.iterrows():
            if isinstance(index, pd.Timestamp):
                date = index.date()
                StockPrice.objects.update_or_create(
                    stock=stock_obj,
                    date=date,
                    defaults={
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'close': float(row['Close']),
                        'volume': int(row['Volume'])
                    }
                )
        print(f"Successfully updated data for {ticker}")

    except Exception as e:
        print(f"An error occurred while fetching data for {ticker}: {e}")