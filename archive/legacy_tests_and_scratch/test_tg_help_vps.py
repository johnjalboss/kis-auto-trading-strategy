"""
Test Telegram help message output on VPS
"""
import sys, os
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
os.chdir('/home/ubuntu/kis-auto-trading')

from telegram_interactive_bot import TelegramInteractiveBot

bot = TelegramInteractiveBot()
print("==================================================")
print("🔍 TESTING TELEGRAM HELP MENU OUTPUT")
print("==================================================")

text = (
    "🤖 <b>KIS 미국주식 AI 스윙 봇 대시보드</b>\n\n"
    "🌐 <b>실시간 웹 대시보드:</b>\n"
    "👉 http://141.148.172.12:8080 (PW: <code>0201!</code>)\n\n"
    "아래 버튼을 눌러 실시간 성과 및 분석을 확인하세요:"
)
print(text)
print("==================================================")
