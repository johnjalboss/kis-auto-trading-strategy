"""Test all yf.Ticker modules — safe version that catches any return type"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 60)
print("yf.Ticker SHIM VERIFICATION — ALL MODULES")
print("=" * 60)

results = []

def test(name, fn):
    try:
        r = fn()
        results.append(('PASS', name))
        print(f"  ✅ {name}")
    except Exception as e:
        results.append(('FAIL', name, str(e)[:120]))
        print(f"  ❌ {name}: {type(e).__name__}: {str(e)[:120]}")

# [A] Ticker shim basic
print("\n[A] TICKER SHIM BASIC")
def t0():
    import yfinance as yf
    t = yf.Ticker("AAPL")
    info = t.info
    hist = t.history()
    print(f"      info keys={len(info)}, price=${info.get('regularMarketPrice',0)}, hist bars={len(hist)}")
    assert len(info) > 5 and len(hist) > 0
test("yf.Ticker proxy", t0)

# [B] All yf.Ticker-using modules
print("\n[B] yf.Ticker MODULES — import + analyze")

modules_to_test = [
    ("earnings_calendar", lambda: __import__("earnings_calendar")),
    ("event_calendar", lambda: __import__("event_calendar")),
    ("options_flow", lambda: __import__("options_flow")),
    ("options_metrics", lambda: __import__("options_metrics")),
    ("insider_tracker", lambda: __import__("insider_tracker")),
    ("news_analyzer", lambda: __import__("news_analyzer")),
    ("factor_analysis", lambda: __import__("factor_analysis")),
    ("fundamental_analyzer", lambda: __import__("fundamental_analyzer")),
    ("sector_rotation", lambda: __import__("sector_rotation")),
    ("sector_rotator", lambda: __import__("sector_rotator")),
    ("squeeze_detector", lambda: __import__("squeeze_detector")),
    ("realtime_monitor", lambda: __import__("realtime_monitor")),
    ("market_psychology", lambda: __import__("market_psychology")),
    ("fed_watch", lambda: __import__("fed_watch")),
    ("crypto_sentiment", lambda: __import__("crypto_sentiment")),
    ("oil_impact", lambda: __import__("oil_impact")),
    ("liquidity_analyzer", lambda: __import__("liquidity_analyzer")),
    ("liquidity_filter", lambda: __import__("liquidity_filter")),
]

for name, fn in modules_to_test:
    test(f"import {name}", fn)

# [C] Functional calls on critical modules
print("\n[C] FUNCTIONAL CALLS")

def t_smart():
    from smart_money import get_smart_money_tracker
    r = get_smart_money_tracker().analyze("AAPL")
    print(f"      score={r.score:+d}, inst={r.institutional is not None}, dp={r.dark_pool is not None}")
    assert r.institutional is not None
test("smart_money.analyze(AAPL)", t_smart)

def t_earn():
    from earnings_analyzer import get_earnings_analyzer
    r = get_earnings_analyzer().analyze("NVDA")
    print(f"      earnings_score={r.earnings_score:+d}, signal={r.signal}")
test("earnings_analyzer.analyze(NVDA)", t_earn)

def t_sent():
    from sentiment import get_sentiment_analyzer
    r = get_sentiment_analyzer().analyze("TSLA")
    print(f"      score={r.score:+d}, signal={r.signal}")
test("sentiment.analyze(TSLA)", t_sent)

def t_comp():
    from composite_signal import get_composite_engine
    r = get_composite_engine().analyze("AMD")
    print(f"      composite={r.composite_score:+d}, action={r.action.value}")
    print(f"      tech={r.technical_score.score:+d}, sm={r.smart_money_score.score:+d}, sent={r.sentiment_score.score:+d}, macro={r.macro_score.score:+d}")
test("composite_signal.analyze(AMD) — FULL CHAIN", t_comp)

# Summary
print("\n" + "=" * 60)
p = sum(1 for s in results if s[0] == 'PASS')
f = sum(1 for s in results if s[0] == 'FAIL')
print(f"TOTAL: {p} PASS / {f} FAIL out of {len(results)}")
if f == 0:
    print("🎉 ALL yf.Ticker MODULES WORKING!")
else:
    print("\nFAILURES:")
    for r in results:
        if r[0] == 'FAIL':
            print(f"  ❌ {r[1]}: {r[2] if len(r) > 2 else ''}")
print("=" * 60)
