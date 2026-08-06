import sqlite3
import os

os.chdir("/home/ubuntu/kis-auto-trading")
conn = sqlite3.connect("trades.db")
c = conn.cursor()

c.execute("SELECT COUNT(*), AVG(pnl_pct), SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END)*100.0/COUNT(*) FROM trades WHERE exit_time IS NOT NULL AND pnl_pct != 0")
row = c.fetchone()
total = row[0] or 0
avg_pnl = row[1]
win_rate = row[2]
print(f"Total closed trades: {total}")
print(f"Avg PnL: {avg_pnl:.2%}" if avg_pnl else "Avg PnL: N/A")
print(f"Win rate: {win_rate:.1f}%" if win_rate else "Win rate: N/A")

c.execute("SELECT symbol, pnl_pct, exit_time FROM trades WHERE exit_time IS NOT NULL ORDER BY exit_time DESC LIMIT 10")
print("\nLast 10 trades:")
for r in c.fetchall():
    print(f"  {r[2][:16]}  {r[0]:8s}  pnl={r[1]:.2%}")

c.execute("SELECT SUM(pnl_pct) FROM trades WHERE exit_time IS NOT NULL AND pnl_pct != 0")
total_pnl = c.fetchone()[0]
print(f"\nTotal cumulative PnL: {total_pnl:.2%}" if total_pnl else "\nTotal cumulative PnL: N/A")

conn.close()
