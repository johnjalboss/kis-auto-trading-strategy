import os
import sys
from loguru import logger
from datetime import datetime

sys.path.append(os.getcwd())
import config
from trader import get_trader
from strategy import get_strategy

def verify_fix():
    print("\n--- [STEP 1] VERIFYING MULTI-EXCHANGE SYNC ---")
    trader = get_trader()
    api_positions = trader.get_positions()
    
    symbols = [p.symbol for p in api_positions]
    print(f"Total positions found: {len(symbols)}")
    print(f"Positions: {symbols}")
    
    found_pld = "PLTD" in symbols or "PLD" in symbols
    if found_pld:
        print("✅ SUCCESS: PLTD/PLD (NYSE) is now visible to the bot!")
    else:
        print("❌ FAILURE: PLTD/PLD still missing from cross-exchange sync.")
        
    print("\n--- [STEP 2] SYNCING STRATEGY STATE ---")
    strategy = get_strategy()
    strategy.sync_positions(api_positions)
    
    print("\n--- [STEP 3] VERIFYING EXIT AUDIT LOGIC ---")
    current_positions = strategy.get_all_positions()
    for sym, pos in current_positions.items():
        try:
            # Fetch current price again to be fresh
            curr_price = trader.get_price(sym)
            if curr_price <= 0:
                curr_price = pos.entry_price
            
            exit_sig = strategy.check_exit(sym, curr_price)
            pnl_pct = (curr_price / pos.entry_price - 1) * 100 if pos.entry_price > 0 else 0
            
            print(f"Symbol: {sym:10} Price: {curr_price:10.2f} Avg: {pos.entry_price:10.2f} P&L: {pnl_pct:6.1f}% -> Action: {exit_sig.action if exit_sig else 'NONE'} ({exit_sig.reason if exit_sig else 'N/A'})")
            
            if sym in ["PLTD", "PLD", "AFRM"] and pnl_pct < -5:
                print(f"  -> {sym} is being audited for stop-loss. Reason: {exit_sig.reason}")
        except Exception as e:
            print(f"Symbol: {sym:10} - Error checking exit: {e}")

if __name__ == "__main__":
    verify_fix()
