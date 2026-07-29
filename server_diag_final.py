import trader
import config
from datetime import datetime

def diagnose():
    print("=== FINAL SERVER DIAGNOSIS ===")
    t = trader.get_trader()
    t.start()
    
    bp = t.get_buying_power()
    print(f"Buying Power: ${bp:,.2f}")
    
    positions = t.get_positions()
    print(f"Positions: {len(positions)}")
    
    total_market_value = 0
    for p in positions:
        total_market_value += p.market_value
        print(f" - {p.symbol}: {p.quantity} shares, Market Value: ${p.market_value:,.2f}, Avg Price: ${p.avg_price:,.2f}, P&L: {p.pnl_pct:+.2%}")
    
    total_value = bp + total_market_value
    print(f"\nTOTAL ACCOUNT VALUE: ${total_value:,.2f}")
    
    print(f"\nConfig Defaults:")
    print(f" - MAX_POSITIONS: {config.MAX_POSITIONS}")
    print(f" - MAX_POSITION_PCT: {getattr(config, 'MAX_POSITION_PCT', 'N/A')}")
    print(f" - RISK_PER_TRADE: {getattr(config, 'RISK_PER_TRADE', 'N/A')}")

if __name__ == "__main__":
    diagnose()
