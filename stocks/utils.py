import yfinance as yf

def verify_ticker(ticker, market):
    """
    Verifies if a ticker is valid using yfinance.

    Args:
        ticker (str): The stock ticker symbol.
        market (str): 'US' or 'TW'.

    Returns:
        tuple: (is_valid, formatted_ticker, info_dict)
        - is_valid (bool): True if valid.
        - formatted_ticker (str): The ticker formatted for yfinance (e.g. adding .TW).
        - info_dict (dict): Basic info if available, else None.
    """
    formatted_ticker = ticker.upper().strip()

    if market == 'TW':
        if not formatted_ticker.endswith('.TW') and not formatted_ticker.endswith('.TWO'):
             # Try appending .TW first as default
             formatted_ticker += '.TW'

    try:
        stock = yf.Ticker(formatted_ticker)
        # We need to fetch some data to verify it exists.
        # .info is often cached or partial, but fetching history is a sure test.
        # However, .info is better for getting the name.

        # New yfinance versions might handle .info differently.
        # Let's try fetching history for 1 day.
        hist = stock.history(period="1d")

        if hist.empty:
            # Maybe it's delisted or wrong.
            # But sometimes .info works even if history doesn't for some obscure things?
            # No, if history is empty for 1d, it's likely invalid or suspended.
            return False, formatted_ticker, None

        # If we got here, it's valid. Try to get info for name.
        try:
            info = stock.info
        except:
            info = {}

        return True, formatted_ticker, info

    except Exception as e:
        print(f"Error verifying ticker {formatted_ticker}: {e}")
        return False, formatted_ticker, None
