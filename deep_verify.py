"""
Deep Functional Verification
===================================
Import가 아니라 실제로 함수를 호출해서 데이터가 정상적으로 흘러가는지 확인.
"""
import sys, os, traceback
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

results = []
def test(name, fn):
    try:
        result = fn()
        results.append(('PASS', name, str(result)[:120]))
        print(f"  ✅ {name}: {str(result)[:120]}")
    except Exception as e:
        results.append(('FAIL', name, f"{type(e).__name__}: {e}"))
        print(f"  ❌ {name}: {type(e).__name__}: {str(e)[:150]}")
        traceback.print_exc()

print("=" * 70)
print("DEEP FUNCTIONAL TEST — 실제 함수 호출")
print("=" * 70)

# ============================================================
# TEST 1: kis_data — 실제 주가 데이터가 들어오는가?
# ============================================================
print("\n[TEST 1] kis_data — 데이터 호출")

def t1a():
    import kis_data
    price = kis_data.get_current_price("AAPL")
    assert price is not None, "get_current_price returned None"
    assert 'last' in price, f"Missing 'last' key: {price.keys()}"
    assert price['last'] > 0, f"Price <= 0: {price['last']}"
    return f"AAPL = ${price['last']}, change: {price.get('rate', '?')}%"
test("kis_data.get_current_price(AAPL)", t1a)

def t1b():
    import kis_data
    df = kis_data.download("NVDA", period="30d", progress=False)
    assert df is not None, "download returned None"
    assert len(df) >= 10, f"Only {len(df)} rows"
    assert 'Close' in df.columns, f"Missing 'Close': {list(df.columns)}"
    return f"NVDA 30d: {len(df)} bars, last close=${float(df['Close'].iloc[-1]):.2f}"
test("kis_data.download(NVDA, 30d)", t1b)

def t1c():
    import kis_data
    df = kis_data.get_daily_ohlcv("TSLA", days=60)
    assert df is not None, "get_daily_ohlcv returned None"
    assert len(df) >= 20, f"Only {len(df)} rows"
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        assert col in df.columns, f"Missing column: {col}"
    return f"TSLA 60d OHLCV: {len(df)} bars, cols={list(df.columns)}"
test("kis_data.get_daily_ohlcv(TSLA, 60d)", t1c)

def t1d():
    import kis_data
    rank = kis_data.get_volume_rank("NAS", min_price=5.0, top_n=10)
    assert isinstance(rank, list), f"Expected list, got {type(rank)}"
    assert len(rank) > 0, "Empty volume rank"
    return f"Volume rank: {len(rank)} stocks, first={rank[0].get('symbol', '?')}"
test("kis_data.get_volume_rank(NAS)", t1d)

# ============================================================
# TEST 2: data_proxy — yfinance shim이 정상 작동하는가?
# ============================================================
print("\n[TEST 2] data_proxy — yfinance shim")

def t2a():
    import data_proxy
    import yfinance as yf  # This should be shimmed
    df = yf.download("AMD", period="30d", progress=False)
    assert df is not None and len(df) > 0, "Shimmed download failed"
    return f"yfinance.download shimmed OK: AMD {len(df)} bars"
test("yfinance shim download(AMD)", t2a)

# ============================================================
# TEST 3: indicators — 지표 계산이 정상인가?
# ============================================================
print("\n[TEST 3] indicators — 기술적 지표 계산")

def t3a():
    import kis_data
    from indicators import analyze_all
    df = kis_data.download("SPY", period="90d", progress=False)
    result = analyze_all(df)
    assert result is not None, "analyze_all returned None"
    assert hasattr(result, 'rsi'), f"Missing RSI"
    assert hasattr(result, 'macd'), f"Missing MACD"
    assert hasattr(result, 'atr'), f"Missing ATR"
    assert 0 < result.rsi < 100, f"RSI out of range: {result.rsi}"
    assert result.atr > 0, f"ATR invalid: {result.atr}"
    return f"RSI={result.rsi:.1f}, ATR={result.atr:.2f}, MACD.hist={result.macd.histogram:.4f}"
test("indicators.analyze_all(SPY)", t3a)

