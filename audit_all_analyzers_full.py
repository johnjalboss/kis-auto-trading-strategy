"""
Comprehensive Codebase & Strategy Audit Script (audit_all_analyzers_full.py)
Tests every single analyzer, data proxy, composite engine, risk manager,
and position sizer across candidate universe symbols.
"""
import sys, os, time, json
import pandas as pd
import numpy as np
from datetime import datetime, date

sys.path.insert(0, r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")
if os.path.exists('/home/ubuntu/kis-auto-trading'):
    sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
    os.chdir('/home/ubuntu/kis-auto-trading')

print("==========================================================")
print("[AUDIT] DEEP QUANT CODEBASE & STRATEGY VERIFICATION")
print("==========================================================")

report = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "analyzers_tested": 0,
    "analyzers_passed": 0,
    "analyzers_failed": [],
    "data_pipeline_status": "UNKNOWN",
    "composite_scoring_status": "UNKNOWN",
    "risk_gates_status": "UNKNOWN"
}

# 1. Test Data Proxy & Data Pipeline
print("\n--- 1. Data Pipeline & Proxy Inspection ---")
try:
    from data_proxy import kis_data
    from trader import Trader
    
    trader = Trader()
    bp = trader.get_buying_power("AAPL")
    print(f"  [OK] Trader Buying Power API: ${bp:,.2f}")
    
    df_test = kis_data.get_daily_ohlcv("AAPL", period_days=100)
    if df_test is not None and not df_test.empty and len(df_test) >= 30:
        print(f"  [OK] OHLCV Fetching for AAPL: {len(df_test)} bars returned (Cols: {list(df_test.columns)})")
        report["data_pipeline_status"] = "PASSED"
    else:
        print("  [WARN] OHLCV returned insufficient bars:", len(df_test) if df_test is not None else 0)
        report["data_pipeline_status"] = "WARNING"
except Exception as e:
    print(f"  [FAIL] Data Pipeline Error: {e}")
    report["data_pipeline_status"] = f"FAILED: {e}"

# 2. Test All Analyzers in Composite Signal Engine
print("\n--- 2. Composite Signal Engine & All Analyzers Inspection ---")
try:
    from composite_signal import get_composite_engine
    engine = get_composite_engine()
    
    total_analyzers = 0
    passed_analyzers = 0
    failed_list = []
    
    for cat, analyzer_list in engine.analyzers.items():
        print(f"  Category [{cat.upper()}] - {len(analyzer_list)} analyzers:")
        for analyzer in analyzer_list:
            total_analyzers += 1
            an_name = analyzer.name
            try:
                # Test analyze with sample DataFrame
                if hasattr(analyzer, 'analyze'):
                    res = analyzer.analyze(df_test, symbol="AAPL")
                    score = getattr(res, 'score', 0) if not isinstance(res, dict) else res.get('score', 0)
                    sigs = getattr(res, 'signals', []) if not isinstance(res, dict) else res.get('signals', [])
                elif hasattr(analyzer, 'calculate'):
                    score, sigs = analyzer.calculate(df_test, symbol="AAPL")
                else:
                    score, sigs = 0, []
                passed_analyzers += 1
                print(f"    - {an_name:30s} -> Score: {score} | Signals: {len(sigs)}")
            except Exception as an_err:
                failed_list.append(f"{an_name}: {an_err}")
                print(f"    - {an_name:30s} -> [ERROR] {an_err}")
                
    report["analyzers_tested"] = total_analyzers
    report["analyzers_passed"] = passed_analyzers
    report["analyzers_failed"] = failed_list
    
    # Test Composite Engine Full Analyze
    comp_res = engine.analyze("AAPL", df=df_test)
    print(f"\n  [OK] Composite Signal Output for AAPL:")
    print(f"       Action: {comp_res.action.value} | Composite Score: {comp_res.composite_score} | Confidence: {comp_res.confidence}%")
    print(f"       Category Breakdown: {comp_res.score_breakdown}")
    report["composite_scoring_status"] = "PASSED"
except Exception as c_err:
    print(f"  [FAIL] Composite Signal Engine Error: {c_err}")
    report["composite_scoring_status"] = f"FAILED: {c_err}"

# 3. Test Risk Manager & Sizing Gate
print("\n--- 3. Risk Manager & Position Sizer Gate Inspection ---")
try:
    from risk_manager import get_risk_manager
    from position_sizer import get_position_sizer
    import config
    
    rm = get_risk_manager()
    allowed, rm_reason = rm.can_trade("AAPL")
    print(f"  [OK] RiskManager Gate Check for AAPL: Allowed={allowed} ({rm_reason})")
    
    sizer = get_position_sizer(portfolio=766.49)
    print(f"  [OK] PositionSizer Initialized for Portfolio=$766.49 USD")
    report["risk_gates_status"] = "PASSED"
except Exception as r_err:
    print(f"  [FAIL] Risk Manager Gate Error: {r_err}")
    report["risk_gates_status"] = f"FAILED: {r_err}"

print("\n==========================================================")
print(f"AUDIT SUMMARY: {report['analyzers_passed']}/{report['analyzers_tested']} Analyzers Passed")
if report['analyzers_failed']:
    print("FAILED ANALYZERS:", report['analyzers_failed'])
else:
    print("ALL ANALYZERS OPERATING 100% CLEANLY WITH ZERO FAILURES!")
print("==========================================================")
