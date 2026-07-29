import sys
import os

# Ensure we can import modules from the current directory
sys.path.append(os.getcwd())

try:
    from trader import Trader
    from config import *
    from loguru import logger
    
    # Disable loguru output for this small script
    logger.remove()
    
    t = Trader()
    positions = t.get_positions()
    bp = t.get_buying_power()
    
    print(f"--- RESULTS ---")
    print(f"BUYING_POWER: {bp}")
    print(f"POSITION_COUNT: {len(positions)}")
    for p in positions:
        # p is a PositionInfo dataclass
        print(f"POS: {p.symbol} qty={p.quantity} avg={p.avg_price} cur={p.current_price}")
    print(f"--- END ---")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
