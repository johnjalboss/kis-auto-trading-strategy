import sqlite3
import os

os.chdir("/home/ubuntu/kis-auto-trading")
conn = sqlite3.connect("trades.db")
c = conn.cursor()

# CDNS 전체 내역
c.execute("SELECT id, symbol, side, quantity, price, total, entry_time, exit_time, pnl, reason, created_at FROM trades WHERE symbol='CDNS' ORDER BY created_at")
cols = [d[0] for d in c.description]
rows = c.fetchall()
print("=== CDNS 전체 거래 내역 ===")
for r in rows:
    d = dict(zip(cols, r))
    status = "OPEN" if not d['exit_time'] else f"CLOSED"
    print(f"  ID={d['id']} | {d['side']:4s} | qty={d['quantity']} | ${d['price']:.2f} | {str(d['entry_time'])[:16]} | {status} | {d['reason']}")

conn.close()
