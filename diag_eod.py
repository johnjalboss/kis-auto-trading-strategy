import sys
sys.path.insert(0, ".")
import pytz
from datetime import datetime
import scheduler
from daily_settlement_reporter import DailySettlementReporter
from weekly_ai_report_generator import WeeklyAIReportGenerator
from telegram_interactive_bot import TelegramInteractiveBot

print("=== TIME DIAGNOSTIC ===")
s = scheduler.TradingScheduler()
print("Market open:", s.is_market_open())
print("Now EST:", s.now_est())

print("\n=== DAILY SETTLEMENT REPORT ===")
ds = DailySettlementReporter()
rep = ds.generate_daily_report()
print("Daily Report Msg:")
print(rep.get("telegram_msg"))

print("\n=== TESTING TELEGRAM SEND ===")
from notification import get_notifier
notifier = get_notifier()
print("Notifier initialized:", notifier)

print("\n=== TESTING TELEGRAM INTERACTIVE BOT ===")
bot = TelegramInteractiveBot()
print("Testing _handle_quant_status:")
try:
    bot._handle_quant_status()
    print("SUCCESS _handle_quant_status")
except Exception as e:
    print("ERROR _handle_quant_status:", e)
