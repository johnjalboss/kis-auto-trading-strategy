import os, sys, time
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from chart_generator import generate_daily_pnl_chart
from notifier import get_notifier

print("Generating fresh All-Time performance chart...")
chart_path = generate_daily_pnl_chart(days=0)
print("Generated chart path:", chart_path)

if chart_path and os.path.exists(chart_path):
    print("Sending fresh chart to Telegram...")
    notifier = get_notifier()
    notifier.send_photo_sync(chart_path, f"📊 [전체 수익차트] 오늘({time.strftime('%Y-%m-%d %H:%M:%S')}) 자산 최신화 반영 완료!")
    print("✅ Fresh chart successfully sent to Telegram!")
else:
    print("❌ Chart generation failed!")
