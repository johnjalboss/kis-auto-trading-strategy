import os, glob

print("Searching for cmd_chart in all .py files...")
for f in glob.glob("*.py"):
    try:
        content = open(f, encoding='utf-8', errors='ignore').read()
        if "cmd_chart" in content:
            print(f"Found cmd_chart in: {f}")
    except Exception:
        pass
