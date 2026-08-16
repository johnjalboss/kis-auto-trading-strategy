import sqlite3

conn = sqlite3.connect("trades.db")
cur = conn.cursor()
print("=== SENT_REPORTS ===")
for row in cur.execute("SELECT * FROM sent_reports"):
    print(row)

print("\n=== TESTING reporter.send_daily_summary() ===")
from reporter import PerformanceReporter
rep = PerformanceReporter()
us_d = rep._us_date()
print("US Date for reporter:", us_d)
print("generate_daily_report text:")
txt = rep.generate_daily_report(us_d)
print(txt)

print("\n=== EXECUTING send_daily_summary() NOW ===")
rep.send_daily_summary()
print("send_daily_summary completed!")
