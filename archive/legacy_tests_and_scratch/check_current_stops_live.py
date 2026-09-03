"""
Check Current Position Stop Lines Live (check_current_stops_live.py)
====================================================================
Calculates the exact mathematical Z-Score volatility-normalized stop prices ($) for all held positions.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import kis_data
from trader import Trader
from mathematical_dynamic_stop import MathematicalDynamicStop

print("============================================================")
print("📐 MATHEMATICAL VOLATILITY Z-SCORE DYNAMIC STOP AUDIT")
print("============================================================")

trader = Trader()
positions = trader.get_positions()

if not positions:
    print("No active positions held.")
    sys.exit(0)

mds = MathematicalDynamicStop(atr_period=14, z_safety_margin=1.0)

print(f"{'SYMBOL':<8} {'ENTRY':<10} {'CURRENT':<10} {'PNL %':<9} {'SIGMA(σ)':<10} {'Z-SCORE':<10} {'MATH STOP':<12} {'PROTECTION TYPE':<28}")
print("-" * 105)

for p in positions:
    sym = p.symbol
    entry_p = p.avg_price
    curr_p = p.current_price
    pnl_pct = ((curr_p - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0

    df = kis_data.get_daily_ohlcv(sym, days=30)
    res = mds.calculate_optimal_stop(df, entry_p, curr_p)

    stop_p = res['stop_price']
    z_score = res['z_score']
    sigma = res['sigma_pct']
    reason = res['reason']
    dist_pct = ((curr_p - stop_p) / curr_p) * 100.0 if curr_p > 0 else 0.0

    print(f"{sym:<8} ${entry_p:<9.2f} ${curr_p:<9.2f} {pnl_pct:+6.2f}%   {sigma:5.2f}%     {z_score:5.2f}σ    ${stop_p:<11.2f} {reason:<28} (Dist: -{dist_pct:.1f}%)")

print("============================================================")
