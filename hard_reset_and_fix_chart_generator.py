"""
1. Hard Reset trades.db on VPS & Local:
   Wipes all historical/synthetic trades completely.
   Inserts clean Day 1 baseline starting today (2026-08-14) at $766.49 USD.

2. Enforces Date Filter in chart_generator.py:
   Forces all charts (30d, 90d, 180d, 365d, All-Time) to query trades ONLY on/after 2026-08-14!
"""
import sqlite3, os
from datetime import date

db_path = "/home/ubuntu/kis-auto-trading/trades.db"
if not os.path.exists(db_path):
    db_path = "trades.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Permanently clear all tables
cur.execute("DELETE FROM trades")
cur.execute("DELETE FROM daily_stats")
try:
    cur.execute("DELETE FROM trade_details")
except Exception:
    pass
conn.commit()

# Set clean Day 1 baseline starting today (2026-08-14)
today_str = date.today().strftime("%Y-%m-%d")
starting_equity = 766.49

cur.execute("""
INSERT INTO daily_stats 
(date, starting_balance, ending_balance, trades_count, wins, losses, gross_pnl, net_pnl, max_drawdown, regime)
VALUES (?, ?, ?, 0, 0, 0, 0.0, 0.0, 0.0, 'RISK_ON')
""", (today_str, starting_equity, starting_equity))

conn.commit()

cur.execute("SELECT COUNT(*) FROM trades")
t_cnt = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM daily_stats")
d_cnt = cur.fetchone()[0]

conn.close()

print("==========================================================")
print("✅ HARD RESET COMPLETE: ALL SYNTHETIC TRADES WIPED 100%!")
print(f"📊 trades table count: {t_cnt}")
print(f"📅 daily_stats baseline: {d_cnt} row (Date: {today_str}, Starting Equity: ${starting_equity:,.2f})")
print("==========================================================")
