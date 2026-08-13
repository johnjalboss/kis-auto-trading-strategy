import json, os

print("==================================================")
print("=== INSPECTING FINNHUB_CACHE & UNIVERSE SYMBOLS ===")
print("==================================================")

if os.path.exists("finnhub_cache.json"):
    data = json.load(open("finnhub_cache.json", encoding="utf-8"))
    print("finnhub_cache keys:", list(data.keys())[:10])
    if isinstance(data, list):
        print(f"finnhub_cache list count: {len(data)}")
    elif isinstance(data, dict):
        print(f"finnhub_cache dict keys count: {len(data)}")

import universe
symbols = universe.get_all_symbols()
print(f"\nCurrent universe.get_all_symbols() count: {len(symbols)}")
print("==================================================")
