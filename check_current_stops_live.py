"""
Check Current Position Stop Lines Live (check_current_stops_live.py)
====================================================================
Calculates the exact trailing stop & profit-locking stop price ($) for all currently held positions on VPS.
"""

import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import kis_data
from trader import Trader
from profit_locking_stop import ProfitLockingStop

print("============================================================")
print("📊 LIVE POSITION TRAILING STOP & PROFIT LOCKING AUDIT")
print("============================================================")

trader = Trader()
positions = trader.get_positions()

if not positions:
    print("No active positions held.")
    sys.exit(0)

pls = ProfitLockingStop(atr_multiplier=2.0)

print(f"{'SYMBOL':<8} {'ENTRY':<10} {'CURRENT':<10} {'PNL %':<10} {'STOP PRICE':<12} {'PROTECTION TYPE':<32}")
print("-" * 88)

for p in positions:
    sym = p.symbol
    entry_p = p.avg_price
    curr_p = p.current_price
    pnl_pct = ((curr_p - entry_p) / entry_p) * 100.0 if entry_p > 0 else 0.0

    # Fetch daily OHLCV
    df = kis_data.get_daily_ohlcv(sym, days=30)
    stop_p = 0.0
    stop_type = "Trailing Stop"
    highest_p = curr_p
    atr = curr_p * 0.02 # Default 2% ATR

    if df is not None and not df.empty:
        highest_p = max(df['High'].max(), curr_p)
        # Calculate 14-day ATR
        df['TR'] = (df['High'] - df['Low']).abs()
        atr = float(df['TR'].tail(14).mean())

    lock_res = pls.calculate_locked_stop(entry_p, curr_p, highest_p, atr)
    stop_p = lock_res['stop_price']
    stop_type = lock_res['type']

    dist_pct = ((curr_p - stop_p) / curr_p) * 100.0 if curr_p > 0 else 0.0

    print(f"{sym:<8} ${entry_p:<9.2f} ${curr_p:<9.2f} {pnl_pct:+6.2f}%   ${stop_p:<11.2f} {stop_type:<32} (Dist: -{dist_pct:.1f}%)")

print("============================================================")
