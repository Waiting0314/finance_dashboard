from background_task import background
from .models import Stock, StockPrice
import yfinance as yf
import pandas as pd
from datetime import datetime

@background(schedule=0) # Run immediately
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

            # Populate new financial fields
            if info.get('beta') and stock_obj.beta != info.get('beta'):
                 stock_obj.beta = info.get('beta')
                 updated = True

            if info.get('marketCap') and stock_obj.market_cap != info.get('marketCap'):
                 stock_obj.market_cap = info.get('marketCap')
                 updated = True

            if info.get('dividendYield') and stock_obj.dividend_yield != info.get('dividendYield'):
                 stock_obj.dividend_yield = info.get('dividendYield')
                 updated = True
            
            # Profitability
            if info.get('returnOnEquity') and stock_obj.roe != info.get('returnOnEquity'):
                 stock_obj.roe = info.get('returnOnEquity')
                 updated = True
            if info.get('returnOnAssets') and stock_obj.roa != info.get('returnOnAssets'):
                 stock_obj.roa = info.get('returnOnAssets')
                 updated = True
            if info.get('grossMargins') and stock_obj.gross_margin != info.get('grossMargins'):
                 stock_obj.gross_margin = info.get('grossMargins')
                 updated = True
            if info.get('operatingMargins') and stock_obj.operating_margin != info.get('operatingMargins'):
                 stock_obj.operating_margin = info.get('operatingMargins')
                 updated = True
            if info.get('profitMargins') and stock_obj.profit_margin != info.get('profitMargins'):
                 stock_obj.profit_margin = info.get('profitMargins')
                 updated = True

            # Solvency & Structure
            if info.get('debtToEquity') and stock_obj.debt_to_equity != info.get('debtToEquity'):
                 stock_obj.debt_to_equity = info.get('debtToEquity')
                 updated = True
            if info.get('quickRatio') and stock_obj.quick_ratio != info.get('quickRatio'):
                 stock_obj.quick_ratio = info.get('quickRatio')
                 updated = True

            # Valuation
            if info.get('priceToBook') and stock_obj.price_to_book != info.get('priceToBook'):
                 stock_obj.price_to_book = info.get('priceToBook')
                 updated = True

            # Cash Flow
            if info.get('freeCashflow') and stock_obj.free_cash_flow != info.get('freeCashflow'):
                 stock_obj.free_cash_flow = info.get('freeCashflow')
                 updated = True

            # Fallback Calculation for Missing Ratios (e.g. for Financial Sector)
            if len(stock_data) > 0: # Ensure we accessed the ticker successfully
                try:
                    financials = ticker_obj.financials
                    balance_sheet = ticker_obj.balance_sheet
                    
                    if not financials.empty and not balance_sheet.empty:
                        # Get latest data (column 0)
                        latest_date = financials.columns[0]
                        bs_latest_date = balance_sheet.columns[0]
                        
                        # Helper to safely get value
                        def get_val(df, key):
                            try:
                                return df.loc[key].iloc[0]
                            except:
                                return None

                        net_income = get_val(financials, 'Net Income')
                        total_revenue = get_val(financials, 'Total Revenue')
                        total_assets = get_val(balance_sheet, 'Total Assets')
                        stockholders_equity = get_val(balance_sheet, 'Stockholders Equity')
                        total_debt = get_val(balance_sheet, 'Total Debt')

                        # Calculate ROE
                        if not stock_obj.roe and net_income and stockholders_equity:
                            stock_obj.roe = net_income / stockholders_equity
                            updated = True
                        
                        # Calculate ROA
                        if not stock_obj.roa and net_income and total_assets:
                            stock_obj.roa = net_income / total_assets
                            updated = True
                            
                        # Calculate Net Margin
                        if not stock_obj.profit_margin and net_income and total_revenue:
                            stock_obj.profit_margin = net_income / total_revenue
                            updated = True
                            
                        # Calculate Debt/Equity
                        if not stock_obj.debt_to_equity and total_debt and stockholders_equity:
                            stock_obj.debt_to_equity = (total_debt / stockholders_equity) * 100 # usually a percentage-like number like 150
                            updated = True

                except Exception as e:
                    print(f"Error calculating fallback ratios for {ticker}: {e}")

            # Localized Name (TW Stocks)
            if '.TW' in ticker and not stock_obj.short_name:
                try:
                    from .data_sources import get_tw_stock_name
                    cname = get_tw_stock_name(ticker)
                    if cname:
                        stock_obj.short_name = cname
                        updated = True
                except Exception as e:
                    print(f"Error fetching FinMind name: {e}")

            # Financial Data
            # For TW stocks, try FinMind first for Revenue
            if '.TW' in ticker:
                try:
                    from .data_sources import get_tw_revenue_finmind
                    fm_rev = get_tw_revenue_finmind(ticker)
                    if fm_rev:
                        stock_obj.last_revenue = fm_rev
                        updated = True
                except Exception as e:
                    print(f"Error fetching FinMind revenue: {e}")
            
            # Fallback to yfinance revenue if empty
            if not stock_obj.last_revenue and info.get('totalRevenue'):
                stock_obj.last_revenue = info.get('totalRevenue')
                updated = True
            
            # Earnings Date logic - Multi-source
            try:
                from .data_sources import get_earnings_date_multi_source
                earnings_dt = get_earnings_date_multi_source(ticker, info)
                if earnings_dt:
                    stock_obj.next_earnings_date = earnings_dt
                    updated = True
            except Exception as e:
                print(f"Error fetching earnings date: {e}")
                # Fallback to old logic if error
                from django.utils import timezone
                earnings_ts = info.get('earningsTimestamp') or info.get('earningsTimestampStart')
                if earnings_ts:
                    try:
                        stock_obj.next_earnings_date = timezone.make_aware(datetime.fromtimestamp(earnings_ts))
                        updated = True
                    except:
                        pass

            if updated:
                stock_obj.save()
                print(f"Updated metadata for {ticker}")

        except Exception as e:
            print(f"Error fetching metadata for {ticker}: {e}")

        # Iterate over the downloaded data and save it
        latest_row = None
        previous_close = None

        if len(stock_data) >= 1:
             latest_row = stock_data.iloc[-1]
             if len(stock_data) >= 2:
                 previous_close = stock_data.iloc[-2]['Close']

        stock_prices_to_create = []
        for row in stock_data.itertuples():
            if isinstance(row.Index, pd.Timestamp):
                date = row.Index.date()
                stock_prices_to_create.append(StockPrice(
                    stock=stock_obj,
                    date=date,
                    open=float(row.Open),
                    high=float(row.High),
                    low=float(row.Low),
                    close=float(row.Close),
                    volume=int(row.Volume)
                ))

        if stock_prices_to_create:
            StockPrice.objects.bulk_create(
                stock_prices_to_create,
                update_conflicts=True,
                unique_fields=['stock', 'date'],
                update_fields=['open', 'high', 'low', 'close', 'volume']
            )
        
        # Update Real-time stats on Stock model
        # Try to use yfinance info for more up-to-date price/change first
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Use currentPrice or regularMarketPrice
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            previous_close_info = info.get('regularMarketPreviousClose')

            if current_price:
                 stock_obj.last_price = current_price
                 
                 if previous_close_info:
                     change = current_price - previous_close_info
                     if previous_close_info != 0:
                         change_pct = (change / previous_close_info) * 100
                     else:
                         change_pct = 0
                     
                     stock_obj.change = change
                     stock_obj.change_percent = change_pct
            elif latest_row is not None:
                # Fallback to dataframe if info is missing
                current_close = float(latest_row['Close'])
                stock_obj.last_price = current_close
                
                if previous_close is not None:
                    prev_close = float(previous_close)
                    change = current_close - prev_close
                    if prev_close != 0:
                        change_pct = (change / prev_close) * 100
                    else:
                        change_pct = 0
                    
                    stock_obj.change = change
                    stock_obj.change_percent = change_pct

        except Exception as e:
            print(f"Error updating stats from info for {ticker}: {e}")
            # Fallback to dataframe logic if info fetch fails completely
            if latest_row is not None:
                current_close = float(latest_row['Close'])
                stock_obj.last_price = current_close
                
                if previous_close is not None:
                    prev_close = float(previous_close)
                    change = current_close - prev_close
                    if prev_close != 0:
                        change_pct = (change / prev_close) * 100
                    else:
                        change_pct = 0
                    
                    stock_obj.change = change
                    stock_obj.change_percent = change_pct
            
        # Check for name update if still default or empty
        if not stock_obj.name:
             try:
                 ticker_obj = yf.Ticker(ticker)
                 info = ticker_obj.info
                 stock_obj.name = info.get('longName') or info.get('shortName') or ticker
             except:
                 pass
        
        stock_obj.save()
        print(f"Updated price stats for {ticker}: {stock_obj.last_price} ({stock_obj.change_percent}%)")

        print(f"Successfully updated data for {ticker}")

    except Exception as e:
        print(f"An error occurred while fetching data for {ticker}: {e}")