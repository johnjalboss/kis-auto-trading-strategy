import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
import data_proxy

from base_adapters import get_available_adapters
from loguru import logger
import yfinance as yf
import pandas as pd

def main():
    symbol = "AAPL"
    df = yf.download(symbol, period="1mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df is None or df.empty:
        print("ERROR: Could not fetch data")
        return

    print(f"\nFetched {len(df)} rows for {symbol}")
    
    available_adapters = get_available_adapters()
    print(f"\nTotal adapters: {len(available_adapters)}")
    
    failures = []
    for adapter_class in available_adapters:
        try:
            adapter = adapter_class()
            result = adapter.analyze(df, symbol=symbol)
            score = result.get('score', 0) if isinstance(result, dict) else getattr(result, 'score', 0)
            print(f"  OK  {adapter.name}: score={score}")
        except AttributeError as e:
            print(f"  ERR {adapter_class.__name__}: AttributeError - {e}")
            failures.append((adapter_class.__name__, str(e)))
        except Exception as e:
            print(f"  ERR {adapter_class.__name__}: {type(e).__name__} - {e}")
            failures.append((adapter_class.__name__, str(e)))
    
    print(f"\n=== FAILURES ({len(failures)}) ===")
    for name, err in failures:
        print(f"  {name}: {err}")

if __name__ == "__main__":
    main()
