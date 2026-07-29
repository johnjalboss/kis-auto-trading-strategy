import re

log_file = "remote_trading_bot_latest.log"

try:
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    rlmd_lines = []
    for i, line in enumerate(lines):
        if "RLMD" in line or "rlmd" in line:
            rlmd_lines.append(line.strip())
            
    print(f"Found {len(rlmd_lines)} lines mentioning RLMD. First 20:")
    for line in rlmd_lines[:20]:
        print(line)
        
    print("\nLast 20:")
    for line in rlmd_lines[-20:]:
        print(line)

except FileNotFoundError:
    print(f"File {log_file} not found locally.")
except Exception as e:
    print(f"Error reading file: {e}")
