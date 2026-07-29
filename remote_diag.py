import sys
import os
from datetime import datetime

# Ensure we can import modules from the current directory
sys.path.append(os.getcwd())

try:
    from trader import Trader
    from strategy import StrategyEngine
    from orchestrator import BotOrchestrator
    from risk_manager import RiskManager
    from database import TradeDatabase
    import config
    from loguru import logger
    
    # Disable loguru output for this small script
    logger.remove()
    
    t = Trader()
    s = StrategyEngine()
    rm = RiskManager()
    db = TradeDatabase()
    
    # Sync positions
    api_pos = t.get_positions()
    s.sync_positions(api_pos)
    
    bp = t.get_buying_power()
    
    print(f"--- DIAGNOSTICS ---")
    print(f"TIME_KST: {datetime.now()}")
    print(f"BUYING_POWER: {bp}")
    print(f"CONFIG_MAX_POSITIONS: {config.MAX_POSITIONS}")
    print(f"API_POSITION_COUNT: {len(api_pos)}")
    
    for p in api_pos:
        pnl = (p.current_price - p.avg_price) / p.avg_price if p.avg_price > 0 else 0
        print(f"API_POS: {p.symbol} qty={p.quantity} avg={p.avg_price:.2f} cur={p.current_price:.2f} pnl={pnl:+.2%}")
        
    print(f"STRATEGY_POSITION_COUNT: {len(s._positions)}")
    for sym, pos in s._positions.items():
        print(f"STRAT_POS: {sym} entry={pos.entry_price:.2f} qty={pos.quantity} high={pos.high_since_entry:.2f}")
        
    # Check if a sample buy would trigger
    sample_sym = "PLTR"
    signal = s.check_entry(sample_sym)
    print(f"SAMPLE_SIGNAL ({sample_sym}): {signal.action} score={signal.confidence} reason={signal.reason}")
    
    print(f"--- END ---")
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
