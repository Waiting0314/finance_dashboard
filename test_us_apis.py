"""
測試美股額外資料來源 API
- SEC EDGAR (免費、無需 API Key)
- Finnhub (免費層)
- Alpha Vantage (免費層 25次/日)
"""
import requests
import json

HEADERS = {
    'User-Agent': 'finance-dashboard/1.0 (contact@example.com)'
}

def test_sec_edgar_company_facts(ticker="AAPL"):
    """
    SEC EDGAR Company Facts API
    直接從 SEC 取得公司財務數據（XBRL 格式）
    無需 API Key
    """
    # 首先需要取得 CIK (Central Index Key)
    cik_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=10-K&dateb=&owner=include&count=1&output=atom"
    
    # 直接使用已知的 CIK mapping（AAPL = 0000320193）
    cik_map = {
        'AAPL': '0000320193',
        'MSFT': '0000789019',
        'GOOGL': '0001652044',
        'AMZN': '0001018724',
        'TSLA': '0001318605',
    }
    
    cik = cik_map.get(ticker.upper())
    if not cik:
        print(f"[SEC EDGAR] CIK not found for {ticker}")
        return None
    
    # 取得公司財務數據
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    
    print(f"[SEC EDGAR] Fetching company facts for {ticker} (CIK: {cik})")
    print(f"URL: {facts_url}")
    
    try:
        resp = requests.get(facts_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            
            # 顯示可用的財務指標
            facts = data.get('facts', {})
            us_gaap = facts.get('us-gaap', {})
            
            print(f"[SEC EDGAR] Available metrics: {len(us_gaap)} items")
            
            # 顯示一些關鍵指標
            key_metrics = ['Revenues', 'NetIncomeLoss', 'EarningsPerShareBasic', 
                          'Assets', 'Liabilities', 'StockholdersEquity']
            
            for metric in key_metrics:
                if metric in us_gaap:
                    units = us_gaap[metric].get('units', {})
                    for unit_type, values in units.items():
                        if values:
                            latest = values[-1]
                            print(f"  {metric}: {latest.get('val')} ({latest.get('end')})")
                            break
            
            return data
    except Exception as e:
        print(f"[SEC EDGAR] Error: {e}")
    
    return None


def test_finnhub_basic_financials(ticker="AAPL"):
    """
    Finnhub 基本財務指標（需要 API Key，但有免費層）
    """
    # 注意：這需要 API Key，此處僅展示 API 結構
    api_key = "demo"  # 需要替換為真實 API Key
    
    url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={api_key}"
    
    print(f"[Finnhub] API endpoint structure: {url}")
    print("[Finnhub] Note: Requires API key registration at finnhub.io")
    
    # 不實際呼叫，因為需要真實 API Key
    return None


def test_alpha_vantage_overview(ticker="AAPL"):
    """
    Alpha Vantage 公司概況（需要 API Key，免費層 25次/日）
    """
    api_key = "demo"  # 需要替換為真實 API Key
    
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    
    print(f"[Alpha Vantage] Fetching company overview for {ticker}")
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            if 'Symbol' in data:
                key_fields = ['Symbol', 'Name', 'PERatio', 'PEGRatio', 
                             'BookValue', 'DividendYield', 'EPS', 
                             'RevenuePerShareTTM', 'ProfitMargin', 
                             'OperatingMarginTTM', 'ReturnOnAssetsTTM',
                             'ReturnOnEquityTTM', 'Beta']
                
                for field in key_fields:
                    if field in data:
                        print(f"  {field}: {data[field]}")
                
                return data
            else:
                print(f"[Alpha Vantage] Unexpected response: {data}")
    except Exception as e:
        print(f"[Alpha Vantage] Error: {e}")
    
    return None


if __name__ == "__main__":
    print("="*60)
    print("測試 SEC EDGAR API（免費、無需 API Key）")
    print("="*60)
    test_sec_edgar_company_facts("AAPL")
    
    print("\n" + "="*60)
    print("測試 Finnhub API（需要免費 API Key）")
    print("="*60)
    test_finnhub_basic_financials("AAPL")
    
    print("\n" + "="*60)
    print("測試 Alpha Vantage API（demo key，有限制）")
    print("="*60)
    test_alpha_vantage_overview("AAPL")
