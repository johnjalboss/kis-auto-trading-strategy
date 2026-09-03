import os
import sys

sys.path.insert(0, r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")

import data_proxy
from strategy import StrategyEngine
from composite_signal import CompositeSignalEngine, ActionType

print("=========================================================")
print("LIVE STRATEGY ENGINE VERIFICATION TEST")
print("=========================================================")

strategy = StrategyEngine()
comp_engine = CompositeSignalEngine()

test_symbols = ["SQQQ", "BMY", "GIS", "PEP", "ES"]

for symbol in test_symbols:
    try:
        comp_signal = comp_engine.analyze(symbol)
        print(f"\n[SYMBOL: {symbol}]")
        print(f"  -> Composite Score: {comp_signal.composite_score:.1f} | Action: {comp_signal.action}")
        
        entry_res = strategy.check_entry(symbol, macro_score=comp_signal.composite_score, is_screened=True)
        print(f"  -> Entry Action: {entry_res.action}")
        print(f"  -> Entry Reason: {entry_res.reason}")
        print(f"  -> Entry Price: ${entry_res.price:.2f}")
        
        if entry_res.action == "BUY":
            print(f"  [SUCCESS] VERIFIED BUY SIGNAL PASSED FOR {symbol}!")
        else:
            print(f"  [HOLD] Entry Held for {symbol}: {entry_res.reason}")
            
    except Exception as e:
        print(f"  [ERROR] testing {symbol}: {e}")
        import traceback
        traceback.print_exc()

print("\n=========================================================")
print("LIVE STRATEGY TEST COMPLETED CLEANLY!")
print("=========================================================")
