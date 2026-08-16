import sqlite3
import os
from reporter import PerformanceReporter
from daily_settlement_reporter import DailySettlementReporter
from notification import get_notifier

# 1. Clear sent_reports lock for 2026-08-14 so it sends cleanly
conn = sqlite3.connect("trades.db")
conn.execute("DELETE FROM sent_reports WHERE report_type='DAILY_SUMMARY' AND report_date='2026-08-14'")
conn.commit()
conn.close()

# 2. Trigger Full Daily Performance Report with Day 1 Chart
rep = PerformanceReporter()
rep.send_daily_summary()

# 3. Trigger Daily Settlement Breakdown Card
ds = DailySettlementReporter()
settle_data = ds.generate_daily_report()
if settle_data and settle_data.get('telegram_msg'):
    get_notifier().send_message(settle_data['telegram_msg'])

print("DAILY REPORT RE-SENT TO TELEGRAM SUCCESSFULLY!")
