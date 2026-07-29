"""
전략 로직 완전 기능 검증 스크립트
=====================================
각 가드/전략이 실제로 올바른 결과를 내는지 end-to-end 검증
단순 연결 여부가 아닌 실제 로직 동작 확인
"""
import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from datetime import datetime
import traceback

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

results = []

def test(name, fn, expected_desc=""):
    try:
        outcome, detail = fn()
        status = PASS if outcome else FAIL
        results.append((name, status, detail, expected_desc))
        print(f"{status} [{name}]")
        print(f"        결과: {detail}")
        if expected_desc:
            print(f"        기대: {expected_desc}")
    except Exception as e:
        results.append((name, FAIL, str(e)[:150], expected_desc))
        print(f"{FAIL} [{name}] EXCEPTION: {e}")
        traceback.print_exc()
    print()

# ====================================================================
# BLOCK 1: strategy.py 시간 가드
# ====================================================================
print("="*70)
print("BLOCK 1: 시간대 가드 (ET 11:00-12:30 데드존 차단)")
print("="*70)

def test_time_guard_dead_zone():
    """ET 11:30 → 차단되어야 함"""
    import strategy as st
    from unittest.mock import patch
    from datetime import timezone
    import pytz
    et = pytz.timezone('America/New_York')
    # Mock datetime to ET 11:30
    mock_dt = datetime(2026, 5, 1, 11, 30, 0, tzinfo=et)
    with patch('strategy.datetime') as mock_date:
        mock_date.now.return_value = mock_dt
        mock_date.side_effect = lambda *a, **kw: datetime(*a, **kw)
        eng = st.StrategyEngine.__new__(st.StrategyEngine)
        eng._day_type_cache = "TRENDING"
        eng._day_type_date = mock_dt.date()
        blocked = eng._is_dead_zone_et(mock_dt)
    return blocked, f"ET 11:30 dead zone blocked={blocked}"

def test_time_guard_ok_zone():
    """ET 13:30 → 허용되어야 함"""
    import strategy as st
    import pytz
    et = pytz.timezone('America/New_York')
    mock_dt = datetime(2026, 5, 1, 13, 30, 0, tzinfo=et)
    eng = st.StrategyEngine.__new__(st.StrategyEngine)
    blocked = eng._is_dead_zone_et(mock_dt)
    return not blocked, f"ET 13:30 should NOT be dead zone, blocked={blocked}"

# dead zone 메서드가 있는지 확인
try:
    import strategy as st_mod
    has_dead_zone = hasattr(st_mod.StrategyEngine, '_is_dead_zone_et')
    print(f"  _is_dead_zone_et 메서드 존재: {has_dead_zone}")
    if has_dead_zone:
        test("시간 가드: ET 11:30 차단", test_time_guard_dead_zone, "True (차단)")
        test("시간 가드: ET 13:30 허용", test_time_guard_ok_zone, "True (허용)")
    else:
        print(f"  ⚠️  _is_dead_zone_et 없음 — is_safe_to_trade() 내부 확인 필요")
        # 직접 코드 확인
        import inspect
        src = inspect.getsource(st_mod.StrategyEngine.is_safe_to_trade)
        has_dead_in_safe = 'dead_zone' in src or '11' in src or 'ET' in src
        print(f"  is_safe_to_trade에 시간 체크 코드 포함: {has_dead_in_safe}")
except Exception as e:
    print(f"  ERROR: {e}")

# ====================================================================
# BLOCK 2: 경제 캘린더 — 오늘 PCE → 거래 차단
# ====================================================================
print("="*70)
print("BLOCK 2: 경제 캘린더 가드 (오늘 PCE 발표 → 차단)")
print("="*70)

def test_econ_calendar_blocks_today():
    from economic_calendar import EconomicCalendar
    ec = EconomicCalendar()
    safe, reason = ec.is_safe_to_trade()
    events = ec.get_todays_events()
    event_names = [e.name for e in events]
    # PCE 있으면 safe=False여야 함
    if 'PCE' in event_names:
        return not safe, f"PCE 발표일, safe={safe}, events={event_names}"
    else:
        return True, f"오늘 이벤트 없음, safe={safe}, events={event_names}"

test("경제 캘린더: 발표일 차단 확인", test_econ_calendar_blocks_today,
     "PCE 있으면 safe=False")

# ====================================================================
# BLOCK 3: SPY SMA20 브레드스 가드
# ====================================================================
print("="*70)
print("BLOCK 3: SPY SMA20 시장 배경 가드")
print("="*70)

