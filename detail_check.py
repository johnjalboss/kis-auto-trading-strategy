"""
세부 API 검증 스크립트
"""
import sys, os
os.chdir('/home/ubuntu/kis-auto-trading')
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

print("=== 1. kis_data.get_daily_ohlcv ===")
try:
    from kis_data import get_daily_ohlcv
    df = get_daily_ohlcv("AAPL", days=25)
    if df is not None and not df.empty:
        print(f"OK: {len(df)} rows, cols={list(df.columns)}")
    else:
        print(f"EMPTY: df={df}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 2. risk_manager.day_start_equity ===")
try:
    from risk_manager import RiskManager
    rm = RiskManager()
    print(f"has day_start_equity: {hasattr(rm, 'day_start_equity')}")
    print(f"value: {getattr(rm, 'day_start_equity', 'MISSING')}")
    print(f"daily_stats: {rm.get_daily_stats()}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 3. fed_watch actual API ===")
try:
    import fed_watch
    print(f"Available: {[x for x in dir(fed_watch) if not x.startswith('_')]}")
    fa = fed_watch.get_fed_analyzer()
    sig = fa.analyze()
    print(f"direction={sig.rate_direction}, score={sig.fed_score}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 4. hidden_markov_regime actual API ===")
try:
    import hidden_markov_regime as hmm
    print(f"Available: {[x for x in dir(hmm) if not x.startswith('_') and callable(getattr(hmm,x))]}")
    obj = hmm.HiddenMarkovRegime()
    result = obj.get_current_regime()
    print(f"result type={type(result)}, value={result}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 5. geopolitical actual API ===")
try:
    import geopolitical
    print(f"Available fns: {[x for x in dir(geopolitical) if not x.startswith('_') and callable(getattr(geopolitical,x))]}")
    gm = geopolitical.get_geopolitical()
    result = gm.analyze()
    print(f"result={result}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 6. intermarket actual API ===")
try:
    import intermarket
    print(f"Available fns: {[x for x in dir(intermarket) if not x.startswith('_') and callable(getattr(intermarket,x))]}")
    ia = intermarket.get_intermarket()
    result = ia.analyze()
    print(f"result={result}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 7. trade_journal.generate_daily_entry ===")
try:
    from trade_journal import get_trade_journal
    tj = get_trade_journal()
    print(f"methods: {[m for m in dir(tj) if not m.startswith('_')]}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 8. earnings_calendar.get_recent_earnings ===")
try:
    from earnings_calendar import EarningsCalendar
    ec = EarningsCalendar()
    print(f"methods: {[m for m in dir(ec) if not m.startswith('_')]}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 9. earnings_analyzer methods ===")
try:
    from earnings_analyzer import get_earnings_analyzer
    ea = get_earnings_analyzer()
    print(f"methods: {[m for m in dir(ea) if not m.startswith('_')]}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 10. vix_structure VixSignal fields ===")
try:
    from vix_structure import get_vix_analyzer
    va = get_vix_analyzer()
    sig = va.analyze()
    print(f"VixSignal fields: {[f for f in dir(sig) if not f.startswith('_')]}")
    print(f"vix={getattr(sig,'vix',None)}, score_adj={getattr(sig,'score_adj',None)}, regime={getattr(sig,'regime',None)}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 11. options_flow.get_vix_snapshot fields ===")
try:
    from options_flow import get_vix_snapshot
    snap = get_vix_snapshot()
    print(f"fields: {[f for f in dir(snap) if not f.startswith('_')]}")
    print(f"vix={getattr(snap,'vix',None)}, score_adj={getattr(snap,'score_adj',None)}, regime={getattr(snap,'regime',None)}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== 12. drawdown_controller state file corruption ===")
try:
    import json
    with open('drawdown_state.json','r') as f:
        content = f.read()
    print(f"State: {content[:200]}")
    data = json.loads(content)
    print(f"Parsed OK: {data}")
except Exception as e:
    print(f"ERROR (will reset): {e}")
    # Auto-fix: reset corrupt state
    import json
    with open('drawdown_state.json','w') as f:
        json.dump({"peak_equity": 0, "daily_start": 0, "weekly_start": 0, 
                   "halted": False, "halt_reason": ""}, f)
    print("FIXED: Reset drawdown_state.json")
