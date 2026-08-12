"""DB positions 테이블 확인 및 오래된 데이터(quantity=0 또는 청산된 종목) 정리"""
import sqlite3, os, sys

sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

DB = '/home/ubuntu/kis-auto-trading/trades.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 테이블 목록
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [t[0] for t in cur.fetchall()])

# positions 현재 상태
print("\n=== positions (before cleanup) ===")
cur.execute("SELECT symbol, quantity, avg_price FROM positions")
rows = cur.fetchall()
for r in rows:
    print(f"  {r}")

# KIS 실제 포지션 (기준)
try:
    from trader import Trader
    t = Trader()
    live = t.get_positions()
    live_symbols = {p.symbol for p in live}
    print(f"\n=== KIS Live Positions: {live_symbols} ===")

    # DB에서 KIS에 없는 종목 정리 (quantity=0 또는 old)
    for r in rows:
        sym = r[0]
        if sym not in live_symbols:
            print(f"  🗑  Removing stale: {sym}")
            cur.execute("DELETE FROM positions WHERE symbol=?", (sym,))

    conn.commit()
    print("\n=== positions (after cleanup) ===")
    cur.execute("SELECT symbol, quantity, avg_price FROM positions")
    for r in cur.fetchall():
        print(f"  {r}")
except Exception as e:
    print(f"KIS API error: {e}")

conn.close()
print("\nDone.")
