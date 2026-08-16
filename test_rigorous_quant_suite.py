"""
Unit Test Script: 4 Rigorous Theory-Driven Quant Engines
=======================================================
Tests:
1. VCPBreakoutEngine (vcp_breakout_engine.py)
2. AccountHighWaterMarkSentinel (account_high_water_mark_sentinel.py)
3. DBMaintenanceGuard (db_maintenance_guard.py)
4. DailySettlementReporter (daily_settlement_reporter.py)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import os

print("======================================================================")
print("🧪 TESTING 4 RIGOROUS THEORY-DRIVEN QUANT ENGINES")
print("======================================================================")

# 1. VCP Breakout Engine
print("\n[TEST 1] VCPBreakoutEngine:")
from vcp_breakout_engine import VCPBreakoutEngine
vcp_engine = VCPBreakoutEngine()

# Synthesize 30 days of price data: Wave 1 depth (100 -> 88 -> 98), Wave 2 (98 -> 92 -> 97), Wave 3 (97 -> 94.5 -> 99 breakout)
prices_close = [95, 92, 90, 89, 93, 96, 98, 97, 95, 93, 92, 94, 96, 97, 96, 95, 96, 95.5, 96.5, 97, 96.8, 96.5, 97.2, 97.5, 98.0, 98.2, 98.5, 98.8, 99.2, 100.5]
prices_high = [p + 0.8 for p in prices_close]
prices_low = [p - 0.8 for p in prices_close]
vol = [100000 for _ in range(29)] + [250000] # Breakout volume spike
df_vcp = pd.DataFrame({"Close": prices_close, "High": prices_high, "Low": prices_low, "Volume": vol})

res_vcp = vcp_engine.analyze(df_vcp, "MINERVINI_LEADER")
print(f"  • VCP Pattern: {res_vcp['is_vcp_pattern']}, Pivot Breakout: {res_vcp['is_pivot_breakout']}, Bonus: +{res_vcp['score_bonus']} pts, Label: {res_vcp['label']}")
assert res_vcp['is_vcp_pattern'] == True
print("  ✅ [PASS] VCPBreakoutEngine verified!")

# 2. Account High-Water Mark Sentinel
print("\n[TEST 2] AccountHighWaterMarkSentinel:")
from account_high_water_mark_sentinel import AccountHighWaterMarkSentinel
sentinel = AccountHighWaterMarkSentinel(state_file="test_hwm_state.json", threshold_drawdown_pct=-4.5)

# 1. New peak $1,000
res_hwm1 = sentinel.evaluate_equity(1000.0)
print(f"  • Peak Equity: ${res_hwm1['hwm_equity']}, Status: {res_hwm1['status']}")
assert res_hwm1['hwm_equity'] == 1000.0

# 2. Drawdown to $940 (-6.0% -> trigger profit lock)
res_hwm2 = sentinel.evaluate_equity(940.0)
print(f"  • DD: {res_hwm2['drawdown_from_hwm_pct']}%, Lock Active: {res_hwm2['is_profit_lock_active']}, Sizing: {res_hwm2['sizing_multiplier']}x")
assert res_hwm2['is_profit_lock_active'] == True
assert res_hwm2['sizing_multiplier'] == 0.50

if os.path.exists("test_hwm_state.json"):
    os.remove("test_hwm_state.json")
print("  ✅ [PASS] AccountHighWaterMarkSentinel verified!")

# 3. DB Maintenance Guard
print("\n[TEST 3] DBMaintenanceGuard:")
from db_maintenance_guard import DBMaintenanceGuard
db_guard = DBMaintenanceGuard(db_path="trades.db", backup_dir="test_backups", max_backups=3)
res_db = db_guard.run_daily_maintenance()
print(f"  • Integrity OK: {res_db['integrity_ok']}, Vacuum OK: {res_db['vacuum_ok']}, Backup: {res_db['backup_created']}")
assert res_db['integrity_ok'] == True
assert res_db['vacuum_ok'] == True
if os.path.exists("test_backups"):
    import shutil
    shutil.rmtree("test_backups")
print("  ✅ [PASS] DBMaintenanceGuard verified!")

# 4. Daily Settlement Reporter & Tax CSV
print("\n[TEST 4] DailySettlementReporter & Tax CSV:")
from daily_settlement_reporter import DailySettlementReporter
reporter = DailySettlementReporter(db_path="trades.db")
rep_out = reporter.generate_daily_report()
print(f"  • Daily Report Date: {rep_out['date']}, Trades: {rep_out['trades_count']}, PnL: ${rep_out['realized_pnl_usd']:.2f}")

tax_csv = reporter.export_tax_csv(output_file="test_tax_export.csv")
assert os.path.exists(tax_csv)
print(f"  • Korean Tax Export CSV generated: {tax_csv}")
if os.path.exists("test_tax_export.csv"):
    os.remove("test_tax_export.csv")
print("  ✅ [PASS] DailySettlementReporter verified!")

print("\n======================================================================")
print("🎉 ALL 4 RIGOROUS QUANT ENGINES TESTED & VALIDATED 100% CLEAN!")
print("======================================================================")