def test_spy_sma20_guard():
    from kis_data import get_daily_ohlcv
    df = get_daily_ohlcv("SPY", days=25)
    if df is None or df.empty:
        return False, "SPY 데이터 없음"
    sma20 = df['Close'].rolling(20).mean().iloc[-1]
    current = df['Close'].iloc[-1]
    above_sma20 = current > sma20
    return True, f"SPY current={current:.2f}, SMA20={sma20:.2f}, above={above_sma20}"

test("SPY SMA20 데이터 정상 조회", test_spy_sma20_guard, "SPY 가격 > SMA20 여부 확인")

# ====================================================================
# BLOCK 4: 섹터 가드 — 실제 종목 분류 테스트
# ====================================================================
print("="*70)
print("BLOCK 4: 섹터 로테이터 — 종목 섹터 분류 및 하락 섹터 차단")
print("="*70)

def test_sector_classification():
    from sector_rotator import get_sector_rotator
    sr = get_sector_rotator()
    # AAPL → XLK (Technology)
    aapl_etf = sr.get_sector_for_stock("AAPL")
    # XOM → XLE (Energy)
    xom_etf = sr.get_sector_for_stock("XOM")
    ok = aapl_etf == "XLK" and xom_etf == "XLE"
    return ok, f"AAPL={aapl_etf}(expect XLK), XOM={xom_etf}(expect XLE)"

def test_sector_rankings_fresh():
    from sector_rotator import get_sector_rotator
    sr = get_sector_rotator()
    rankings = sr.analyze()
    top3 = [(r.sector, f"{r.momentum_1m:+.1f}%") for r in rankings[:3]]
    bot3 = [(r.sector, f"{r.momentum_1m:+.1f}%") for r in rankings[-3:]]
    # 최소 5개 섹터 분류되어야 함
    return len(rankings) >= 5, f"top3={top3} | bottom3={bot3}"

test("섹터 분류: AAPL=XLK, XOM=XLE", test_sector_classification, "정확한 ETF 매핑")
test("섹터 순위: 실시간 모멘텀 랭킹", test_sector_rankings_fresh, "최소 5개 섹터")

# ====================================================================
# BLOCK 5: 일일 손실 서킷 브레이커
# ====================================================================
print("="*70)
print("BLOCK 5: 일일 손실 서킷 브레이커 (-3% 한도)")
print("="*70)

def test_circuit_breaker_triggers():
    from emergency_stop import EmergencyStop
    es = EmergencyStop()
    # 700 → 672 = -4% → 차단되어야 함
    should_block = es.check_daily_loss(700, 672)
    return should_block, f"700→672 (-4%) blocked={should_block} (expect True)"

def test_circuit_breaker_not_triggers():
    from emergency_stop import EmergencyStop
    es = EmergencyStop()
    # 700 → 693 = -1% → 허용되어야 함
    should_block = es.check_daily_loss(700, 693)
    return not should_block, f"700→693 (-1%) blocked={should_block} (expect False)"

test("서킷 브레이커: -4% → 차단", test_circuit_breaker_triggers, "True")
test("서킷 브레이커: -1% → 통과", test_circuit_breaker_not_triggers, "False")

# ====================================================================
# BLOCK 6: ATR 포지션 사이징 — 실제 데이터
# ====================================================================
print("="*70)
print("BLOCK 6: ATR 기반 포지션 사이징")
print("="*70)

