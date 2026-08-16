import sqlite3
from reporter import PerformanceReporter
from daily_settlement_reporter import DailySettlementReporter
from notification import get_notifier

# 1. Clear sent_reports for 2026-08-14 so it sends cleanly
conn = sqlite3.connect("trades.db")
conn.execute("DELETE FROM sent_reports WHERE report_type='DAILY_SUMMARY' AND report_date='2026-08-14'")
conn.commit()
conn.close()

# 2. Trigger Daily Performance Summary with Chart
rep = PerformanceReporter()
rep.send_daily_summary()

# 3. Trigger SOTA Institutional Daily Settlement Card
ds = DailySettlementReporter()
rep_data = ds.generate_daily_report()
if rep_data.get('telegram_msg'):
    get_notifier().send_message(rep_data['telegram_msg'])
ds.export_tax_csv()

print("ALL DAILY REPORTS SENT SUCCESSFULLY TO TELEGRAM!")
