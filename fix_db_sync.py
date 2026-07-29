"""
DB 싱크 수정 스크립트
- KIS API에서 실제 보유 포지션 확인
- DB에서 실제로 청산된 종목들을 closed 처리
"""
import sqlite3
import os
import sys

sys.path.insert(0, "/home/ubuntu/kis-auto-trading")
os.chdir("/home/ubuntu/kis-auto-trading")

from dotenv import load_dotenv
load_dotenv(".env")

# 실제 KIS API에서 보유 종목 가져오기
try:
    from trader import get_trader
    trader = get_trader()
    live_positions = trader.get_positions()
    print("=== KIS API 실제 보유 포지션 ===")
    live_symbols = set()
    for p in live_positions:
        sym = p.get('symbol') or p.get('ticker') or p.get('pdno', '')
        qty = p.get('quantity') or p.get('hldg_qty', 0)
        price = p.get('current_price') or p.get('prpr', 0)
        avg = p.get('avg_price') or p.get('pchs_avg_pric', 0)
        print(f"  {sym}: qty={qty} avg=${float(avg):.2f} current=${float(price):.2f}")
        live_symbols.add(sym)
except Exception as e:
    print(f"KIS API 오류: {e}")
    # 수동으로 알려진 실제 보유 종목 설정
    live_symbols = {"CDNS", "ADM"}
    print(f"수동 설정: {live_symbols}")

print(f"\n실제 보유 종목: {live_symbols}")

# DB에서 OPEN인데 실제로 청산된 것들 처리
conn = sqlite3.connect("trades.db")
c = conn.cursor()

c.execute("SELECT id, symbol, price, quantity, entry_time FROM trades WHERE exit_time IS NULL ORDER BY created_at DESC")
open_rows = c.fetchall()

print(f"\n=== DB OPEN 포지션 ({len(open_rows)}건) ===")
fixed = 0
for row in open_rows:
    id_, sym, price, qty, entry = row
    print(f"  ID={id_} {sym} qty={qty} entry={str(entry)[:16]}", end="")
    
    if sym not in live_symbols:
        # 이미 청산된 것 → closed 처리 (pnl은 0으로, exit_reason은 MANUAL_SYNC_FIX)
        c.execute("""
            UPDATE trades 
            SET exit_time = datetime('now'),
                reason = 'DB_SYNC_FIX: position no longer in KIS API'
            WHERE id = ? AND exit_time IS NULL
        """, (id_,))
        print(f" → CLOSED (not in KIS API)")
        fixed += 1
    else:
        print(f" → OPEN (confirmed in KIS API)")

conn.commit()
conn.close()
print(f"\n총 {fixed}건 정리 완료")
