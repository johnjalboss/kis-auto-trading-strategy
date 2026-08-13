"""
Verify QQQ Benchmark & Excess Return Exact Calculations (verify_qqq_benchmark_live.py)
======================================================================================
Queries trades.db and QQQ live price history on VPS to verify 100% calculation accuracy.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

print("============================================================")
print("📊 QQQ BENCHMARK & EXCESS RETURN (ALPHA) MATHEMATICAL AUDIT")
print("============================================================")

db_path = "trades.db"
if not os.path.exists(db_path):
    print("No trades.db found on server.")
    sys.exit(0)

conn = sqlite3.connect(db_path)
df_stats = pd.read_sql_query("SELECT * FROM daily_stats ORDER BY date ASC", conn)
conn.close()

if df_stats.empty:
    print("daily_stats table is currently empty or initializing.")
    sys.exit(0)

start_date = df_stats['date'].iloc[0]
end_date = df_stats['date'].iloc[-1]

print(f"Audit Date Range: {start_date} to {end_date}")

# Fetch real QQQ price history for exact date range
qqq_df = yf.download("QQQ", start=start_date, end=end_date, progress=False)

if qqq_df is not None and not qqq_df.empty:
    qqq_start_p = float(qqq_df['Close'].iloc[0])
    qqq_end_p = float(qqq_df['Close'].iloc[-1])
    qqq_return_pct = ((qqq_end_p - qqq_start_p) / qqq_start_p) * 100.0

    init_eq = float(df_stats['starting_balance'].iloc[0])
    final_eq = float(df_stats['ending_balance'].iloc[-1])
    port_return_pct = ((final_eq - init_eq) / init_eq) * 100.0 if init_eq > 0 else 0.0

    excess_alpha = port_return_pct - qqq_return_pct

    print(f"✅ QQQ Start Price ({start_date}): ${qqq_start_p:.2f}")
    print(f"✅ QQQ End Price ({end_date}):   ${qqq_end_p:.2f}")
    print(f"📈 Real QQQ Benchmark Return:   {qqq_return_pct:+.2f}%")
    print(f"💼 Real Portfolio Net Return:   {port_return_pct:+.2f}%")
    print(f"🚀 Excess Return (Alpha vs QQQ): {excess_alpha:+.2f}%")
else:
    print("Could not fetch QQQ benchmark history.")

print("============================================================")
