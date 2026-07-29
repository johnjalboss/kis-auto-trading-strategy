
import sys
import os
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

try:
    import trader
    import base_adapters
    from base_analyzer import BaseAnalyzer
    
    print("--- Code Version Check ---")
    print(f"BaseAnalyzer has is_symbol_dependent: {hasattr(BaseAnalyzer, 'is_symbol_dependent')}")
    
    from base_adapters import UniversalAdapter
    ua = UniversalAdapter(None) # dummy instance
    print(f"UniversalAdapter has is_symbol_dependent: {hasattr(ua, 'is_symbol_dependent')}")
    
    print("\n--- Position Check ---")
    t = trader.get_trader()
    t.start()
    positions = t.get_positions()
    print(f"Total positions found: {len(positions)}")
    for p in positions:
        print(f"  {p.symbol}: {p.quantity} @ {p.avg_price} ({p.exchange})")
    
    print("\n--- Buying Power ---")
    print(f"  USD: {t.get_buying_power()}")
    
except Exception as e:
    print(f"\nCRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
