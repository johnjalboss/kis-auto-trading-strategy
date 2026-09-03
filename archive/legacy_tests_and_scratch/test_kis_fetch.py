import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

try:
    from trader import Trader
    t = Trader()
    eq = t.get_total_equity()
    cash = t.get_buying_power()
    print(f"✅ TRADER REAL-TIME EQUITY: ${eq:,.2f}")
    print(f"✅ TRADER REAL-TIME CASH: ${cash:,.2f}")
except Exception as e:
    import traceback
    print(f"❌ Trader Fetch Error: {e}")
    traceback.print_exc()
