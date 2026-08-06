import os

log_files = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.log'):
            log_files.append(os.path.join(root, file))

results = []
for log in log_files:
    try:
        with open(log, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'Trade Executed' in line:
                    results.append(f"{log}: {line.strip()}")
    except Exception as err:
        print("⚠️ [find_all_trades.py] Fallback triggered:", err)

# Sort results by what looks like a timestamp in the log line
def extract_timestamp(line):
    # Try to find something like 2026-03-06 17:01:31
    match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
    return match.group(0) if match else ""

import re
results.sort(key=extract_timestamp)

with open('all_trade_executions.txt', 'w', encoding='utf-8') as f:
    for line in results:
        f.write(line + '\n')

print(f"Total trade executions found: {len(results)}")
if results:
    print("Latest 10 executions:")
    for r in results[-10:]:
        print(r)
