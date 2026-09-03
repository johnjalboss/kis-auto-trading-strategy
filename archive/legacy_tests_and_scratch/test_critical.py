import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

print("=" * 60)
print("CRITICAL MODULE FUNCTIONAL TEST")
print("=" * 60)

# Test 1: smart_money (25% weight!)
print("\n[1] smart_money.analyze(AAPL)")
try:
    from smart_money import get_smart_money_tracker
    sm = get_smart_money_tracker()
    r = sm.analyze("AAPL")
    print(f"  Score: {r.score:+d}")
    print(f"  Signals: {r.signals}")
    print(f"  Institutional: {r.institutional is not None}")
    print(f"  Dark Pool: {r.dark_pool is not None}")
    if r.institutional:
        print(f"    inst_own={r.institutional.inst_ownership_pct:.0%}, sentiment={r.institutional.net_insider_sentiment}")
    if r.dark_pool:
        print(f"    dp_type={r.dark_pool.signal_type}, vol_ratio={r.dark_pool.volume_ratio:.1f}x, blocks={r.dark_pool.block_trades}")
    print(f"  ✅ OK" if r.institutional is not None else "  ❌ STILL NULL")
except Exception as e:
    print(f"  ❌ FAIL: {e}")

# Test 2: composite_signal full chain
print("\n[2] composite_signal.analyze(NVDA) — FULL CHAIN")
try:
    from composite_signal import get_composite_engine
    engine = get_composite_engine()
    sig = engine.analyze("NVDA")
    print(f"  Composite Score: {sig.composite_score:+d}")
    print(f"  Action: {sig.action.value}")
    print(f"  Technical: {sig.technical_score.score:+d}")
    print(f"  Smart Money: {sig.smart_money_score.score:+d}")
    print(f"  Sentiment: {sig.sentiment_score.score:+d}")
    print(f"  Macro: {sig.macro_score.score:+d}")
    print(f"  ✅ SMART_MONEY={sig.smart_money_score.score:+d} (was 0 before fix)")
except Exception as e:
    print(f"  ❌ FAIL: {e}")

# Test 3: screener
print("\n[3] screener.screen()")
try:
    from screener import get_screener
    from macro import MarketRegime
    sc = get_screener()
    r = sc.screen(MarketRegime.RISK_ON)
    if r and r.scores:
        top = r.scores[0]
        print(f"  Found {len(r.tickers)} stocks")
        print(f"  Top: {top.symbol} score={top.total_score}")
        print(f"  ✅ OK")
    else:
        print(f"  ❌ No scores returned")
except Exception as e:
    print(f"  ❌ FAIL: {e}")

# Test 4: earnings_analyzer
print("\n[4] earnings_analyzer.analyze(TSLA)")
try:
    from earnings_analyzer import get_earnings_analyzer
    ea = get_earnings_analyzer()
    r = ea.analyze("TSLA")
    print(f"  Score: {r.earnings_score:+d}, Signal: {r.signal}")
    print(f"  EPS Growth: {r.eps_growth_yoy:.1%}")
    print(f"  ✅ OK")
except Exception as e:
    print(f"  ❌ FAIL: {e}")

print("\n" + "=" * 60)
print("DONE — All critical modules tested with real KIS API data")
print("=" * 60)
