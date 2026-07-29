
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from strategy import get_strategy
from trader import get_trader

def diag():
    print("--- Internal State Check ---")
    s = get_strategy()
    internal_positions = s.get_all_positions()
    print(f"Internal positions count: {len(internal_positions)}")
    for sym, pos in internal_positions.items():
        print(f"  {sym}: {pos.quantity} (Entry: {pos.entry_time})")
        
    print("\n--- API State Check ---")
    t = get_trader()
    api_positions = t.get_positions()
    api_symbols = {p.symbol for p in api_positions}
    print(f"API positions: {api_symbols}")
    
    stale = [sym for sym in internal_positions if sym not in api_symbols]
    print(f"Stale positions identified: {stale}")
    
    if stale:
        print("\n--- Attempting manual sync ---")
        s.sync_positions(api_positions)
        print(f"New internal positions count: {len(s.get_all_positions())}")

if __name__ == "__main__":
    diag()
