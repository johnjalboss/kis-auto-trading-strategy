import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print("TELEGRAM_CHAT_ID:", chat_id)
print("Testing sendMessage to chat_id:")
url = f"https://api.telegram.org/bot{token}/sendMessage"
resp = requests.post(url, json={"chat_id": chat_id, "text": "🔔 <b>[시스템 연동 테스트]</b> 텔레그램 양방향 봇 통신 정상", "parse_mode": "HTML"}, timeout=5)
print("SendMessage response:", resp.status_code, resp.text)
