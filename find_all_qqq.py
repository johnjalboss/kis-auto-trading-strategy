"""
Search for QQQ benchmark chart logic across all py files
"""
import os

search_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
results = []

for root, dirs, files in os.walk(search_dir):
    for f in files:
        if f.endswith(".py"):
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as file:
                    for idx, line in enumerate(file, 1):
                        if "QQQ" in line:
                            results.append(f"{f}:{idx}: {line.strip()}")
            except Exception:
                pass

print(f"Total QQQ references found: {len(results)}")
for r in results[:30]:
    print(r)
