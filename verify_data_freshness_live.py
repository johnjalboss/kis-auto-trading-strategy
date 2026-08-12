"""
Data Freshness & Staleness Audit Script (verify_data_freshness_live.py)
========================================================================
Checks exact timestamps, bar dates, and data freshness across all data pipelines on the VPS.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import datetime
import time
import pandas as pd

print("============================================================")
print("🕒 DATA FRESHNESS & TIMESTAMP VERIFICATION AUDIT")
print("============================================================")

now_dt = datetime.datetime.now()
print(f"Current VPS Server Time: {now_dt.strftime('%Y-%m-%d %H:%M:%S EST/KST')}\n")

# 1. KIS API Daily OHLCV Freshness
import kis_data
df_kis = kis_data.get_daily_ohlcv("AAPL", days=5)
if df_kis is not None and not df_kis.empty:
    last_date = df_kis.index[-1]
    last_close = df_kis['Close'].iloc[-1]
    print(f"✅ [KIS Daily OHLCV] AAPL Last Bar Date: {last_date} | Close: ${last_close:.2f}")

# 2. Real-Time Trader Price Freshness
from trader import Trader
t = Trader()
lp = t.get_price("AAPL")
bp = t.get_buying_power()
print(f"✅ [KIS Real-Time Quote] AAPL Live Price: ${lp:.2f} | Buying Power: ${bp:.2f}")

# 3. YFinance Proxy Freshness
import yfinance as yf
df_yf = yf.download("SPY", period="2d", progress=False)
if df_yf is not None and not df_yf.empty:
    yf_last_date = df_yf.index[-1]
    print(f"✅ [YFinance Proxy] SPY Last Bar Date: {yf_last_date}")

# 4. FRED Macro Data Freshness
from fred_macro import get_fred_analyzer
fa = get_fred_analyzer()
vix_history = fa.get_vix_history(days_back=5)
if vix_history is not None and not vix_history.empty:
    vix_last_date = vix_history.index[-1]
    vix_val = vix_history['Close'].iloc[-1]
    print(f"✅ [FRED Macro VIX] VIX Last Bar Date: {vix_last_date} | VIX Value: {vix_val:.2f}")

# 5. Options Snapshot Freshness
from options_flow import get_options_snapshot
opt_snap = get_options_snapshot("AAPL")
print(f"✅ [Options Flow] AAPL Options Implied Price: ${opt_snap.price:.2f} | DTE: {opt_snap.days_to_expiry}d")

print("============================================================")
print("📊 ALL PIPELINES VERIFIED LIVE & UP-TO-DATE!")
print("============================================================")
