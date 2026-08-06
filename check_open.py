import sqlite3
import os

os.chdir("/home/ubuntu/kis-auto-trading")
conn = sqlite3.connect("trades.db")
c = conn.cursor()

# 오픈 포지션 (exit_time 없는 것)
c.execute("SELECT id, symbol, side, quantity, price, total, entry_time, created_at FROM trades WHERE exit_time IS NULL ORDER BY created_at DESC LIMIT 10")
cols = [d[0] for d in c.description]
rows = c.fetchall()
print("=== 현재 오픈 포지션 (DB) ===")
if rows:
    for r in rows:
        d = dict(zip(cols, r))
        print(f"  {d['symbol']:6s} | {d['side']:4s} | qty={d['quantity']} | price=${d['price']:.2f} | entry={str(d['entry_time'])[:16]}")
else:
    print("  없음")

# 최근 BUY 포지션 (exit 있든 없든) - 최근 5건
c.execute("SELECT id, symbol, side, quantity, price, entry_time, exit_time, pnl, pnl_pct FROM trades WHERE side='BUY' ORDER BY created_at DESC LIMIT 10")
cols2 = [d[0] for d in c.description]
rows2 = c.fetchall()
print("\n=== 최근 BUY 10건 ===")
for r in rows2:
    d = dict(zip(cols2, r))
    status = "OPEN" if not d['exit_time'] else f"CLOSED pnl={d['pnl_pct']:.2%}"
    print(f"  {d['symbol']:6s} | qty={d['quantity']} | ${d['price']:.2f} | {str(d['entry_time'])[:16]} | {status}")

conn.close()
