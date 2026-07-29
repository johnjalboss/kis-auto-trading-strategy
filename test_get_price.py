import sys
from loguru import logger
logger.add(sys.stdout, level="DEBUG")

from trader import get_trader

def main():
    t = get_trader()
    t.start()
    for sym in ["BROS", "ACHC", "ANAB", "ACLS", "AAP"]:
        price = t.get_price(sym)
        print(f"Symbol {sym} price: {price}")
    t.stop()

if __name__ == "__main__":
    main()
