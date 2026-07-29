"""
전체 시스템 연결 상태 완전 검증 스크립트
- Phase 1~6 모든 모듈 실제 데이터 반환 여부
- strategy.py 가드 데이터 소스 연결 여부
- 크로스 모듈 연결 상태
"""
import sys, os, traceback
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

results = []

def check(name, fn):
    try:
        result = fn()
        status = "✅" if result else "⚠️ (empty/None)"
        results.append((name, status, str(result)[:80] if result else "None/Empty"))
    except Exception as e:
        results.append((name, "❌ ERROR", str(e)[:120]))

# ============================================================
# 1. kis_data 핵심 함수들
# ============================================================
check("kis_data.get_daily_ohlcv(SPY)", lambda: __import__('kis_data').get_daily_ohlcv("SPY", days=25))
check("kis_data.get_daily_ohlcv(AAPL)", lambda: __import__('kis_data').get_daily_ohlcv("AAPL", days=25))
check("kis_data.get_current_price(AAPL)", lambda: __import__('kis_data').get_current_price("AAPL"))

# ============================================================
# 2. VIX / Options
# ============================================================
def _vix():
    from vix_monitor import get_vix_snapshot
    snap = get_vix_snapshot()
    return f"VIX={snap.vix}, adj={snap.score_adj}"
check("vix_monitor.get_vix_snapshot()", _vix)

def _opts():
    from options_flow import get_options_score
    score, sig = get_options_score("AAPL", current_price=170)
    return f"score={score}, signals={sig[:2] if sig else []}"
check("options_flow.get_options_score(AAPL)", _opts)

# ============================================================
# 3. 경제 캘린더
# ============================================================
def _econ():
    from economic_calendar import EconomicCalendar
    ec = EconomicCalendar()
    evs = ec.get_todays_events()
    safe = ec.is_safe_to_trade()
    return f"today={[e.name for e in evs]}, safe={safe[0]}"
check("economic_calendar (ET 기반)", _econ)

# ============================================================
# 4. 실적 캘린더 / PEAD
# ============================================================
def _earn_cal():
    from earnings_calendar import EarningsCalendar
    ec = EarningsCalendar()
    # get_recent_earnings 있는지
    has_method = hasattr(ec, 'get_recent_earnings')
    upcoming = ec.get_upcoming_earnings("AAPL") if hasattr(ec, 'get_upcoming_earnings') else None
    return f"has_get_recent_earnings={has_method}, upcoming={upcoming}"
check("earnings_calendar.EarningsCalendar()", _earn_cal)

def _earn_anal():
    # earnings_analyzer 모듈 자체가 있는지
    try:
        import earnings_analyzer
        ea = earnings_analyzer.get_earnings_analyzer() if hasattr(earnings_analyzer, 'get_earnings_analyzer') else None
        has_surprise = hasattr(ea, 'get_recent_surprise') if ea else False
        return f"module=OK, get_earnings_analyzer={ea is not None}, has_get_recent_surprise={has_surprise}"
    except ImportError:
        return None
check("earnings_analyzer module", _earn_anal)

# ============================================================
# 5. 뉴스 분석기
# ============================================================
def _news():
    from news_analyzer import get_news_analyzer
    result = get_news_analyzer().analyze("AAPL")
    return f"score={result.sentiment_score}, articles={len(result.articles) if hasattr(result,'articles') else '?'}"
check("news_analyzer.analyze(AAPL)", _news)

# ============================================================
# 6. 인사이더 트래커
# ============================================================
def _insider():
    from insider_tracker import get_insider_tracker
    result = get_insider_tracker().analyze("AAPL")
    return f"sentiment={result.insider_sentiment}, net={result.insider_net_value}"
check("insider_tracker.analyze(AAPL)", _insider)

# ============================================================
# 7. 섹터 로테이터
# ============================================================
def _sector():
    from sector_rotator import get_sector_rotator
    sr = get_sector_rotator()
    rankings = sr.analyze()
    top3 = [r.sector for r in rankings[:3]]
    sym_etf = sr.get_sector_for_stock("AAPL")
    return f"top3={top3}, AAPL_sector={sym_etf}"
check("sector_rotator.analyze() + get_sector_for_stock", _sector)

# ============================================================
# 8. 인사이더/Short Squeeze
# ============================================================
def _squeeze():
    from short_squeeze import ShortSqueezeMonitor
    import pandas as pd, numpy as np
    df = pd.DataFrame({'Close': np.random.randn(20).cumsum()+100, 'Volume': [1e6]*20,
                       'High': np.random.randn(20).cumsum()+102, 'Low': np.random.randn(20).cumsum()+98})
    result = ShortSqueezeMonitor().analyze(df, symbol="PLTR")
    return f"score={result.get('score')}, signals={result.get('signals',[])[:]}"
