"""
Find QQQ benchmark lines in web_dashboard.py
"""
with open(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\web_dashboard.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if "QQQ" in line or "qqq" in line or "benchmark" in line.lower():
        print(f"Line {idx}: {line.strip()}")
