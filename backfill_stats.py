import sqlite3, os
from datetime import datetime, date

db_path = os.path.expanduser('~/kis-auto-trading/trades.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all unique trade dates based on exit_time for SELL orders
cur.execute("SELECT DISTINCT date(created_at, '-14 hours') as d FROM trades WHERE side = 'SELL'")
trade_dates = [row['d'] for row in cur.fetchall() if row['d']]

print("Found dates to backfill:", trade_dates)

for d in trade_dates:
    cur.execute('''
        SELECT SUM(pnl) as net_pnl,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses
        FROM trades 
        WHERE date(created_at, '-14 hours') = ? AND side = 'SELL'
    ''', (d,))
    row = cur.fetchone()
    if not row or row['net_pnl'] is None: continue
    
    net_pnl = row['net_pnl']
    wins = row['wins'] or 0
    losses = row['losses'] or 0

    print(f"Date: {d} | PNL: {net_pnl} | W: {wins} | L: {losses}")

    cur.execute('''
        INSERT OR REPLACE INTO daily_stats (date, net_pnl, wins, losses)
        VALUES (?, ?, ?, ?)
    ''', (d, net_pnl, wins, losses))

conn.commit()
print('Backfill complete.')
conn.close()
