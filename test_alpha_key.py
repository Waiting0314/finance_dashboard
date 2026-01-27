"""
測試 Alpha Vantage API Key
"""
import requests

API_KEY = "6M4A5PBIKAZ0P0MM"

def test_overview(ticker="AAPL"):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}"
    
    print(f"[Alpha Vantage] Fetching company overview for {ticker}")
    
    resp = requests.get(url, timeout=10)
    data = resp.json()
    
    if 'Symbol' in data:
        print("✅ API Key 有效！")
        key_fields = ['Symbol', 'Name', 'PERatio', 'PEGRatio', 
                     'BookValue', 'DividendYield', 'EPS', 
                     'RevenuePerShareTTM', 'ProfitMargin', 
                     'OperatingMarginTTM', 'ReturnOnAssetsTTM',
                     'ReturnOnEquityTTM', 'Beta', 'AnalystTargetPrice']
        
        for field in key_fields:
            if field in data:
                print(f"  {field}: {data[field]}")
    else:
        print(f"❌ 錯誤回應: {data}")

if __name__ == "__main__":
    test_overview("AAPL")
