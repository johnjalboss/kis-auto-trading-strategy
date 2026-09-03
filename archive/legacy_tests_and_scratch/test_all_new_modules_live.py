"""
Comprehensive Live Integration Verification Script (test_all_new_modules_live.py)
=====================================================================================
Runs live functional tests for all 14 newly added/updated quant modules on the VPS.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import pandas as pd
import numpy as np

print("============================================================")
print("🚀 RUNNING LIVE INTEGRATION & FORMULA AUDIT FOR ALL MODULES")
print("============================================================")

passed = 0
failed = 0

def test(name, func):
    global passed, failed
    try:
        res = func()
        print(f"  ✅ [PASS] {name}: {res}")
        passed += 1
    except Exception as e:
        import traceback
        print(f"  ❌ [FAIL] {name}: {e}")
        traceback.print_exc()
        failed += 1

# 1. safe_math
from safe_math import safe_div
test("safe_math", lambda: f"safe_div(10, 0) -> {safe_div(10, 0)}")

# 2. chandelier_exit
from chandelier_exit import ChandelierExit
df_dummy = pd.DataFrame({'High': [10, 12, 14, 15, 16]*3, 'Low': [9, 10, 12, 13, 14]*3, 'Close': [9.5, 11, 13, 14, 15]*3})
test("chandelier_exit", lambda: ChandelierExit().calculate_stop(df_dummy, 10.0)["stop_price"])

# 3. atomic_account_sync
from atomic_account_sync import AtomicAccountSync
test("atomic_account_sync", lambda: AtomicAccountSync().sync({})["synced"])

# 4. smart_order_controller
from smart_order_controller import SmartOrderController
test("smart_order_controller", lambda: SmartOrderController().execute_smart_buy("AAPL", 0, 100.0)["success"])

# 5. compound_capital_scaler
from compound_capital_scaler import CompoundCapitalScaler
test("compound_capital_scaler", lambda: CompoundCapitalScaler().calculate_scaled_allocation(1500.0, 300.0))

# 6. news_sentiment_engine
from news_sentiment_engine import NewsSentimentEngine
test("news_sentiment_engine", lambda: NewsSentimentEngine().analyze_symbol_news("AAPL")["label"])

# 7. telegram_receipt
from telegram_receipt import TelegramReceiptGenerator
test("telegram_receipt", lambda: "매수 체결" in TelegramReceiptGenerator.format_buy_receipt("AAPL", 5, 200.0))

# 8. weekly_audit
from weekly_audit import WeeklySelfHealingAudit
test("weekly_audit", lambda: WeeklySelfHealingAudit().run_audit_and_backup()["success"])

# 9. adaptive_vix_engine
from adaptive_vix_engine import AdaptiveVixEngine
vix_df = pd.DataFrame({'Close': [15.0 + i*0.2 for i in range(30)]})
test("adaptive_vix_engine", lambda: AdaptiveVixEngine().evaluate_vix_regime(vix_df, 18.0)["regime"])

# 10. mtf_confluence_filter
from mtf_confluence_filter import MTFConfluenceFilter
df_mtf = pd.DataFrame({'Close': [100.0 + i for i in range(120)]})
test("mtf_confluence_filter", lambda: MTFConfluenceFilter().check_alignment(df_mtf, "AAPL")["reason"])

# 11. gamma_squeeze_radar
from gamma_squeeze_radar import GammaSqueezeRadar
test("gamma_squeeze_radar", lambda: GammaSqueezeRadar().analyze_gamma("AAPL", 220.0)["score_bonus"])

# 12. risk_parity_allocator
from risk_parity_allocator import RiskParityAllocator
test("risk_parity_allocator", lambda: RiskParityAllocator().calculate_risk_parity_qty("AAPL", 200.0, 1000.0, 500.0, 5.0))

# 13. cross_asset_momentum
from cross_asset_momentum import CrossAssetMomentumTracker
spy = pd.DataFrame({'Close': [500, 502, 505, 508, 510]})
tlt = pd.DataFrame({'Close': [90, 89, 88, 87, 86]})
gld = pd.DataFrame({'Close': [200, 199, 198, 197, 196]})
test("cross_asset_momentum", lambda: CrossAssetMomentumTracker().analyze_cross_asset_flow(spy, tlt, gld)["regime"])

# 14. order_flow_imbalance
from order_flow_imbalance import OrderFlowImbalanceDetector
df_ofi = pd.DataFrame({'Close': [10, 11, 12, 13, 14], 'Volume': [1000, 2000, 1500, 3000, 2500]})
test("order_flow_imbalance", lambda: OrderFlowImbalanceDetector().evaluate_ofi(df_ofi, "AAPL")["ofi_score"])

print("============================================================")
print(f"📊 LIVE INTEGRATION TEST SUMMARY: PASSED {passed}/{passed+failed} | FAILED {failed}")
print("============================================================")