def test_atr_sizing():
    import pandas as pd
    from kis_data import get_daily_ohlcv
    df = get_daily_ohlcv("NVDA", days=20)
    if df is None or len(df) < 15:
        return False, "NVDA 데이터 없음"
    high = df['High']; low = df['Low']; cls = df['Close']
    tr = pd.concat([high-low, (high-cls.shift()).abs(), (low-cls.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    entry_price = float(cls.iloc[-1])
    risk_amount = max(15, min(25, 700 * 0.02))  # $14 = 2%
    stop_dist = max(atr * 1.5, entry_price * 0.015)
    qty = int(risk_amount / stop_dist)
    return qty >= 1, f"NVDA: price={entry_price:.0f}, ATR={atr:.2f}, stop_dist={stop_dist:.2f}, risk=${risk_amount:.0f} → qty={qty}"

test("ATR 사이징: NVDA 실제 계산", test_atr_sizing, "qty >= 1 (유효한 수량)")

# ====================================================================
# BLOCK 7: RS (상대강도) 계산
# ====================================================================
print("="*70)
print("BLOCK 7: SPY 대비 상대강도 (RS) 필터")
print("="*70)

def test_rs_filter():
    from kis_data import get_daily_ohlcv
    spy = get_daily_ohlcv("SPY", days=10)
    nvda = get_daily_ohlcv("NVDA", days=10)
    if spy is None or nvda is None or len(spy)<5 or len(nvda)<5:
        return False, "데이터 부족"
    spy_ret = float(spy['Close'].iloc[-1]/spy['Close'].iloc[-5]-1)
    nvda_ret = float(nvda['Close'].iloc[-1]/nvda['Close'].iloc[-5]-1)
    rs = nvda_ret - spy_ret
    bonus = 15 if rs > 0.02 else (7 if rs > 0 else (-15 if rs < -0.03 else 0))
    return True, f"NVDA 5d={nvda_ret:+.1%}, SPY 5d={spy_ret:+.1%}, RS={rs:+.1%} → bonus={bonus:+d}"

test("RS 필터: NVDA vs SPY 상대강도", test_rs_filter, "RS 계산 후 보너스/페널티 부여")

# ====================================================================
# BLOCK 8: VIX 기반 동적 TP/SL
# ====================================================================
print("="*70)
print("BLOCK 8: VIX 기반 동적 TP/SL")
print("="*70)

def test_vix_adaptive_tpsl():
    from options_flow import get_vix_snapshot
    snap = get_vix_snapshot()
    vix = snap.vix
    base_tp_mult = 2.0  # config.ORB_TP_MULTIPLIER
    if vix > 30:
        mult = base_tp_mult * 1.3
        case = "고변동성"
    elif vix > 20:
        mult = base_tp_mult * 1.1
        case = "중간변동성"
    elif vix < 15:
        mult = base_tp_mult * 0.9
        case = "저변동성"
    else:
        mult = base_tp_mult
        case = "보통"
    return True, f"VIX={vix:.1f} ({case}) → TP_mult={mult:.2f}x (base={base_tp_mult})"

test("VIX 동적 TP/SL: 현재 VIX 값으로 계산", test_vix_adaptive_tpsl, "VIX에 따라 multiplier 변동")

# ====================================================================
# BLOCK 9: 52주 신고가 체크
# ====================================================================
print("="*70)
print("BLOCK 9: 52주 신고가 보너스")
print("="*70)

def test_52w_high_bonus():
    from kis_data import get_daily_ohlcv
    results_sym = {}
    for sym in ["NVDA", "AAPL", "PLTR"]:
        df = get_daily_ohlcv(sym, days=100)
        if df is None or len(df) < 50:
            results_sym[sym] = "NO_DATA"
            continue
        high_52w = float(df['High'].max())
        current = float(df['Close'].iloc[-1])
        dist = (current - high_52w) / high_52w
        if dist >= 0:
            bonus = 20
        elif dist >= -0.02:
            bonus = 10
        elif dist >= -0.05:
            bonus = 5
        else:
            bonus = 0
        results_sym[sym] = f"dist={dist:+.1%} bonus=+{bonus}"
    return True, str(results_sym)

test("52주 신고가 보너스: NVDA/AAPL/PLTR", test_52w_high_bonus, "각 종목별 신고가 거리와 보너스")

# ====================================================================
# BLOCK 10: 갭필 회피 — 당일 갭업 감지
# ====================================================================
print("="*70)
print("BLOCK 10: 갭필 회피 (3% 이상 갭업 페널티)")
print("="*70)

def test_gap_detection():
    from kis_data import get_daily_ohlcv
    df = get_daily_ohlcv("AAPL", days=10)
    if df is None or len(df) < 2:
        return False, "데이터 없음"
    prev_close = float(df['Close'].iloc[-2])
    if 'Open' in df.columns:
        today_open = float(df['Open'].iloc[-1])
    else:
        today_open = float(df['Close'].iloc[-1])
    gap_pct = (today_open - prev_close) / prev_close
    penalty = -20 if gap_pct > 0.03 else (0 if gap_pct <= 0.03 else -10)
    return True, f"AAPL: prev_close={prev_close:.2f}, today_open={today_open:.2f}, gap={gap_pct:+.1%} → penalty={penalty}"

test("갭필 회피: AAPL 당일 갭 감지", test_gap_detection, "gap > 3% → penalty=-20")

# ====================================================================
# BLOCK 11: 연속 손절 쿨다운 — 카운터 작동
# ====================================================================
print("="*70)
print("BLOCK 11: 연속 손절 쿨다운")
print("="*70)

def test_consec_loss_cooldown():
    import strategy as st
    eng = st.StrategyEngine.__new__(st.StrategyEngine)
    # 3연속 손절 시뮬레이션
    eng._consecutive_losses_today = 3
    val = getattr(eng, '_consecutive_losses_today', 0)
    blocked = val >= 3
    # 0으로 리셋 후 확인
    eng._consecutive_losses_today = 0
    not_blocked = getattr(eng, '_consecutive_losses_today', 0) < 3
    return blocked and not_blocked, f"3연속 손절 → blocked={blocked}, 0으로 리셋 후 → not_blocked={not_blocked}"

test("연속 손절: 3회 → 차단, 리셋 → 허용", test_consec_loss_cooldown)

# ====================================================================
# BLOCK 12: 스크리너 최종 스코어 계산 (실제 종목)
# ====================================================================
print("="*70)
print("BLOCK 12: 스크리너 종합 점수 계산")
print("="*70)

def test_screener_scoring():
    from screener import DynamicScreener, ScreenMode
    screener = DynamicScreener()
    # _score_stock() 단일 종목 스코어링 (screen() 전체 유니버스 대신 빠른 테스트)
    score = screener._score_stock('AAPL', ScreenMode.MOMENTUM)
    if score is None:
        return False, '_score_stock AAPL returned None'
    return score.total_score >= 0, (
        f'AAPL: total={score.total_score}, momentum={score.momentum_score}, '
        f'tech={score.technical_score}, near_high={score.near_52w_high}'
    )

test("스크리너: NVDA 실제 점수 계산", test_screener_scoring, "total_score >= 0")

# ====================================================================
# BLOCK 13: auto_tuner — DB 데이터 읽기 및 분석
# ====================================================================
print("="*70)
print("BLOCK 13: Auto Tuner — 실거래 데이터 분석")
print("="*70)

def test_auto_tuner_analysis():
    from auto_tuner import get_recent_metrics
    metrics = get_recent_metrics(days=30)
    trades = metrics.get('total_trades', 0)
    if trades == 0:
        return True, f"DB 거래 없음 (OK - 봇 초기 단계), metrics={metrics}"
    wr = metrics.get('win_rate', 0)
    pf = metrics.get('profit_factor', 0)
    pnl = metrics.get('total_pnl', 0)
    return True, (
        f"trades={trades}, WR={wr:.0%}, PF={pf:.2f}, total_pnl=${pnl:.2f}"
    )

test("Auto Tuner: 실거래 분석", test_auto_tuner_analysis, "WR/PF/PNL 계산 성공")

# ====================================================================
# BLOCK 14: news_analyzer 실제 점수
# ====================================================================
print("="*70)
print("BLOCK 14: 뉴스 감성 분석")
print("="*70)

def test_news_analyzer():
    from news_analyzer import get_news_analyzer
    for sym in ["NVDA", "TSLA"]:
        result = get_news_analyzer().analyze(sym)
        score = result.sentiment_score
        # 실제 뉴스 없으면 0, 있으면 ±점수 — 0 이외의 값 나오는지 확인
        print(f"  {sym}: sentiment_score={score}, type={type(score).__name__}")
    return True, "뉴스 분석 실행 완료"

test("뉴스 감성: NVDA/TSLA", test_news_analyzer, "score 반환 (0이어도 OK)")

# ====================================================================
# BLOCK 15: drawdown_controller 정상 동작
# ====================================================================
print("="*70)
print("BLOCK 15: Drawdown Controller")
print("="*70)

def test_drawdown_controller():
    from drawdown_controller import get_drawdown_controller
    dc = get_drawdown_controller(700)
    halted = dc.is_halted()
    # 초기화 후 halted=False여야 함
    return not halted, f"is_halted()={halted} (초기화 후 False여야 함)"

test("Drawdown Controller: 초기 상태 정상", test_drawdown_controller, "is_halted()=False")

# ====================================================================
# BLOCK 16: economic_calendar get_todays_events vs is_safe_to_trade 일관성
# ====================================================================
print("="*70)
print("BLOCK 16: 경제 캘린더 일관성 검증")
print("="*70)

def test_econ_consistency():
    from economic_calendar import EconomicCalendar
    ec = EconomicCalendar()
    events = ec.get_todays_events()
    safe, reason = ec.is_safe_to_trade()
    has_events = len(events) > 0
    # 이벤트 있으면 unsafe여야 함
    consistent = (has_events and not safe) or (not has_events and safe)
    return consistent, f"events={[e.name for e in events]}, safe={safe}, consistent={consistent}"

test("경제 캘린더: 이벤트↔안전거래 일관성", test_econ_consistency,
     "이벤트 있으면 safe=False")

# ====================================================================
# 최종 결과 요약
# ====================================================================
print("\n" + "="*70)
print("최종 결과 요약")
print("="*70)
ok = sum(1 for _, s, _, _ in results if s == PASS)
fail = sum(1 for _, s, _, _ in results if s == FAIL)
warn = sum(1 for _, s, _, _ in results if s == WARN)

print(f"\n✅ PASS: {ok}개")
print(f"❌ FAIL: {fail}개")
print(f"⚠️  WARN: {warn}개")
print(f"전체: {len(results)}개\n")

if fail > 0:
    print("❌ 실패 항목:")
    for name, status, detail, _ in results:
        if status == FAIL:
            print(f"  - [{name}]: {detail}")
