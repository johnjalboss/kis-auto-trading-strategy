import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import sqlite3, pandas as pd, yfinance as yf
from datetime import datetime, date, timedelta
from chart_generator import _fetch_qqq_dollar_returns

# Test 90 days, 30 days, and all time
for d_val in [30, 90, 0]:
    print(f"\n=================== TESTING DAYS = {d_val} ===================")
    conn = sqlite3.connect("trades.db")
    cur = conn.cursor()
    cur.execute("SELECT MIN(date(exit_time, '-14 hours')) as min_date, MAX(date(exit_time, '-14 hours')) as max_date FROM trades WHERE side = 'SELL'")
    row = cur.fetchone()
    conn.close()
    
    if d_val <= 0:
        start_date = datetime.strptime(row[0], '%Y-%m-%d').date() if row[0] else date.today() - timedelta(days=90)
        end_date = date.today()
    else:
        end_date = date.today()
        start_date = end_date - timedelta(days=d_val - 1)
        
    print(f"Start date: {start_date}, End date: {end_date}")
    q_map = _fetch_qqq_dollar_returns(start_date, end_date, 1000.0)
    print("First 5 entries in QQQ dollar returns map:")
    for k in list(q_map.keys())[:5]:
        print(f"  {k}: ${q_map[k]:.2f}")
    print("Last 3 entries:")
    for k in list(q_map.keys())[-3:]:
        print(f"  {k}: ${q_map[k]:.2f}")
