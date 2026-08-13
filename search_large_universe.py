import os, glob

print("Searching for universe files or 3000+ ticker lists...")
for f in glob.glob("*.py") + glob.glob("*.json") + glob.glob("*.txt"):
    try:
        content = open(f, encoding='utf-8', errors='ignore').read()
        if "3000" in content or "3,000" in content or "3500" in content or "3,500" in content or "NASDAQ" in content and "NYSE" in content and len(content) > 50000:
            print(f"Match found in: {f} (size: {os.path.getsize(f)} bytes)")
    except Exception:
        pass
