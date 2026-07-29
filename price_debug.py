import sys
import os

# Ensure we can import modules from the current directory
sys.path.append(os.getcwd())

if __name__ == "__main__":
    try:
        from trader import Trader
        import config
        
        t = Trader()
        symbols = ["NFLX", "AMD", "TQQQ", "XOM", "PLTR"]
        
        print("--- PRICE CHECK ---")
        for s in symbols:
            p = t.get_price(s)
            print(f"{s}: ${p:.2f}")
        
        print("\n--- POSITION CHECK ---")
        pos = t.get_positions()
        for p in pos:
            print(f"POS: {p.symbol} qty={p.quantity} avg={p.avg_price:.2f} cur={p.current_price:.2f} exch={p.exchange}")
        
        print("--- END ---")
    except Exception as e:
        print(f"ERROR: {e}")
