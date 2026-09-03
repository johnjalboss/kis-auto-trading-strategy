import sqlite3
import os

os.chdir("/home/ubuntu/kis-auto-trading")
conn = sqlite3.connect("trades.db")
c = conn.cursor()

# exit reason (컬럼명 = 'reason')
c.execute("SELECT reason, COUNT(*), AVG(pnl_pct) FROM trades WHERE exit_time IS NOT NULL GROUP BY reason ORDER BY COUNT(*) DESC LIMIT 15")
print("Exit reasons:")
for r in c.fetchall():
    reason = str(r[0])[:30] if r[0] else "None"
    print(f"  {reason:32s} n={r[1]:3d}  avg={r[2]:.2%}")

# 승/패 비율 요약
c.execute("SELECT AVG(CASE WHEN pnl_pct > 0 THEN pnl_pct END), AVG(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) END) FROM trades WHERE exit_time IS NOT NULL AND pnl_pct != 0")
row = c.fetchone()
avg_win = row[0] or 0
avg_loss = row[1] or 0
print(f"\nAvg win:  +{avg_win:.2%}")
print(f"Avg loss: -{avg_loss:.2%}")
if avg_loss > 0:
    print(f"Risk/Reward: {avg_win/avg_loss:.2f}x")

# 월별 성과
c.execute("""
    SELECT 
        strftime('%Y-%m', exit_time) as month,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)*100.0/COUNT(*) as wr,
        AVG(pnl_pct) as avg_pnl,
        SUM(pnl_pct) as total_pnl
    FROM trades 
    WHERE exit_time IS NOT NULL AND pnl_pct != 0
    GROUP BY month ORDER BY month
""")
print("\nMonthly performance:")
for r in c.fetchall():
    print(f"  {r[0]}  trades={r[1]:3d}  WR={r[2]:.0f}%  avg={r[3]:.2%}  total={r[4]:.2%}")

conn.close()
