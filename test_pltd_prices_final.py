from trader import get_trader
import os

def test():
    t = get_trader()
    exchanges = ["NASD", "NYSE", "AMEX", "NAS", "NYS", "AMS"]
    symbol = "PLTD"
    
    print(f"Testing price fetch for {symbol} across codes:")
    for ex in exchanges:
        try:
            p = t.get_price(symbol, ex)
            print(f"  {ex}: {p}")
        except Exception as e:
            print(f"  {ex}: Error: {e}")

if __name__ == "__main__":
    test()
