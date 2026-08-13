"""
Fetch 3,500+ US Stocks from SEC EDGAR Official Ticker Registry
"""
import requests, json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
url = "https://www.sec.gov/files/company_tickers.json"

try:
    resp = requests.get(url, headers=headers, timeout=10)
    print("SEC API Status:", resp.status_code)
    if resp.ok:
        data = resp.json()
        tickers = []
        for k, v in data.items():
            t = v.get("ticker", "").strip().upper().replace(".", "-")
            if t and t.isalpha() and len(t) <= 5:  # Clean 1-5 letter US tickers
                tickers.append(t)
        
        tickers = sorted(list(set(tickers)))
        print(f"Total Clean SEC US Tickers: {len(tickers)}")
        print("First 30 tickers:", tickers[:30])
except Exception as e:
    print("SEC query error:", e)
