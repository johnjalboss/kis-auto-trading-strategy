import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime, date, timedelta

conn = sqlite3.connect("trades.db")
cur = conn.cursor()

print("=== DAILY STATS COUNT ===")
cur.execute("SELECT COUNT(*) FROM daily_stats")
print("daily_stats total:", cur.fetchone()[0])

print("\n=== RECENT 15 DAILY STATS ===")
for r in cur.execute("SELECT date, starting_balance, ending_balance, trades_count, wins, losses, gross_pnl, net_pnl FROM daily_stats ORDER BY date DESC LIMIT 15"):
    print(r)

print("\n=== RECENT 15 SELL TRADES ===")
for r in cur.execute("SELECT id, symbol, side, quantity, price, pnl, pnl_pct, date(created_at) FROM trades WHERE side='SELL' ORDER BY id DESC LIMIT 15"):
    print(r)

print("\n=== QQQ PRICE FETCH FOR PAST 30 DAYS ===")
df_qqq = yf.download("QQQ", period="1mo", interval="1d", progress=False)
print(df_qqq.tail(10))
