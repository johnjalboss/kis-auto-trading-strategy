import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from chart_generator import generate_daily_pnl_chart

path = generate_daily_pnl_chart(days=0)
print("Generated path:", path)
if os.path.exists(path):
    print("File size:", os.path.getsize(path), "bytes")