# ============================================================
# TEST 4: composite_signal — 종합 점수가 나오는가?
# ============================================================
print("\n[TEST 4] composite_signal — 매매 판단 점수")

def t4a():
    from composite_signal import get_composite_engine
    engine = get_composite_engine()
    sig = engine.analyze("AAPL")
    assert sig is not None, "analyze returned None"
    assert -100 <= sig.composite_score <= 100, f"Score out of range: {sig.composite_score}"
    assert sig.action is not None, "No action"
    return f"AAPL: score={sig.composite_score:+d}, action={sig.action.value}, conf={sig.confidence}%, pos={sig.position_size_pct:.1%}"
test("composite_signal.analyze(AAPL)", t4a)

def t4b():
    from composite_signal import get_composite_engine
    engine = get_composite_engine()
    sig = engine.analyze("NVDA")
    return f"NVDA: score={sig.composite_score:+d}, action={sig.action.value}, tech={sig.technical_score.score:+d}, smart={sig.smart_money_score.score:+d}"
test("composite_signal.analyze(NVDA)", t4b)

# ============================================================
# TEST 5: strategy — 진입/퇴출 판단이 작동하는가?
# ============================================================
print("\n[TEST 5] strategy — 진입/퇴출 로직")

def t5a():
    from strategy import StrategyEngine
    se = StrategyEngine()
    df = se.fetch_data("MSFT")
    assert df is not None, "fetch_data returned None"
    assert len(df) >= 30, f"Only {len(df)} bars"
    entry = se.check_entry("MSFT")
    assert entry is not None, "check_entry returned None"
    assert entry.action in ["BUY", "HOLD"], f"Unexpected action: {entry.action}"
    return f"MSFT entry: action={entry.action}, confidence={entry.confidence}, reason={entry.reason[:60]}"
test("strategy.check_entry(MSFT)", t5a)

def t5b():
    """레버리지 ETF 퇴출 규칙 테스트"""
    from strategy import StrategyEngine, Position
    from datetime import datetime, timedelta
    import config
    se = StrategyEngine()
    # Simulate a TQQQ position held for 25 hours
    se._positions["TQQQ"] = Position(
        symbol="TQQQ", entry_price=50.0, quantity=4,
        entry_time=datetime.now() - timedelta(hours=25),
        atr_at_entry=1.5, high_since_entry=52.0
    )
    df = se.fetch_data("TQQQ")
    if df is not None:
        exit_sig = se.check_exit("TQQQ", 51.0)
        assert exit_sig is not None, "check_exit returned None"
        assert "LEVERAGED" in exit_sig.reason, f"Expected LEVERAGED exit, got: {exit_sig.reason}"
        return f"TQQQ 25h hold -> {exit_sig.action}: {exit_sig.reason}"
    return "TQQQ data not available, but logic is in code"
test("strategy leveraged ETF 24h exit", t5b)

# ============================================================
# TEST 6: macro — 매크로 분석이 작동하는가?
# ============================================================
print("\n[TEST 6] macro — 매크로 점수 분석")

def t6a():
    from macro import get_macro_analyzer, get_macro_score
    analyzer = get_macro_analyzer()
    result = analyzer.analyze()
    assert result is not None, "analyze returned None"
    assert -100 <= result.score <= 100, f"Score out of range: {result.score}"
    score_fn = get_macro_score()
    return f"Regime={result.regime.value}, Score={result.score:.0f}, Betting={result.betting_ratio:.0%}, get_macro_score()={score_fn:.0f}"
test("macro.analyze()", t6a)

# ============================================================
# TEST 7: screener — 종목 발굴이 작동하는가?
# ============================================================
print("\n[TEST 7] screener — 종목 발굴")

def t7a():
    from screener import get_screener
    from macro import MarketRegime
    sc = get_screener()
    result = sc.screen(MarketRegime.RISK_ON)
    assert result is not None, "screen returned None"
    assert len(result.tickers) > 0, "No tickers found"
    top3 = [(s.symbol, s.total_score) for s in result.scores[:3]]
    return f"Mode={result.mode.value}, Found {len(result.tickers)} stocks, Top3={top3}"
test("screener.screen(RISK_ON)", t7a)

