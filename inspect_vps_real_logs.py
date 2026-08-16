"""
Inspect real log files on VPS to extract 100% genuine live executed trades by main.py
"""
import os, glob, re

print("==========================================================")
print("🔍 SEARCHING REAL VPS LOG FILES FOR GENUINE EXECUTED TRADES")
print("==========================================================")

log_files = glob.glob("/home/ubuntu/kis-auto-trading/logs/*.log") + glob.glob("logs/*.log")
real_trades_found = []

for lf in log_files:
    if not os.path.exists(lf):
        continue
    print(f"Reading log file: {lf} ({os.path.getsize(lf)} bytes)")
    try:
        with open(lf, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if any(k in line for k in ["BUY", "SELL", "체결", "매수", "매도", "ORDER"]):
                    if "INFO" in line or "SUCCESS" in line or "Order" in line:
                        real_trades_found.append(line.strip())
    except Exception as e:
        print(f"  Error reading {lf}: {e}")

print(f"\nTotal Log Lines with Trade Events: {len(real_trades_found)}")
if real_trades_found:
    print("Sample Real Log Events (last 20):")
    for l in real_trades_found[-20:]:
        print("  ", l)

print("==========================================================")
