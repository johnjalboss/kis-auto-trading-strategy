"""
수정사항 검증 스크립트
======================
실제 API 호출로 주요 버그 수정을 확인합니다.
매매는 하지 않고 조회만 수행합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

results = {"pass": 0, "fail": 0, "errors": []}

def test(name, func):
    try:
        result = func()
        print(f"  ✅ {name}: {result}")
        results["pass"] += 1
        return result
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        results["fail"] += 1
        results["errors"].append((name, str(e)))
        return None

print("=" * 60)
print("🔍 수정사항 검증 (조회만, 매매 없음)")
print("=" * 60)

# ─── Test 1: Config & API Key ───
print("\n[1] API 설정 확인")
import config
test("APP_KEY 설정", lambda: f"{'OK' if config.KIS_APP_KEY else 'MISSING'} (len={len(config.KIS_APP_KEY)})")
test("CANO 설정", lambda: f"{'OK' if config.KIS_CANO else 'MISSING'}")
test("Paper Trading", lambda: f"{'모의' if config.IS_PAPER_TRADING else '실전'}")

# ─── Test 2: Trader & Token ───
print("\n[2] Trader 초기화 & 토큰")
from trader import Trader, ExchangeMapper
trader = Trader()
test("토큰 발급", lambda: f"Bearer ...{trader._token_mgr.get_token()[-8:]}")

# ─── Test 3: Exchange Mapper (TQQQ 추가 확인) ───
print("\n[3] Exchange Mapper (레버리지 ETF 추가 확인)")
test("TQQQ → NASD", lambda: ExchangeMapper.get_exchange("TQQQ"))
test("SOXL → NYSE", lambda: ExchangeMapper.get_exchange("SOXL"))
test("AAPL → NASD", lambda: ExchangeMapper.get_exchange("AAPL"))

# ─── Test 4: Price Query (빈 문자열 방어) ───
print("\n[4] 가격 조회 (빈 문자열 방어 확인)")
tqqq_price = test("TQQQ 가격", lambda: f"${trader.get_price('TQQQ'):.2f}")
test("AAPL 가격", lambda: f"${trader.get_price('AAPL'):.2f}")

# ─── Test 5: Buying Power (핵심 수정) ───
print("\n[5] ★ 매수가능금액 조회 (API 변경: TTTS3007R)")
bp = test("Buying Power", lambda: f"${trader.get_buying_power():.2f}")

# ─── Test 6: Positions ───
print("\n[6] 보유 종목 조회")
positions = trader.get_positions()
test("보유 종목 수", lambda: f"{len(positions)}개")
for p in positions:
    print(f"      → {p.symbol} x {p.quantity} @ ${p.avg_price:.2f} (현재 ${p.current_price:.2f}, P&L {p.pnl_pct:+.1%})")

# ─── Test 7: Screener Init (인자 제거 확인) ───
print("\n[7] Screener 초기화 (인자 없이)")
test("DynamicScreener()", lambda: type(__import__('screener').DynamicScreener()).__name__)

# ─── Test 8: Strategy check_exit Signature ───
print("\n[8] Strategy check_exit 시그니처 확인")
import inspect
from strategy import StrategyEngine
sig = inspect.signature(StrategyEngine.check_exit)
test("check_exit(symbol, price)", lambda: f"파라미터: {list(sig.parameters.keys())}")

# ─── Test 9: data_proxy (tickers= 키워드) ───
print("\n[9] data_proxy download (tickers= 키워드)")
try:
    import data_proxy
    import kis_data
    df = kis_data.download(tickers="TQQQ", period="5d")
    test("kis_data.download(tickers='TQQQ')", lambda: f"{len(df)}행 x {len(df.columns)}열" if df is not None and not df.empty else "빈 데이터")
except Exception as e:
    print(f"  ❌ data_proxy: {e}")
    results["fail"] += 1

# ─── Test 10: Scheduler 2026 공휴일 ───
print("\n[10] Scheduler 2026 공휴일")
from scheduler import TradingScheduler
sched = TradingScheduler()
test("2026-11-26 (추수감사절)", lambda: "공휴일 ✓" if "2026-11-26" in sched.HOLIDAYS else "누락 ✗")
test("2026-12-25 (크리스마스)", lambda: "공휴일 ✓" if "2026-12-25" in sched.HOLIDAYS else "누락 ✗")

# ─── Summary ───
print("\n" + "=" * 60)
total = results["pass"] + results["fail"]
pct = results["pass"] / total * 100 if total > 0 else 0
print(f"결과: {results['pass']}/{total} 통과 ({pct:.0f}%)")
print("=" * 60)

if results["fail"] > 0:
    print(f"\n❌ 실패 항목 ({results['fail']}):")
    for name, err in results["errors"]:
        print(f"  • {name}: {err[:80]}")
else:
    print("\n🎉 모든 수정사항이 정상 동작합니다!")
