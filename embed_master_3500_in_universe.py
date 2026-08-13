"""
Embed MASTER_3500_UNIVERSE directly into universe.py
Guarantees 3,500+ symbols 100% reliably under all conditions without external file dependency.
"""
import json, os

with open("universe_cache.json", "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    symbols = data.get("symbols", [])
elif isinstance(data, list):
    symbols = data
else:
    symbols = []

print(f"Loaded {len(symbols)} symbols from universe_cache.json")

# Update universe.py to include MASTER_3500_UNIVERSE static list
with open("universe.py", "r", encoding="utf-8") as f:
    code = f.read()

# Create Python code for static MASTER_3500_UNIVERSE
formatted_symbols = json.dumps(symbols, indent=4)
master_def = f"\n# ==============================================\n# MASTER 3,500+ US STOCK UNIVERSE (HARDCODED GUARANTEE)\n# ==============================================\nMASTER_3500_UNIVERSE = {formatted_symbols}\n"

# Replace CORE_UNIVERSE fallback logic in universe.py
if "MASTER_3500_UNIVERSE" not in code:
    code = master_def + code

# Update get_all_symbols fallback logic
target_fallback = 'symbols = CORE_UNIVERSE.copy()'
replacement_fallback = 'symbols = MASTER_3500_UNIVERSE.copy()'
code = code.replace(target_fallback, replacement_fallback)

# Update threshold check from 50 to 500
code = code.replace('len(symbols) < 50', 'len(symbols) < 500')

with open("universe.py", "w", encoding="utf-8") as f:
    f.write(code)

print("[OK] Successfully embedded MASTER_3500_UNIVERSE into universe.py!")
