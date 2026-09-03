import universe
import os, json

syms = universe.get_all_symbols()
print(f"Total symbols in universe: {len(syms)}")
print(f"First 15: {syms[:15]}")
print(f"Last 10: {syms[-10:]}")

cache = 'universe_cache.json'
if os.path.exists(cache):
    d = json.load(open(cache))
    print(f"\nCache file: EXISTS")
    print(f"Cache updated: {d.get('updated','N/A')}")
    print(f"Cache count: {d.get('count', 0)}")
else:
    print("\nCache file: NOT FOUND (using CORE_UNIVERSE fallback)")
    print(f"CORE_UNIVERSE size: {len(universe.CORE_UNIVERSE)}")
