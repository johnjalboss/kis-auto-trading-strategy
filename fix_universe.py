"""S&P 500 Wikipedia fetch 진단 + 캐시 강제 갱신"""
import sys
from loguru import logger

# 1) Wikipedia S&P 500 직접 테스트
print("=== 1. Wikipedia S&P500 Fetch Test ===")
try:
    import pandas as pd
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    symbols = df["Symbol"].str.replace(".", "-", regex=False).tolist()
    print(f"SUCCESS: {len(symbols)} symbols fetched from Wikipedia")
    print(f"Sample: {symbols[:10]}")
except Exception as e:
    print(f"FAILED: {e}")

# 2) 현재 캐시 상태
print("\n=== 2. Current Cache State ===")
import os, json
cache = 'universe_cache.json'
if os.path.exists(cache):
    d = json.load(open(cache))
    print(f"Count: {d.get('count',0)}, Updated: {d.get('updated','?')}")
else:
    print("No cache file")

# 3) 강제 갱신
print("\n=== 3. Force Refresh Universe ===")
# 캐시 삭제 후 재로딩
if os.path.exists(cache):
    os.remove(cache)
    print("Cache deleted")

import universe
universe._universe_cache = None  # In-memory 캐시도 초기화
syms = universe.get_all_symbols()
print(f"AFTER REFRESH: {len(syms)} symbols")
print(f"Cache now: {json.load(open(cache)).get('count',0) if os.path.exists(cache) else 'no cache'}")
