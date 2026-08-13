import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from chart_generator import generate_daily_pnl_chart

try:
    res = generate_daily_pnl_chart(days=0)
    print("CHART_GEN_SUCCESS:", res)
    if os.path.exists(res):
        print("FILE_SIZE_BYTES:", os.path.getsize(res))
except Exception as e:
    import traceback
    traceback.print_exc()
