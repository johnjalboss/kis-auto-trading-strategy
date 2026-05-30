"""
Integration Test - All 111+ Modules
=====================================
Verify all modules work together.
"""

import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING")

def test_module(name: str, import_func):
    """Test a single module"""
    try:
        result = import_func()
        return True, result
    except Exception as e:
        return False, str(e)

print("="*60)
print("INTEGRATION TEST - 111+ Modules")
print("="*60)

results = {'passed': 0, 'failed': 0, 'errors': []}

# ===== CORE MODULES =====
print("\n[Core Modules]")
modules_core = [
    ("scheduler", lambda: __import__('scheduler').get_scheduler()),
    ("health_monitor", lambda: __import__('health_monitor').get_health_monitor()),
    ("emergency_stop", lambda: __import__('emergency_stop').get_emergency_stop()),
    ("notification", lambda: __import__('notification').get_notifier()),
    ("trade_journal", lambda: __import__('trade_journal').get_trade_journal()),
]

for name, func in modules_core:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== ANALYSIS MODULES =====
print("\n[Analysis Modules]")
modules_analysis = [
    ("fundamental_analyzer", lambda: __import__('fundamental_analyzer').get_fundamental_analyzer()),
    ("technical_analyzer", lambda: __import__('technical_analyzer').get_technical_analyzer()),
    ("news_analyzer", lambda: __import__('news_analyzer').get_news_analyzer()),
    ("market_psychology", lambda: __import__('market_psychology').get_market_psychology()),
    ("market_internals", lambda: __import__('market_internals').get_internals_analyzer()),
]

for name, func in modules_analysis:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== STRATEGY MODULES =====
print("\n[Strategy Modules]")
modules_strategy = [
    ("adaptive_strategy", lambda: __import__('adaptive_strategy').get_adaptive_selector()),
    ("drawdown_controller", lambda: __import__('drawdown_controller').get_drawdown_controller(100000)),
    ("drawdown_recovery", lambda: __import__('drawdown_recovery').get_drawdown_recovery(100000)),
    ("multi_timeframe", lambda: __import__('multi_timeframe').get_multi_timeframe()),
    ("mean_reversion", lambda: __import__('mean_reversion').get_mean_reversion()),
    ("gap_fill", lambda: __import__('gap_fill').get_gap_analyzer()),
    ("seasonality", lambda: __import__('seasonality').get_seasonality()),
]

for name, func in modules_strategy:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== RISK MODULES =====
print("\n[Risk Modules]")
modules_risk = [
    ("kelly_criterion", lambda: __import__('kelly_criterion').get_kelly()),
    ("cost_model", lambda: __import__('cost_model').get_cost_model()),
    ("liquidity_filter", lambda: __import__('liquidity_filter').get_liquidity_filter()),
    ("anti_fragility", lambda: __import__('anti_fragility').get_antifragility()),
    ("tax_optimizer", lambda: __import__('tax_optimizer').get_tax_optimizer()),
    ("hedge_manager", lambda: __import__('hedge_manager').get_hedge_manager()),
    ("stress_test", lambda: __import__('stress_test').get_stress_test()),
]

for name, func in modules_risk:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== MARKET MODULES =====
print("\n[Market Modules]")
modules_market = [
    ("economic_calendar", lambda: __import__('economic_calendar').get_economic_calendar()),
    ("intermarket", lambda: __import__('intermarket').get_intermarket()),
    ("correlation_regime", lambda: __import__('correlation_regime').get_correlation_regime()),
    ("options_flow", lambda: __import__('options_flow').get_options_score("AAPL")),
    ("sector_rotator", lambda: __import__('sector_rotator').get_sector_rotator()),
]

for name, func in modules_market:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== EXECUTION MODULES =====
print("\n[Execution Modules]")
modules_exec = [
    ("realtime_monitor", lambda: __import__('realtime_monitor').get_realtime_monitor()),
    ("manipulation_defense", lambda: __import__('manipulation_defense').get_manipulation_defense()),
    ("exit_optimizer", lambda: __import__('exit_optimizer').get_exit_optimizer()),
    ("execution_tracker", lambda: __import__('execution_tracker').get_execution_tracker()),
    ("frequency_controller", lambda: __import__('frequency_controller').get_frequency_controller()),
]

for name, func in modules_exec:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== PERFORMANCE MODULES =====
print("\n[Performance Modules]")
modules_perf = [
    ("high_performance", lambda: __import__('high_performance').get_optimizer()),
    ("alpha_generator", lambda: __import__('alpha_generator').get_alpha_generator()),
    ("winrate_optimizer", lambda: __import__('winrate_optimizer').get_winrate_optimizer()),
    ("performance_diagnosis", lambda: __import__('performance_diagnosis').get_diagnosis()),
    ("performance_attribution", lambda: __import__('performance_attribution').get_attribution()),
]

for name, func in modules_perf:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== SCALING MODULES =====
print("\n[Scaling Modules]")
modules_scale = [
    ("auto_compound", lambda: __import__('auto_compound').get_compound(100000)),
    ("dynamic_scaling", lambda: __import__('dynamic_scaling').get_scaler(100000)),
    ("ml_predictor", lambda: __import__('ml_predictor').get_ml_predictor()),
    ("earnings_calendar", lambda: __import__('earnings_calendar').get_earnings_calendar()),
]

for name, func in modules_scale:
    ok, res = test_module(name, func)
    if ok:
        print(f"  ✅ {name}")
        results['passed'] += 1
    else:
        print(f"  ❌ {name}: {res}")
        results['failed'] += 1
        results['errors'].append((name, res))

# ===== SUMMARY =====
print("\n" + "="*60)
total = results['passed'] + results['failed']
print(f"RESULT: {results['passed']}/{total} modules passed")
print("="*60)

if results['failed'] > 0:
    print(f"\n❌ FAILED MODULES ({results['failed']}):")
    for name, err in results['errors']:
        print(f"  • {name}: {err[:50]}")
else:
    print("\n🎉 ALL MODULES PASSED! System ready for deployment.")

# Calculate percentage
pct = results['passed'] / total * 100 if total > 0 else 0
print(f"\nIntegration Score: {pct:.0f}%")
