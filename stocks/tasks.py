from background_task import background
from .models import Stock, StockPrice
import yfinance as yf
import pandas as pd

@background(schedule=60) # Schedule to run 60 seconds after being called
def fetch_stock_data(ticker):
    """
    Background task wrapper for fetching stock data.
    """
    fetch_stock_data_sync(ticker)

def fetch_stock_data_sync(ticker):
    """
    Fetches historical stock data from yfinance and saves it to the database.
    (Synchronous version for testing and easier calling)
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

        # Fetch extended info if missing (Description, Sector, EPS, PE)
        # This might be slow, so we could move it to a separate task or check if it's needed
        try:
            # Re-fetch ticker object
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info

            # Update stock fields if they are empty
            updated = False
            if not stock_obj.description and info.get('longBusinessSummary'):
                stock_obj.description = info.get('longBusinessSummary')
                updated = True
            if not stock_obj.sector and info.get('sector'):
                stock_obj.sector = info.get('sector')
                updated = True
            if not stock_obj.pe_ratio and info.get('trailingPE'):
                stock_obj.pe_ratio = info.get('trailingPE')
                updated = True
            if not stock_obj.eps and info.get('trailingEps'):
                stock_obj.eps = info.get('trailingEps')
                updated = True

            # New Indicators (Always update if available, or check if empty. Let's update if available to keep fresh)
            # Actually for MVP let's just populate if missing or update.
            # beta, market_cap, dividend_yield, roe, profit_margin, price_to_book

            if info.get('beta') and stock_obj.beta != info.get('beta'):
                 stock_obj.beta = info.get('beta')
                 updated = True

            if info.get('marketCap') and stock_obj.market_cap != info.get('marketCap'):
                 stock_obj.market_cap = info.get('marketCap')
                 updated = True

            if info.get('dividendYield') and stock_obj.dividend_yield != info.get('dividendYield'):
                 stock_obj.dividend_yield = info.get('dividendYield')
                 updated = True

            if info.get('returnOnEquity') and stock_obj.roe != info.get('returnOnEquity'):
                 stock_obj.roe = info.get('returnOnEquity')
                 updated = True

            if info.get('profitMargins') and stock_obj.profit_margin != info.get('profitMargins'):
                 stock_obj.profit_margin = info.get('profitMargins')
                 updated = True

            if info.get('priceToBook') and stock_obj.price_to_book != info.get('priceToBook'):
                 stock_obj.price_to_book = info.get('priceToBook')
                 updated = True

            if updated:
                stock_obj.save()
                print(f"Updated metadata for {ticker}")

        except Exception as e:
            print(f"Error fetching metadata for {ticker}: {e}")

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