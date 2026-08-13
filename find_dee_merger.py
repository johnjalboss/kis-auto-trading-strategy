"""
Find all occurrences of dee-merger or trycloudflare in python files
"""
import os, glob

search_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
found = []

for root, dirs, files in os.walk(search_dir):
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if "dee-merger" in content or "trycloudflare" in content:
                        found.append(fp)
            except Exception:
                pass

print("FOUND IN FILES:")
for f in found:
    print(f)
