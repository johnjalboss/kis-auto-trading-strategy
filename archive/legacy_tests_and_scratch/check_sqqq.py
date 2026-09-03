import kis_data
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="DEBUG")

print("Checking SQQQ Price...")
try:
    price = kis_data.get_current_price("SQQQ")
    print(f"SQQQ Price Data: {price}")
except Exception as e:
    print(f"Error fetching SQQQ price: {e}")

print("\nChecking SQQQ OHLCV...")
try:
    df = kis_data.get_daily_ohlcv("SQQQ", days=5)
    if df is not None:
        print(f"SQQQ OHLCV (last 5 days):\n{df}")
    else:
        print("SQQQ OHLCV returned None")
except Exception as e:
    print(f"Error fetching SQQQ OHLCV: {e}")
