import json, os

path = "/home/ubuntu/kis-auto-trading/universe_cache.json"
print("Path exists:", os.path.exists(path))
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Data type:", type(data))
    if isinstance(data, list):
        print("List length:", len(data))
        print("First 10:", data[:10])
    elif isinstance(data, dict):
        print("Dict keys:", list(data.keys()))
        syms = data.get("symbols", [])
        print("Symbols length:", len(syms))
        print("First 10:", syms[:10])
