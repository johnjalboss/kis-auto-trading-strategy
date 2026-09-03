import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())
import config
from composite_signal import get_composite_engine
from trader import get_trader
import sqlite3

def audit_swap():
    db_path = "/home/ubuntu/kis-auto-trading/trades.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT symbol, avg_price, entry_time, quantity FROM positions WHERE symbol='CDNS'")
    row = cur.fetchone()
    conn.close()
    
    if not row:
        print("CDNS position not found in positions table!")
        return
        
    symbol, avg_price, entry_time_str, qty = row
    entry_time = datetime.strptime(entry_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
    hold_minutes = (datetime.now() - entry_time).total_seconds() / 60
    
    trader = get_trader()
    curr_price = trader.get_price('CDNS')
    pnl_pct = (curr_price - avg_price) / avg_price if avg_price > 0 else 0
    
    print("=== CDNS Position Details ===")
    print(f"Holding: {qty} shares @ ${avg_price:.2f} (Current Price: ${curr_price:.2f})")
    print(f"PnL: {pnl_pct:.2%}")
    print(f"Hold time: {hold_minutes:.1f} minutes")
    print(f"UPGRADE_MIN_HOLD_MINUTES: {config.UPGRADE_MIN_HOLD_MINUTES} minutes")
    print(f"UPGRADE_PROFIT_PROTECT_PCT: {config.UPGRADE_PROFIT_PROTECT_PCT:.2%}")
    
    engine = get_composite_engine()
    
    print("\n=== Re-scoring Existing Position ===")
    cdns_signal = engine.analyze('CDNS')
    print(f"CDNS Score: {cdns_signal.composite_score}")
    
    print("\n=== Scoring Target Upgrades ===")
    for tgt in ['ADM', 'AVT']:
        tgt_signal = engine.analyze(tgt)
        print(f"{tgt} Score: {tgt_signal.composite_score}")
        gap = tgt_signal.composite_score - cdns_signal.composite_score
        print(f"Gap: {gap} (Required Gap: {config.UPGRADE_SCORE_GAP})")
        
        # Check reasons why upgrade would be blocked
        is_hold_ok = hold_minutes >= config.UPGRADE_MIN_HOLD_MINUTES
        is_pnl_ok = pnl_pct < config.UPGRADE_PROFIT_PROTECT_PCT
        is_gap_ok = gap >= config.UPGRADE_SCORE_GAP
        
        print(f"  Hold time check: {'PASS' if is_hold_ok else 'BLOCKED'}")
        print(f"  Profit protect check: {'PASS' if is_pnl_ok else 'BLOCKED'}")
        print(f"  Score gap check: {'PASS' if is_gap_ok else 'BLOCKED'}")

if __name__ == "__main__":
    audit_swap()
