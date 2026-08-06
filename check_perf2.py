import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('trades.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 완료된 거래만 (BUY+SELL 페어, pnl 있는 것)
cur.execute("""
SELECT symbol, side, quantity, price, total, entry_time, exit_time, pnl, pnl_pct, reason, regime
FROM trades
WHERE pnl IS NOT NULL AND side = 'SELL'
ORDER BY exit_time DESC
""")
closed = cur.fetchall()

# 전체 통계
total = len(closed)
wins = [t for t in closed if float(t['pnl']) > 0]
losses = [t for t in closed if float(t['pnl']) <= 0]
total_pnl = sum(float(t['pnl']) for t in closed)
avg_win = sum(float(t['pnl']) for t in wins) / max(len(wins), 1)
avg_loss = sum(float(t['pnl']) for t in losses) / max(len(losses), 1)
pf = abs(avg_win / avg_loss) if avg_loss != 0 else 0

print("=" * 50)
print("전체 거래 통계 (총 {}건)".format(total))
print("=" * 50)
print("승률: {}/{} = {:.1f}%".format(len(wins), total, len(wins)/max(total,1)*100))
print("총 손익: ${:.2f}".format(total_pnl))
print("평균 수익: ${:.2f}".format(avg_win))
print("평균 손실: ${:.2f}".format(avg_loss))
print("손익비(PF): {:.2f}".format(pf))
print("기대값(EV): ${:.2f}/trade".format(total_pnl/max(total,1)))

# 최근 30일
cutoff30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
r30 = [t for t in closed if str(t['exit_time']) >= cutoff30]
r30_wins = [t for t in r30 if float(t['pnl']) > 0]
r30_pnl = sum(float(t['pnl']) for t in r30)

print("")
print("=== 최근 30일 ({}건) ===".format(len(r30)))
print("승률: {}/{} = {:.1f}%".format(len(r30_wins), len(r30), len(r30_wins)/max(len(r30),1)*100))
print("총 손익: ${:.2f}".format(r30_pnl))

# 최근 7일
cutoff7 = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
r7 = [t for t in closed if str(t['exit_time']) >= cutoff7]
r7_wins = [t for t in r7 if float(t['pnl']) > 0]
r7_pnl = sum(float(t['pnl']) for t in r7)

print("")
print("=== 최근 7일 ({}건) ===".format(len(r7)))
print("승률: {}/{} = {:.1f}%".format(len(r7_wins), len(r7), len(r7_wins)/max(len(r7),1)*100))
print("총 손익: ${:.2f}".format(r7_pnl))

# 최근 20건 상세
print("")
print("=== 최근 20건 상세 ===")
print("{:6s} {:>8s} {:>7s}  {}".format("종목", "PNL", "수익률", "이유"))
for t in closed[:20]:
    pnl = float(t['pnl'])
    pnl_pct = float(t['pnl_pct']) if t['pnl_pct'] else 0
    sign = '+' if pnl >= 0 else ''
    emoji = "✅" if pnl > 0 else "❌"
    reason = str(t['reason'])[:30] if t['reason'] else ''
    print("{} {:6s}  {}{:.2f}$ ({}{:.1f}%)  {}".format(
        emoji, str(t['symbol']), sign, pnl, sign, pnl_pct, reason))

# 종목별 성과
print("")
print("=== 종목별 성과 ===")
sym_stats = {}
for t in closed:
    sym = str(t['symbol'])
    if sym not in sym_stats:
        sym_stats[sym] = {'wins': 0, 'losses': 0, 'pnl': 0}
    pnl = float(t['pnl'])
    sym_stats[sym]['pnl'] += pnl
    if pnl > 0:
        sym_stats[sym]['wins'] += 1
    else:
        sym_stats[sym]['losses'] += 1

sorted_syms = sorted(sym_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
for sym, stats in sorted_syms[:15]:
    total_trades = stats['wins'] + stats['losses']
    wr = stats['wins'] / max(total_trades, 1) * 100
    sign = '+' if stats['pnl'] >= 0 else ''
    print("{:6s}  {}트레이드  승률{:.0f}%  {}{:.2f}$".format(
        sym, total_trades, wr, sign, stats['pnl']))

# 일별 통계
print("")
print("=== daily_stats 최근 7일 ===")
cur.execute("""
SELECT date, trades_count, wins, losses, gross_pnl, ending_balance
FROM daily_stats
ORDER BY date DESC LIMIT 7
""")
days = cur.fetchall()
for d in days:
    wins_d = d['wins'] or 0
    trades_d = d['trades_count'] or 0
    wr = wins_d/max(trades_d,1)*100
    pnl = float(d['gross_pnl']) if d['gross_pnl'] else 0
    bal = float(d['ending_balance']) if d['ending_balance'] else 0
    sign = '+' if pnl >= 0 else ''
    print("{}  {}건 승률{:.0f}%  {}{:.2f}$  잔고${:.2f}".format(
        d['date'], trades_d, wr, sign, pnl, bal))

conn.close()
