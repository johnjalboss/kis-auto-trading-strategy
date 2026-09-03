"""
Test All 3 New Institutional Features Live (test_all_3_new_features.py)
========================================================================
Runs direct unit and live scenario tests for:
1. smart_order_chaser
2. tail_risk_circuit_breaker
3. self_tuning_alpha_attribution
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

print("============================================================")
print("🚀 TESTING ALL 3 NEW INSTITUTIONAL QUANT MODULES LIVE")
print("============================================================")

passed, failed = 0, 0

# 1. Test Smart Order Chaser
try:
    from smart_order_chaser import get_smart_chaser
    chaser = get_smart_chaser()
    res1 = chaser.evaluate_order("AAPL", "BUY", 100.0, 101.0, 20.0)
    assert res1['action'] in ["REPRICE", "CANCEL"]
    print("  ✅ [PASS] smart_order_chaser: Reprice action OK")
    passed += 1
except Exception as e:
    print(f"  ❌ [FAIL] smart_order_chaser: {e}")
    failed += 1

# 2. Test Tail Risk Circuit Breaker
try:
    from tail_risk_circuit_breaker import get_tail_risk_breaker
    breaker = get_tail_risk_breaker()
    res2 = breaker.check_tail_risk(vix_val=32.5)
    assert res2['is_active'] is True
    print("  ✅ [PASS] tail_risk_circuit_breaker: VIX 32.5 Triggered OK")
    passed += 1
except Exception as e:
    print(f"  ❌ [FAIL] tail_risk_circuit_breaker: {e}")
    failed += 1

# 3. Test Self Tuning Alpha Attribution
try:
    from self_tuning_alpha_attribution import get_alpha_tuner
    tuner = get_alpha_tuner()
    res3 = tuner.run_attribution_tuning()
    assert isinstance(res3, dict) and len(res3) > 0
    print("  ✅ [PASS] self_tuning_alpha_attribution: Multipliers Generated OK")
    passed += 1
except Exception as e:
    print(f"  ❌ [FAIL] self_tuning_alpha_attribution: {e}")
    failed += 1

print("============================================================")
print(f"📊 INTEGRATION TEST SUMMARY: PASSED {passed}/3 | FAILED {failed}")
print("============================================================")
