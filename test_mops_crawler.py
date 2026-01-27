"""
測試台灣公開資訊觀測站 (MOPS) 爬蟲
用於驗證多資料來源可行性
"""
import requests
import pandas as pd
from datetime import datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_mops_monthly_revenue(year: int, month: int):
    """
    從公開資訊觀測站爬取上市公司月營收
    https://mops.twse.com.tw/nas/t21/sii/t21sc03_{year}_{month}_0.html
    """
    # 轉換為民國年
    roc_year = year - 1911
    url = f"https://mops.twse.com.tw/nas/t21/sii/t21sc03_{roc_year}_{month}_0.html"
    
    print(f"[MOPS] Fetching monthly revenue from: {url}")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'big5'
        
        if resp.status_code == 200:
            tables = pd.read_html(resp.text, encoding='big5')
            if tables:
                # 通常第一個表格包含營收資料
                df = tables[0]
                print(f"[MOPS] Found {len(tables)} tables, first table shape: {df.shape}")
                print(df.head())
                return df
    except Exception as e:
        print(f"[MOPS] Error: {e}")
    
    return None

def get_mops_financial_statement(stock_id: str, year: int, season: int):
    """
    從公開資訊觀測站爬取個股財報（綜合損益表）
    """
    roc_year = year - 1911
    url = "https://mops.twse.com.tw/mops/web/ajax_t164sb04"
    
    payload = {
        'encodeURIComponent': '1',
        'step': '1',
        'firstin': '1',
        'off': '1',
        'keyword4': '',
        'code1': '',
        'TYPEK2': '',
        'checkbtn': '',
        'queryName': 'co_id',
        'inpuType': 'co_id',
        'TYPEK': 'all',
        'isnew': 'false',
        'co_id': stock_id,
        'year': str(roc_year),
        'season': str(season),
    }
    
    print(f"[MOPS] Fetching financial statement for {stock_id}, {year} Q{season}")
    
    try:
        resp = requests.post(url, data=payload, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        
        if resp.status_code == 200:
            tables = pd.read_html(resp.text)
            if tables:
                print(f"[MOPS] Found {len(tables)} tables")
                for i, t in enumerate(tables[:3]):
                    print(f"Table {i} shape: {t.shape}")
                    print(t.head(3))
                    print("---")
                return tables
    except Exception as e:
        print(f"[MOPS] Error: {e}")
    
    return None

def test_twse_per_pbr(stock_id: str = "2330"):
    """
    從證交所取得個股本益比/股價淨值比資料
    """
    url = f"https://www.twse.com.tw/exchangeReport/BWIBBU?response=json&stockNo={stock_id}"
    
    print(f"[TWSE] Fetching PE/PB for {stock_id}")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        
        if data.get('stat') == 'OK' and data.get('data'):
            df = pd.DataFrame(data['data'], columns=data['fields'])
            print(f"[TWSE] Got {len(df)} records")
            print(df.tail())
            return df
    except Exception as e:
        print(f"[TWSE] Error: {e}")
    
    return None

if __name__ == "__main__":
    print("="*60)
    print("測試 MOPS 月營收爬蟲")
    print("="*60)
    get_mops_monthly_revenue(2025, 12)
    
    print("\n" + "="*60)
    print("測試 MOPS 財報爬蟲")
    print("="*60)
    get_mops_financial_statement("2330", 2025, 3)
    
    print("\n" + "="*60)
    print("測試 TWSE PE/PB 爬蟲")
    print("="*60)
    test_twse_per_pbr("2330")
