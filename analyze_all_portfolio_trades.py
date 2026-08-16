import json, os, sqlite3
from datetime import datetime

print("==========================================================")
print("[ANALYSIS] ANALYZING ALL HISTORICAL TRADES IN PORTFOLIO_TRADES.JSON")
print("==========================================================")

with open("portfolio_trades.json", "r", encoding="utf-8") as f:
    trades = json.load(f)

print(f"Total trade entries in portfolio_trades.json: {len(trades)}")

# Group trades by year-month
by_month = {}
for t in trades:
    d_str = t.get("date", "")[:7]  # YYYY-MM
    by_month[d_str] = by_month.get(d_str, 0) + 1

for m in sorted(by_month.keys()):
    print(f"  Month {m}: {by_month[m]} trades")

print("==========================================================")
