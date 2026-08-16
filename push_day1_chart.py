import os
from chart_generator import generate_daily_pnl_chart
from notification import get_notifier

p, c = generate_daily_pnl_chart()
print("Day 1 Chart generated:", p)
print("Caption:\n", c)

notifier = get_notifier()
notifier.send_photo_sync(photo_path=p, caption=c)
print("DAY 1 OFFICIAL CHART SENT TO TELEGRAM SUCCESSFULLY!")
