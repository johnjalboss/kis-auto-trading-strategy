import os
from trader import Trader

def audit_positions():
    trader = Trader()
    # KIS exchange codes for overseas stocks
    exchanges = {
        "NASD": "NASDAQ",
        "NYSE": "NYSE",
        "AMEX": "AMEX",
        "NAS": "NASDAQ (Alt)",
        "NYS": "NYSE (Alt)",
        "AMS": "AMEX (Alt)"
    }
    
    print("=== KIS Position Audit ===")
    for code, name in exchanges.items():
        print(f"\nChecking Exchange: {code} ({name})")
        try:
            # We bypass the cache to get live data
            positions = trader.get_positions() # This might need modification if get_positions doesn't take code
            # Note: If trader.get_positions() fetches ALL, we just need to see how it categorizes them.
            if hasattr(trader, 'kis'):
                # Try direct KIS client call if possible
                pass
            
            for pos in positions:
                print(f"  - {pos.symbol}: {pos.quantity} shares, exchange label: {getattr(pos, 'exchange', 'Unknown')}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    audit_positions()
