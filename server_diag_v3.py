from scheduler import TradingScheduler
from trader import Trader
from datetime import datetime
import pytz

def diagnostic():
    scheduler = TradingScheduler()
    trader = Trader()
    
    now_est = scheduler.now_est()
    is_open = scheduler.is_market_open()
    session = scheduler.get_session()
    
    print(f"--- Diagnostic Report ({datetime.now()}) ---")
    print(f"Now EST: {now_est}")
    print(f"Session: {session}")
    print(f"Is Market Open: {is_open}")
    print(f"Weekday: {now_est.weekday()} (0=Mon, 6=Sun)")
    
    try:
        bp = trader.get_buying_power()
        print(f"KIS API Connection: OK (Buying Power: ${bp:,.2f})")
    except Exception as e:
        print(f"KIS API Connection: FAILED ({e})")
        
    try:
        pos = trader.get_positions()
        print(f"KIS Positions: {len(pos)} found")
        for p in pos:
            print(f"  - {p.symbol}: {p.quantity} shares")
    except Exception as e:
        print(f"KIS Position Fetch: FAILED ({e})")

if __name__ == "__main__":
    diagnostic()
