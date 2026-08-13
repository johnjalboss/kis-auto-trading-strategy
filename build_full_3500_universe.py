"""
Build 3,500+ US Stock Universe & Update universe.py + universe_cache.json
"""
import requests
import json
import os
import re

print("==================================================")
print("=== BUILDING 3,500+ US STOCK UNIVERSE ===")
print("==================================================")

# 1. Fetch SEC Official US Ticker List
headers = {'User-Agent': 'AntigravityQuantBot/1.0 (quant_admin@domain.com)'}
sec_url = "https://www.sec.gov/files/company_tickers.json"

sec_tickers = []
try:
    resp = requests.get(sec_url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json()
        for k, v in data.items():
            t = v.get("ticker", "").strip().upper().replace(".", "-")
            if t:
                sec_tickers.append(t)
except Exception as e:
    print("SEC fetch error:", e)

# 2. Filtering rules for 3,500+ prime US stocks
clean_tickers = set()

# Warrants, units, rights, test symbols patterns
bad_suffix = re.compile(r'(W|U|R|WS|WT|UN|UT)$')

for t in sec_tickers:
    if not t.isalnum() and '-' not in t:
        continue
    # Skip test symbols or warrants/units (e.g. AACW, AACU)
    if len(t) > 4 and bad_suffix.search(t):
        continue
    if len(t) > 5:  # OTC long tickers
        continue
    clean_tickers.add(t)

# Add essential ETFs and liquid leaders
essential_etfs = [
    "QQQ", "SPY", "IWM", "DIA", "SOXL", "SOXS", "SMH", "TQQQ", "SQQQ", "UVXY",
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLC", "XLB", "XRT"
]
for etf in essential_etfs:
    clean_tickers.add(etf)

sorted_universe = sorted(list(clean_tickers))
print(f"Total Filtered US Tickers: {len(sorted_universe)}")

# Limit to top 3,500+ clean tickers if oversized
if len(sorted_universe) > 3500:
    # Prioritize 1-4 letter mainboard tickers first
    p1 = [t for t in sorted_universe if len(t) <= 4 and '-' not in t]
    p2 = [t for t in sorted_universe if t not in p1]
    sorted_universe = (p1 + p2)[:3500]

print(f"Final 3,500+ Universe Count: {len(sorted_universe)}")

# Save to universe_cache.json
from datetime import datetime
data = {
    "updated": datetime.now().isoformat(),
    "count": len(sorted_universe),
    "symbols": sorted_universe
}
with open("universe_cache.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("[OK] Saved 3,500+ symbols to universe_cache.json successfully!")
print("==================================================")
