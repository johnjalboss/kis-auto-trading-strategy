import os
import re

files = [f for f in os.listdir('.') if f.startswith('remote_trading_bot') or f.startswith('bot_remote')]
date_pattern = '2026-03-06'
keywords = ['Trade Executed', 'Signal', 'Score', 'PLTD', 'rejected', 'blocked', 'BUY', 'SELL']

results = []
for file in files:
    if not os.path.isfile(file): continue
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if date_pattern in line:
                    if any(k.lower() in line.lower() for k in keywords):
                        results.append(f"{file}: {line.strip()}")
    except Exception as e:
        results.append(f"Error reading {file}: {e}")

with open('trade_analysis_remote.txt', 'w', encoding='utf-8') as f:
    for line in results:
        f.write(line + '\n')

print(f"Extracted {len(results)} lines to trade_analysis_remote.txt")
