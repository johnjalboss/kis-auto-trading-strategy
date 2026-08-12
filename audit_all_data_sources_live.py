"""
Data Source Structural Audit Script (audit_all_data_sources_live.py)
====================================================================
Tests EVERY data pipeline component on the live VPS to verify whether
primary vs backup data sources are functioning accurately without structural failure.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import time
import pandas as pd
from loguru import logger

print("============================================================")
print("🔍 STRUCTURAL DATA SOURCE AUDIT & HEALTH CHECK")
print("============================================================")

results = []

def audit_source(name, test_fn):
    t0 = time.time()
    try:
        res = test_fn()
        elapsed = time.time() - t0
        if res is not None and (not hasattr(res, 'empty') or not res.empty):
            print(f"  ✅ [PRIMARY OK] {name} ({elapsed:.2f}s): {str(res)[:80]}")
            results.append((name, "OK", elapsed))
        else:
            print(f"  ⚠️ [EMPTY DATA] {name} ({elapsed:.2f}s): Returned empty result")
            results.append((name, "EMPTY", elapsed))
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ [STRUCTURAL FAIL] {name} ({elapsed:.2f}s): {e}")
        results.append((name, f"FAIL: {e}", elapsed))

# 1. KIS API Daily OHLCV
import kis_data
audit_source("1. KIS API Daily OHLCV (AAPL)", lambda: kis_data.get_daily_ohlcv("AAPL", days=20))

# 2. KIS Trader Real-Time Price & Buying Power
from trader import Trader
trader = Trader()
audit_source("2. KIS API Buying Power", lambda: f"${trader.get_buying_power():,.2f}")
audit_source("3. KIS API Real-Time Price (AAPL)", lambda: f"${trader.get_price('AAPL'):,.2f}")

# 3. Finnhub API (Insider & News)
from finnhub_client import get_finnhub_client
fc = get_finnhub_client()
audit_source("4. Finnhub Insider Transactions (AAPL)", lambda: fc.get_insider_transactions("AAPL"))
audit_source("5. Finnhub Company News (AAPL)", lambda: fc.get_company_news("AAPL", days_back=2))

# 4. FRED Macro Data (VIX & Yield Spreads)
from fred_macro import get_fred_analyzer
fa = get_fred_analyzer()
audit_source("6. FRED VIX History (VIXCLS)", lambda: fa.get_vix_history(days_back=20))
audit_source("7. FRED Yield Spread (T10Y2Y)", lambda: fa.fetch_series_df("T10Y2Y", limit=20))

# 5. Options Flow Data
from options_flow import get_options_snapshot
audit_source("8. Options Flow Snapshot (AAPL)", lambda: get_options_snapshot("AAPL").price)

# 6. YFinance Data Proxy
import yfinance as yf
audit_source("9. YFinance Proxy Download (SPY)", lambda: yf.download("SPY", period="5d", progress=False))

print("============================================================")
print(f"📊 DATA SOURCE HEALTH SUMMARY: {sum(1 for r in results if r[1]=='OK')}/{len(results)} PIPELINES OK")
print("============================================================")
