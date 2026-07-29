"""스크리너 근본 문제 진단"""
import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

# 1. 유니버스 확인
import config
print("=== 현재 유니버스 ===")
universe = getattr(config, 'BASE_UNIVERSE', getattr(config, 'STOCK_UNIVERSE', []))
print(f"총 {len(universe)}개: {universe[:30]}...")

# 2. 스크리너 후보 선정 로직 확인
import sqlite3
from datetime import datetime, timedelta

print("\n=== 최근 7일 거래 빈도 ===")
conn = sqlite3.connect('trades.db')
rows = conn.execute("""
    SELECT symbol, COUNT(*) as cnt, 
           SUM(CASE WHEN side='BUY' THEN 1 ELSE 0 END) as buys,
           SUM(CASE WHEN side='SELL' THEN 1 ELSE 0 END) as sells,
           MAX(created_at) as last_trade
    FROM trades 
    WHERE created_at >= ?
    GROUP BY symbol ORDER BY cnt DESC
""", ((datetime.now() - timedelta(days=7)).isoformat(),)).fetchall()
for r in rows:
    print(f"  {r[0]:6}: {r[1]}회 (매수{r[2]}/매도{r[3]}) 마지막={r[4][:10]}")

print("\n=== 스크리너 실제 후보 선정 방식 확인 ===")
from screener import DynamicScreener, ScreenMode
s = DynamicScreener()
# get_candidates 내부 로직 확인
import inspect
src = inspect.getsource(s.screen)
# 후보 선정 부분 추출
lines = src.split('\n')
for i, l in enumerate(lines[:50]):
    print(f"  {i}: {l}")

conn.close()
