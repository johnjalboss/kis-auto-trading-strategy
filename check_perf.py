import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('trading.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

# Get trades
try:
    cur.execute("""
    SELECT symbol, entry_price, exit_price, quantity, pnl, pnl_pct, entry_time, exit_time, reason
    FROM trades WHERE exit_time IS NOT NULL
    ORDER BY exit_time DESC LIMIT 100
    """)
    trades = cur.fetchall()
except Exception as e:
    print("trades table error:", e)
    trades = []

total = len(trades)
wins = [t for t in trades if t['pnl'] and float(t['pnl']) > 0]
losses = [t for t in trades if t['pnl'] and float(t['pnl']) <= 0]
total_pnl = sum(float(t['pnl']) for t in trades if t['pnl'])
avg_win = sum(float(t['pnl']) for t in wins) / max(len(wins), 1)
avg_loss = sum(float(t['pnl']) for t in losses) / max(len(losses), 1)

print("=== 전체 거래 통계 ({} 건) ===".format(total))
print("승률: {}/{} = {:.1f}%".format(len(wins), total, len(wins)/max(total,1)*100))
print("총 손익: ${:.2f}".format(total_pnl))
print("평균 수익(승): ${:.2f}".format(avg_win))
print("평균 손실(패): ${:.2f}".format(avg_loss))
if avg_loss != 0:
    print("손익비(PF): {:.2f}".format(abs(avg_win/avg_loss)))

# 최근 30일
cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
recent = [t for t in trades if t['exit_time'] and str(t['exit_time']) > cutoff]
r_wins = [t for t in recent if t['pnl'] and float(t['pnl']) > 0]
r_pnl = sum(float(t['pnl']) for t in recent if t['pnl'])
print("")
print("=== 최근 30일 ({} 건) ===".format(len(recent)))
print("승률: {}/{} = {:.1f}%".format(len(r_wins), len(recent), len(r_wins)/max(len(recent),1)*100))
print("총 손익: ${:.2f}".format(r_pnl))

# 최근 10건
print("")
print("=== 최근 10건 ===")
for t in trades[:10]:
    pnl = float(t['pnl']) if t['pnl'] else 0
    pnl_pct = float(t['pnl_pct']) if t['pnl_pct'] else 0
    sign = '+' if pnl >= 0 else ''
    reason = str(t['reason'])[:35] if t['reason'] else ''
    print("{:6s}  {}{:.2f}$ ({}{:.1f}%)  {}".format(
        str(t['symbol']), sign, pnl, sign, pnl_pct, reason))

# 보유 포지션
print("")
print("=== 현재 보유 포지션 ===")
try:
    cur.execute("""
    SELECT symbol, entry_price, quantity, entry_time
    FROM trades WHERE exit_time IS NULL
    ORDER BY entry_time DESC
    """)
    positions = cur.fetchall()
    for p in positions:
        print("{:6s}  qty={} @ ${:.2f}  since {}".format(
            str(p['symbol']), p['quantity'], float(p['entry_price']), str(p['entry_time'])[:16]))
except Exception as e:
    print("Position query error:", e)

conn.close()
