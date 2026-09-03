import os
import re

directory = '.'

api_patterns = {
    'yfinance': re.compile(r'yfinance|yf\.download|yf\.Ticker'),
    'kis_data': re.compile(r'kis_data|kis_client'),
    'requests': re.compile(r'requests\.get|requests\.post'),
    'beautiful_soup': re.compile(r'BeautifulSoup'),
    'selenium': re.compile(r'selenium|webdriver'),
    'database': re.compile(r'sqlite3|trades\.db|trade_journal\.db'),
}

results = {key: [] for key in api_patterns.keys()}
total_py = 0

for filename in os.listdir(directory):
    if filename.endswith('.py'):
        total_py += 1
        filepath = os.path.join(directory, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for key, pattern in api_patterns.items():
                    if pattern.search(content):
                        results[key].append(filename)
        except Exception as e:
            print("⚠️ [audit_script.py] Fallback triggered:", e)

print(f"Total Python Modules Scanned: {total_py}")
print("========================================")

for key, files in results.items():
    print(f"Modules using API [{key}] (Count: {len(files)}):")
    if len(files) == 0:
        print("  (None)")
    elif len(files) <= 15:
        print('  ' + ', '.join(files))
    else:
        print('  ' + ', '.join(files[:15]) + f'... and {len(files)-15} more')
    print()