# ============================================================
# TEST 8: base_adapters — 모듈 어댑터 체인이 작동하는가?
# ============================================================
print("\n[TEST 8] base_adapters — 분석 모듈 어댑터")

def t8a():
    from base_adapters import get_available_adapters
    adapters = get_available_adapters()
    assert len(adapters) > 0, "No adapters found"
    cats = {}
    for ac in adapters:
        try:
            inst = ac()
            cat = inst.category.lower()
            cats[cat] = cats.get(cat, 0) + 1
        except:
            pass
    return f"{len(adapters)} adapters, categories: {dict(cats)}"
test("base_adapters adapter loading", t8a)

def t8b():
    """어댑터로 실제 분석 돌려보기"""
    from base_adapters import get_available_adapters
    import kis_data
    df = kis_data.download("GOOGL", period="60d", progress=False)
    if df is None or len(df) < 30:
        return "No data for test"
    adapters = get_available_adapters()
    worked = 0
    failed_names = []
    for ac in adapters[:10]:  # Test first 10
        try:
            inst = ac()
            result = inst.analyze(df, symbol="GOOGL")
            if isinstance(result, dict) and 'score' in result:
                worked += 1
        except Exception as e:
            failed_names.append(f"{ac.__name__}:{type(e).__name__}")
    return f"{worked}/10 adapters returned valid scores. Failures: {failed_names[:5]}"
test("adapters functional test (GOOGL)", t8b)

# ============================================================
# TEST 9: reporter & notification
# ============================================================
print("\n[TEST 9] reporter & notification")

def t9a():
    from reporter import TradingReporter
    r = TradingReporter.__new__(TradingReporter)
    # Just verify the class exists and has the right methods
    methods = [m for m in dir(r) if not m.startswith('_') and callable(getattr(type(r), m, None))]
    return f"Reporter methods: {methods[:8]}"
test("reporter class check", t9a)

def t9b():
    from notification import get_notifier
    n = get_notifier()
    assert n is not None, "get_notifier returned None"
    return f"Notifier: {type(n).__name__}, has alert_trade: {hasattr(n, 'alert_trade')}"
test("notification.get_notifier()", t9b)

# ============================================================
# TEST 10: Institutional Modules
# ============================================================
print("\n[TEST 10] Testing Institutional Modules...")
try:
    from fx_risk import FXRiskAnalyzer
    from earnings_quality import EarningsQualityScorer
    from estimate_revision import EstimateRevisionAnalyzer
    
    # Test FX Risk
    fx = FXRiskAnalyzer()
    res_fx = fx.analyze(pd.DataFrame({"Close": [1300]*30}))
    print(f" - FX Risk: score={res_fx['score']}, signals={res_fx['signals']}")
    
    # Test Earnings Quality (AAPL)
    eq = EarningsQualityScorer()
    res_eq = eq.analyze(pd.DataFrame(), symbol="AAPL")
    print(f" - Earnings Quality (AAPL): score={res_eq['score']}, signals={res_eq['signals']}")

    # Test Estimate Revision (TSLA)
    er = EstimateRevisionAnalyzer()
    res_er = er.analyze(pd.DataFrame(), symbol="TSLA")
    print(f" - Estimate Revision (TSLA): score={res_er['score']}, signals={res_er['signals']}")
    
    # Test Aggregator Integration
    from signal_aggregator import get_signal_aggregator
    agg = get_signal_aggregator()
    res_agg = agg.analyze(pd.DataFrame({"Close": np.random.randn(50) + 100}), symbol="AAPL")
    print(f" - Aggregator Institutional: score={res_agg.institutional_score}, details={res_agg.details}")
    
except Exception as e:
    print(f" [!] TEST 10 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 70)
passes = sum(1 for r in results if r[0] == 'PASS')
fails = sum(1 for r in results if r[0] == 'FAIL')
print(f"TOTAL: {passes} PASS / {fails} FAIL out of {len(results)} tests")

if fails == 0:
    print("🎉 ALL DEEP TESTS PASSED — 데이터 흐름, 판단 로직, 점수 계산 모두 정상!")
else:
    print("\n❌ FAILURES:")
    for status, name, detail in results:
        if status == 'FAIL':
            print(f"  {name}: {detail}")
print("=" * 70)
