"""
Trigger fresh all-time chart send to Telegram on VPS
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from telegram_interactive_bot import TelegramInteractiveBot

print("==================================================")
print("🚀 SENDING FRESH ALL-TIME CHART TO TELEGRAM")
print("==================================================")

bot = TelegramInteractiveBot()
bot._handle_chart(0)

print("✅ Fresh chart sent to Telegram!")
print("==================================================")
