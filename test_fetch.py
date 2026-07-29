import sys, os
sys.path.append('/home/ubuntu/kis-auto-trading')
import kis_data
import pandas as pd

for sym in ['NVDA', 'AAPL', 'SPY']:
    try:
        df = kis_data.download(sym, period='90d')
        if df is None:
            print(f"{sym}: None returned")
        elif df.empty:
            print(f"{sym}: Empty DataFrame")
        else:
            print(f"{sym}: OK, shape={df.shape}, columns={list(df.columns)}")
    except Exception as e:
        print(f"{sym}: Exception: {e}")
