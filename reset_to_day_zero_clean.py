"""
Reset trades.db to Day Zero (Clean Fresh Start)
- Wipes out all synthetic/historical trades.
- Sets starting balance baseline to real KIS live broker balance ($766.49 USD: $210.68 cash + $555.81 positions).
- Establishes clean Day 1 tracking starting from today (2026-08-14)!
"""
import sqlite3, os
from datetime import datetime, date

db_path = "/home/ubuntu/kis-auto-trading/trades.db"
if not os.path.exists(db_path):
    db_path = "trades.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ensure tables
cur.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    total REAL NOT NULL,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    pnl REAL DEFAULT 0,
    pnl_pct REAL DEFAULT 0,
    reason TEXT,
    regime TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS daily_stats (
    date DATE PRIMARY KEY,
    starting_balance REAL,
    ending_balance REAL,
    trades_count INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    gross_pnl REAL DEFAULT 0,
    net_pnl REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0,
    regime TEXT
)
""")

# Completely wipe old trades & daily stats
cur.execute("DELETE FROM trades")
cur.execute("DELETE FROM daily_stats")

# Initial Day 1 baseline starting today (2026-08-14)
today_str = date.today().strftime("%Y-%m-%d")

# Real KIS Account Baseline Total Equity ($210.68 Buying Power + $555.81 Open Positions = $766.49 USD)
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
print("RESET TO DAY ZERO (FRESH CLEAN START) COMPLETED!")
print(f"📊 trades table row count: {t_cnt} (100% CLEAN ZERO TRADES)")
print(f"📅 daily_stats baseline: {d_cnt} row (Date: {today_str}, Starting Equity: ${starting_equity:,.2f})")
print("==========================================================")
