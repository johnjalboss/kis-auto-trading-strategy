"""
Deep inspection of QQQ price data fetched on VPS
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta

print("==================================================")
print("🔍 INSPECTING YFINANCE QQQ RAW DATA ON VPS")
print("==================================================")

df = yf.download("QQQ", start="2026-02-15", end="2026-08-15", progress=False)
print("DF columns:", df.columns)
print("DF shape:", df.shape)

if not df.empty:
    print("\nFirst 5 rows of df['Close']:")
    print(df['Close'].head(5))
    print("\nLast 5 rows of df['Close']:")
    print(df['Close'].tail(5))
    
    # Check start price and end price
    try:
        p_start = float(df['Close'].iloc[0])
        p_end = float(df['Close'].iloc[-1])
        ret = (p_end - p_start) / p_start * 100.0
        print(f"\nCalculated QQQ return: {p_start:.2f} -> {p_end:.2f} = {ret:+.2f}%")
    except Exception as e:
        print("Error calculating return:", e)
else:
    print("df is EMPTY!")

print("==================================================")
