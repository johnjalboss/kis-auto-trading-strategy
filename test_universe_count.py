import universe
syms = universe.get_all_symbols()
print("==================================================")
print(f"✅ UNIVERSE ALL SYMBOLS COUNT: {len(syms)}")
print(f"First 10: {syms[:10]}")
print(f"Last 10: {syms[-10:]}")
print("==================================================")
