"""
Audit Initial Capital & Account Deposit History (audit_initial_capital_live.py)
================================================================================
Checks config, .env, trades.db, daily_stats, and KIS account API balance.
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

import sqlite3
import json

print("==========================================================")
print("🏦 INITIAL CAPITAL & ACCOUNT DEPOSIT HISTORY AUDIT")
print("==========================================================")

# 1. Check .env and config.py
env_cap = os.getenv("INITIAL_CAPITAL", "NOT_SET")
print(f"1. .env INITIAL_CAPITAL: {env_cap}")

try:
    import config
    cfg_cap = getattr(config, 'INITIAL_CAPITAL', 'NOT_SET')
    print(f"2. config.py INITIAL_CAPITAL: {cfg_cap}")
except Exception as e:
    print(f"2. config.py load error: {e}")

# 3. Check trades.db daily_stats table
db_path = "trades.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("\n3. trades.db - FIRST 5 ROWS of daily_stats:")
    for row in cur.execute("SELECT date, starting_balance, ending_balance, net_pnl FROM daily_stats ORDER BY date ASC LIMIT 5"):
        print(f"   Date: {row[0]} | StartBal: ${row[1]:,.2f} | EndBal: ${row[2]:,.2f} | NetPnL: ${row[3]:,.2f}")
        
    print("\n4. trades.db - FIRST 3 TRADES:")
    for row in cur.execute("SELECT id, symbol, side, quantity, price, entry_time FROM trades ORDER BY id ASC LIMIT 3"):
        print(f"   Trade #{row[0]}: {row[2]} {row[1]} x {row[3]} @ ${row[4]:,.2f} | Time: {row[5]}")

    conn.close()
else:
    print("trades.db not found")

# 5. Check Live KIS Account Balance via Trader
try:
    from trader import Trader
    t = Trader()
    bp = t.get_buying_power()
    pos = t.get_positions()
    pos_val = sum(p.quantity * p.current_price for p in pos)
    total_eq = bp + pos_val
    print(f"\n5. Live KIS Account Status:")
    print(f"   - Buying Power (Cash): ${bp:,.2f}")
    print(f"   - Positions Value:     ${pos_val:,.2f}")
    print(f"   - Total Equity Today:  ${total_eq:,.2f}")
except Exception as e:
    print(f"Live KIS balance query error: {e}")

print("==========================================================")
