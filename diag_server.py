#!/usr/bin/env python3
"""서버에서 직접 실행해 DB와 로그 상태를 진단하는 스크립트"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import sqlite3
from datetime import datetime, date, timedelta

db_path = '/home/ubuntu/kis-auto-trading/trades.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("【 최근 30개 거래 내역 】")
print("=" * 60)
try:
    rows = cur.execute("""
        SELECT date, symbol, side, qty, price, pnl, pnl_pct
        FROM trades ORDER BY date DESC LIMIT 30
    """).fetchall()
    for r in rows:
        pnl_str = f"${r['pnl']:+.2f} ({r['pnl_pct']:+.1%})" if r['pnl'] is not None else "진행중"
        print(f"  {r['date']}  {r['symbol']:6s}  {r['side']}  {r['qty']}주  ${r['price']:.2f}  {pnl_str}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("【 최근 21일 일별 손익 】")
print("=" * 60)
try:
    rows = cur.execute("""
        SELECT date(date) as d,
               COUNT(*) FILTER (WHERE side='SELL') as sells,
               SUM(pnl) FILTER (WHERE side='SELL') as daily_pnl,
               SUM(CASE WHEN side='SELL' AND pnl>0 THEN 1 ELSE 0 END) as wins
        FROM trades
        WHERE date >= date('now', '-21 days')
        GROUP BY d ORDER BY d DESC
    """).fetchall()
    total = 0
    for r in rows:
        pnl = r['daily_pnl'] or 0
        total += pnl
        emoji = "🟢" if pnl >= 0 else "🔴"
        print(f"  {emoji} {r['d']}  거래:{r['sells']}건  손익:${pnl:+.2f}  승:{r['wins']}")
    print(f"  【 3주 누계 】 ${total:+.2f}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("【 현재 오픈 포지션 】")
print("=" * 60)
try:
    rows = cur.execute("""
        SELECT symbol, qty, entry_price, entry_date
        FROM positions WHERE status='OPEN'
        ORDER BY entry_date DESC
    """).fetchall()
    if not rows:
        # fallback: 매수 후 매도 안된 것 찾기
        rows2 = cur.execute("""
            SELECT symbol, SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END) as net_qty,
                   AVG(CASE WHEN side='BUY' THEN price END) as avg_buy
            FROM trades GROUP BY symbol
            HAVING net_qty > 0
        """).fetchall()
        for r in rows2:
            print(f"  {r['symbol']:6s}  {r['net_qty']}주  평균단가:${r['avg_buy']:.2f}")
    else:
        for r in rows:
            print(f"  {r['symbol']:6s}  {r['qty']}주  단가:${r['entry_price']:.2f}  진입:{r['entry_date']}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("【 reports_sent 테이블 (알림 발송 기록) 】")
print("=" * 60)
try:
    rows = cur.execute("""
        SELECT report_type, report_date FROM reports_sent
        ORDER BY report_date DESC LIMIT 20
    """).fetchall()
    for r in rows:
        print(f"  {r['report_type']:20s}  {r['report_date']}")
    if not rows:
        print("  (기록 없음 — 알림이 전혀 발송되지 않았을 수 있음)")
except Exception as e:
    print(f"  ERROR (테이블 없을 수도): {e}")

conn.close()
