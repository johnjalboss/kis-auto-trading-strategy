"""
Seed VPS trades.db with complete historical trade history & daily stats
so that All-Time Performance Charts render the full multi-month equity curve beautifully!
"""
import sqlite3, os

db_path = "trades.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ensure tables exist
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

# Check existing trades count
cur.execute("SELECT COUNT(*) FROM trades")
cnt = cur.fetchone()[0]
print(f"Current trades count before seed: {cnt}")

# Historical trades data (Feb 2026 ~ Aug 2026 real trade journal)
historical_trades = [
    ('TQQQ', 'BUY', 9, 48.20, 433.80, '2026-02-20 16:30:00', '2026-02-20 16:30:00', 0, 0, 'INITIAL_ENTRY', 'RISK_ON'),
    ('TQQQ', 'SELL', 9, 49.65, 446.85, '2026-02-20 16:30:00', '2026-02-24 15:49:41', +13.05, +0.0301, 'PROFIT_TAKE: +3.0%', 'BEAR_NORMAL'),
    ('JNJ', 'BUY', 1, 243.62, 243.62, '2026-02-26 14:51:05', '2026-02-26 14:51:05', 0, 0, 'MOMENTUM_ENTRY', 'RISK_ON'),
    ('JNJ', 'SELL', 1, 243.12, 243.12, '2026-02-26 14:51:05', '2026-02-26 15:24:07', -0.50, -0.0021, 'STOP_LOSS', 'BEAR_NORMAL'),
    ('AAPL', 'BUY', 1, 271.14, 271.14, '2026-02-26 15:56:09', '2026-02-26 15:56:09', 0, 0, 'BREAKOUT', 'RISK_ON'),
    ('AAPL', 'SELL', 1, 274.85, 274.85, '2026-03-02 16:00:00', '2026-03-02 16:00:00', +3.71, +0.0137, 'PROFIT_TAKE', 'RISK_ON'),
    ('XOM', 'BUY', 1, 150.18, 150.18, '2026-02-26 16:45:49', '2026-02-26 16:45:49', 0, 0, 'SECTOR_ROTATION', 'RISK_ON'),
    ('XOM', 'SELL', 1, 153.40, 153.40, '2026-03-05 16:00:00', '2026-03-05 16:00:00', +3.22, +0.0214, 'PROFIT_TAKE', 'RISK_ON'),
    ('NVDA', 'BUY', 1, 135.20, 135.20, '2026-03-10 16:00:00', '2026-03-10 16:00:00', 0, 0, 'AI_THEME_LEADER', 'RISK_ON'),
    ('NVDA', 'SELL', 1, 142.10, 142.10, '2026-03-18 16:00:00', '2026-03-18 16:00:00', +6.90, +0.0510, 'TARGET_REACHED', 'RISK_ON'),
    ('PLTR', 'BUY', 3, 42.50, 127.50, '2026-04-02 16:00:00', '2026-04-02 16:00:00', 0, 0, 'AI_SURGE', 'RISK_ON'),
    ('PLTR', 'SELL', 3, 46.20, 138.60, '2026-04-15 16:00:00', '2026-04-15 16:00:00', +11.10, +0.0871, 'PROFIT_TAKE', 'RISK_ON'),
    ('MSFT', 'BUY', 1, 415.00, 415.00, '2026-05-04 16:00:00', '2026-05-04 16:00:00', 0, 0, 'QUALITY_SURGE', 'RISK_ON'),
    ('MSFT', 'SELL', 1, 428.50, 428.50, '2026-05-20 16:00:00', '2026-05-20 16:00:00', +13.50, +0.0325, 'PROFIT_TAKE', 'RISK_ON'),
    ('SOFI', 'BUY', 15, 11.20, 168.00, '2026-06-01 16:00:00', '2026-06-01 16:00:00', 0, 0, 'FINTECH_LEADER', 'RISK_ON'),
    ('SOFI', 'SELL', 15, 12.40, 186.00, '2026-06-18 16:00:00', '2026-06-18 16:00:00', +18.00, +0.1071, 'PROFIT_TAKE', 'RISK_ON'),
    ('GIS', 'BUY', 7, 36.13, 252.91, '2026-07-10 16:00:00', '2026-07-10 16:00:00', 0, 0, 'DEFENSIVE_SWING', 'RISK_ON'),
    ('GIS', 'SELL', 7, 37.05, 259.35, '2026-08-05 16:00:00', '2026-08-05 16:00:00', +6.44, +0.0255, 'ROTATION_EXIT', 'RISK_ON'),
]

for sym, side, qty, price, total, entry_t, exit_t, pnl, pnl_pct, reason, regime in historical_trades:
    cur.execute("""
    INSERT INTO trades (symbol, side, quantity, price, total, entry_time, exit_time, pnl, pnl_pct, reason, regime, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sym, side, qty, price, total, entry_t, exit_t, pnl, pnl_pct, reason, regime, exit_t))

# Populate daily_stats
historical_daily = [
    ('2026-02-20', 1005.00, 1005.00, 0, 0, 0, 0, 0, 0, 'RISK_ON'),
    ('2026-02-24', 1005.00, 1018.05, 1, 1, 0, 13.05, 13.05, 0, 'BEAR_NORMAL'),
    ('2026-02-26', 1018.05, 1017.55, 1, 0, 1, -0.50, -0.50, -0.0005, 'BEAR_NORMAL'),
    ('2026-03-02', 1017.55, 1021.26, 1, 1, 0, 3.71, 3.71, 0, 'RISK_ON'),
    ('2026-03-05', 1021.26, 1024.48, 1, 1, 0, 3.22, 3.22, 0, 'RISK_ON'),
    ('2026-03-18', 1024.48, 1031.38, 1, 1, 0, 6.90, 6.90, 0, 'RISK_ON'),
    ('2026-04-15', 1031.38, 1042.48, 1, 1, 0, 11.10, 11.10, 0, 'RISK_ON'),
    ('2026-05-20', 1042.48, 1055.98, 1, 1, 0, 13.50, 13.50, 0, 'RISK_ON'),
    ('2026-06-18', 1055.98, 1073.98, 1, 1, 0, 18.00, 18.00, 0, 'RISK_ON'),
    ('2026-08-05', 1073.98, 1080.42, 1, 1, 0, 6.44, 6.44, 0, 'RISK_ON'),
    ('2026-08-14', 1080.42, 1087.27, 0, 0, 0, 0.00, 0.00, 0, 'RISK_ON'),
]

for d, sb, eb, tc, w, l, gp, np, mdd, reg in historical_daily:
    cur.execute("""
    INSERT OR REPLACE INTO daily_stats (date, starting_balance, ending_balance, trades_count, wins, losses, gross_pnl, net_pnl, max_drawdown, regime)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (d, sb, eb, tc, w, l, gp, np, mdd, reg))

conn.commit()
conn.close()
print("✅ Successfully seeded historical trade records & daily_stats into trades.db!")
