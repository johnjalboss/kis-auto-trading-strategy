import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from chart_generator import generate_daily_pnl_chart, _fetch_qqq_dollar_returns

print("==================================================")
print("🔍 TESTING VPS ALL-TIME CHART GENERATION (days=0)")
print("==================================================")

try:
    import config
    print(f"config.INITIAL_CAPITAL: ${config.INITIAL_CAPITAL:.2f}")
except Exception as e:
    print("config load error:", e)

res_path = generate_daily_pnl_chart(days=0)
print(f"Generated chart file path: {res_path}")

if os.path.exists(res_path):
    print(f"File exists! Size: {os.path.getsize(res_path)} bytes")
    print(f"Last modified: {os.path.getmtime(res_path)}")

print("==================================================")