check("short_squeeze.ShortSqueezeMonitor(PLTR)", _squeeze)

# ============================================================
# 9. Risk Manager - day_start_equity
# ============================================================
def _rm():
    from risk_manager import RiskManager
    rm = RiskManager(700)
    has_attr = hasattr(rm, 'day_start_equity')
    val = getattr(rm, 'day_start_equity', 'NOT_FOUND')
    return f"has_day_start_equity={has_attr}, value={val}"
check("risk_manager.day_start_equity", _rm)

# ============================================================
# 10. Emergency Stop - check_daily_loss
# ============================================================
def _estop():
    from emergency_stop import EmergencyStop
    es = EmergencyStop()
    r = es.check_daily_loss(700, 679)  # 3% 손실 테스트
    return f"check_daily_loss(700→679)={r} (expect True if >3% loss)"
check("emergency_stop.check_daily_loss()", _estop)

# ============================================================
# 11. Auto Tuner
# ============================================================
def _tuner():
    import auto_tuner
    has_fn = hasattr(auto_tuner, 'run_auto_tune')
    return f"run_auto_tune exists={has_fn}"
check("auto_tuner.run_auto_tune", _tuner)

# ============================================================
# 12. Fed Watch → strategy 연결
# ============================================================
def _fed():
    from fed_watch import get_fed_signal
    sig = get_fed_signal()
    return f"direction={sig.rate_direction}, score={sig.fed_score}, signal={sig.signal}"
check("fed_watch.get_fed_signal()", _fed)

# ============================================================
# 13. HMM Regime → strategy 연결
# ============================================================
def _hmm():
    from hidden_markov_regime import get_regime_detector
    rd = get_regime_detector()
    result = rd.get_current_regime()
    return f"regime={result.regime if hasattr(result,'regime') else result}"
check("hidden_markov_regime.get_current_regime()", _hmm)

# ============================================================
# 14. Geopolitical → 실제 데이터 or 하드코딩?
# ============================================================
def _geo():
    from geopolitical import get_geopolitical_analyzer
    ga = get_geopolitical_analyzer()
    result = ga.analyze()
    return f"level={result.level if hasattr(result,'level') else result}, type={type(result).__name__}"
check("geopolitical.analyze()", _geo)

# ============================================================
# 15. Intermarket → 실제 데이터 or 하드코딩?
# ============================================================
def _inter():
    from intermarket import get_intermarket_analyzer
    ia = get_intermarket_analyzer()
    result = ia.analyze()
    return f"score={getattr(result,'score',None)}, signal={getattr(result,'signal',result)}"
check("intermarket.analyze()", _inter)

# ============================================================
# 16. Phase 6 모듈들
# ============================================================
def _journal():
    from trade_journal import get_trade_journal
    tj = get_trade_journal()
    return f"generate_daily_entry={hasattr(tj, 'generate_daily_entry')}"
check("trade_journal.get_trade_journal()", _journal)

def _reporter():
    from reporter import get_reporter
    r = get_reporter()
    return f"send_daily_summary={hasattr(r, 'send_daily_summary')}"
check("reporter.get_reporter()", _reporter)

def _drawdown():
    from drawdown_controller import get_drawdown_controller
    dc = get_drawdown_controller(700)
    return f"is_halted={dc.is_halted()}"
check("drawdown_controller.is_halted()", _drawdown)

def _dynamic():
    from dynamic_scaling import get_scaler
    s = get_scaler(700)
    tier = s.get_tier() if hasattr(s, 'get_tier') else "no_get_tier"
    return f"tier={tier}"
check("dynamic_scaling.get_scaler()", _dynamic)

def _kelly():
    from kelly_criterion import get_kelly_fraction
    kf = get_kelly_fraction("AAPL")
    return f"kelly_fraction={kf}"
check("kelly_criterion.get_kelly_fraction(AAPL)", _kelly)

def _position_sizer():
    from position_sizer import calculate_optimal_size
    qty = calculate_optimal_size("AAPL", 5, 0.25, 0.5)
    return f"optimal_qty={qty}"
check("position_sizer.calculate_optimal_size()", _position_sizer)

# ============================================================
# 출력
# ============================================================
print("\n" + "="*80)
print("전체 시스템 연결 상태 검증 결과")
print("="*80)

ok_count = sum(1 for _, s, _ in results if s.startswith("✅"))
warn_count = sum(1 for _, s, _ in results if s.startswith("⚠️"))
err_count = sum(1 for _, s, _ in results if s.startswith("❌"))

for name, status, detail in results:
    print(f"\n{status} [{name}]")
    print(f"   → {detail}")

print("\n" + "="*80)
print(f"결과: ✅ {ok_count}개 정상 | ⚠️ {warn_count}개 비어있음 | ❌ {err_count}개 오류")
print("="*80)
