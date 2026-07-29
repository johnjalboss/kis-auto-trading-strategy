import re
import subprocess
import os

log_path = os.path.expanduser("~/kis-auto-trading/logs/trading_bot.log")
print(f"Path: {log_path}")
print(f"Exists: {os.path.exists(log_path)}")

if os.path.exists(log_path):
    log_bp = subprocess.getoutput(f"grep 'Buying Power' {log_path} | tail -1")
    print(f"Grep result: '{log_bp}'")
    
    bp_match = re.search(r'Buying Power: \$([0-9,.]+)', log_bp)
    if bp_match:
        bp = float(bp_match.group(1).replace(',', ''))
        print(f"Extracted BP: {bp}")
    else:
        print("Regex FAILED to match")
else:
    print("Log file NOT FOUND")
