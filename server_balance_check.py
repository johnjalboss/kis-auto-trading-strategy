import sys
import os
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from trader import KISTrader
    trader = KISTrader()
    
    print("\n" + "="*60)
    print("### ACCOUNT BALANCE AUDIT ###")
    print("="*60)
    
    # Get balance using the same method the orchestrator uses
    balance = trader.get_balance()
    
    if not balance:
        print("No open positions found in KIS account.")
    else:
        print(f"{'SYMBOL':<10} | {'QTY':<5} | {'ENTRY':<10} | {'CURRENT':<10} | {'P&L %':<10}")
        print("-" * 60)
        for sym, qty, entry_price in balance:
            # Try to get current price
            curr_price = trader.get_price(sym)
            pnl_pct = ((curr_price - entry_price) / entry_price * 100) if entry_price > 0 and curr_price > 0 else 0
            print(f"{sym:<10} | {qty:<5} | {entry_price:<10.2f} | {curr_price:<10.2f} | {pnl_pct:>+7.1f}%")

    print("\n" + "="*60)
    
except Exception as e:
    print(f"BALANCE AUDIT FAILED: {e}")
    import traceback
    traceback.print_exc()
