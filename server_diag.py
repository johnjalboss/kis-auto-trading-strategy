import trader
from loguru import logger
import config
from datetime import datetime

def diagnose():
    logger.remove()
    logger.add("diag_output.txt", level="INFO")
    
    print("=== SERVER DIAGNOSIS ===")
    t = trader.get_trader()
    t.start()
    
    bp = t.get_buying_power()
    print(f"Buying Power: ${bp:,.2f}")
    
    positions = t.get_positions()
    print(f"Positions: {len(positions)}")
    for p in positions:
        print(f" - {p.symbol}: {p.quantity} shares, Market Value: ${p.market_value:,.2f}, P&L: {p.pnl_pct:+.2%}")
    
    import strategy
    s = strategy.StrategyEngine()
    s.sync_positions(positions)
    
    print(f"\nMax Positions: {config.MAX_POSITIONS}")
    print(f"Max Position PCT: {config.MAX_POSITION_PCT:.0%}")
    
    # Check if we are in RISK_OFF
    from orchestrator import get_orchestrator
    # We might not be able to get the running orchestrator easily, but let's try reading the last log
    print("\nRecent Log Tail (Sizing/Exposure):")
    try:
        with open("remote_trading_bot.log", "r") as f:
            lines = f.readlines()
            for line in lines[-100:]:
                if "Exposure" in line or "qty" in line or "size" in line or "130-Module" in line:
                    print(line.strip())
    except:
        print("Could not read log file.")

if __name__ == "__main__":
    diagnose()
