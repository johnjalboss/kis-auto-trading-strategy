import os
from chart_generator import generate_daily_pnl_chart
from notification import get_notifier

chart_path, caption = generate_daily_pnl_chart(days=30)
print("30-day Chart Generated:", chart_path)
print("Caption:\n", caption)

if chart_path and os.path.exists(chart_path):
    notifier = get_notifier()
    notifier.send_photo_sync(photo_path=chart_path, caption=caption)
    print("30-DAY PERFORMANCE CHART SENT TO TELEGRAM SUCCESSFULLY!")
