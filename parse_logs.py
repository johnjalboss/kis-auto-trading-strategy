import re
import json

log_file = 'logs/trading_bot.log'
date_pattern = '2026-03-06'
important_patterns = [
    'Trade Executed',
    'Signal',
    'Score',
    'PLTD',
    'BUY',
    'SELL',
    'rejected',
    'blocked'
]

if __name__ == "__main__":
    results = []
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if date_pattern in line:
                    if any(p.lower() in line.lower() for p in important_patterns):
                        results.append(line.strip())
    except Exception as e:
        print(f"Error reading log: {e}")

    with open('trade_analysis_raw.txt', 'w', encoding='utf-8') as f:
        for line in results:
            f.write(line + '\n')

    print(f"Extracted {len(results)} relevant log lines to trade_analysis_raw.txt")
