import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from trader import Trader

try:
    t = Trader()
    positions = t.get_positions()
    print(f"=== KIS REAL ACCOUNT POSITIONS ({len(positions)} items) ===")
    for p in positions:
        print(f"• Symbol: {p.symbol:5s} | Qty: {p.quantity:2d} | Avg Price: ${p.avg_price:.2f} | Current: ${p.current_price:.2f} | PnL: {p.pnl_pct:+.2f}%")
except Exception as e:
    import traceback
    print(f"Error fetching KIS positions: {e}")
    traceback.print_exc()
