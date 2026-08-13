"""
Audit ALL-TIME 6+ Months Realized PnL from trades.db (audit_all_time_closed_pnl.py)
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import sqlite3

print("==========================================================")
print("🔍 ALL-TIME 6+ MONTHS TRADES & PNL AUDIT")
print("==========================================================")

conn = sqlite3.connect("trades.db")
cur = conn.cursor()

# 1. Total Net Realized PnL from all closed SELL trades
cur.execute("SELECT COUNT(*), SUM(pnl), SUM(pnl_pct) FROM trades WHERE side = 'SELL'")
row = cur.fetchone()
closed_count = row[0] or 0
total_realized_pnl = row[1] or 0.0

print(f"1. Total Closed SELL Trades: {closed_count} trades")
print(f"2. Total All-Time Realized Net PnL: ${total_realized_pnl:+,.2f}")

# 2. Check min date and max date of trades
cur.execute("SELECT MIN(entry_time), MAX(entry_time) FROM trades")
min_t, max_t = cur.fetchone()
print(f"3. Trade Date Range: {min_t} ~ {max_t}")

# 3. Check daily_stats total net_pnl
cur.execute("SELECT COUNT(*), SUM(net_pnl) FROM daily_stats")
ds_row = cur.fetchone()
ds_count = ds_row[0] or 0
ds_total_pnl = ds_row[1] or 0.0
print(f"4. Daily Stats Records: {ds_count} days | Total Net PnL: ${ds_total_pnl:+,.2f}")

# 4. Live Current Total Equity
try:
    from trader import Trader
    t = Trader()
    bp = t.get_buying_power()
    pos = t.get_positions()
    pos_val = sum(p.quantity * p.current_price for p in pos)
    unrealized_pnl = sum((p.current_price - p.avg_price) * p.quantity for p in pos)
    total_eq = bp + pos_val
    print(f"\n5. Live Current Equity: ${total_eq:,.2f}")
    print(f"   - Current Unrealized PnL: ${unrealized_pnl:+,.2f}")

    # TRUE INITIAL CAPITAL CALCULATION
    all_time_total_pnl = total_realized_pnl + unrealized_pnl
    true_initial_capital = total_eq - all_time_total_pnl

    print("\n==========================================================")
    print(f"🎯 ALL-TIME TOTAL PNL (Realized + Unrealized): ${all_time_total_pnl:+,.2f}")
    print(f"🏆 TRUE ALL-TIME INITIAL DEPOSIT CAPITAL:       ${true_initial_capital:,.2f}")
    print("==========================================================")
except Exception as e:
    print("Trader error:", e)

conn.close()
