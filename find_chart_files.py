"""
Find all python scripts related to chart generation or QQQ
"""
import glob, os

files = glob.glob(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\*qqq*.py") + \
        glob.glob(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\*chart*.py") + \
        glob.glob(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\*bench*.py")

print("MATCHING CHART/QQQ FILES:")
for f in files:
    print(f)
