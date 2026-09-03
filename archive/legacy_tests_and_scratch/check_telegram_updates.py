import os
import requests
import config

print("CONFIG CHAT ID:", getattr(config, 'TELEGRAM_CHAT_ID', ''))
bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
if bot_token:
    resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates?limit=10")
    print("GETUPDATES STATUS:", resp.status_code)
    data = resp.json()
    print("TOTAL UPDATES IN QUEUE:", len(data.get("result", [])))
    for u in data.get("result", []):
        if "callback_query" in u:
            cb = u["callback_query"]
            print("CALLBACK:", {
                "id": cb.get("id"),
                "data": cb.get("data"),
                "from_id": cb.get("from", {}).get("id"),
                "from_username": cb.get("from", {}).get("username"),
                "chat_id": cb.get("message", {}).get("chat", {}).get("id")
            })
        elif "message" in u:
            msg = u["message"]
            print("MESSAGE:", {
                "text": msg.get("text"),
                "from_id": msg.get("from", {}).get("id"),
                "chat_id": msg.get("chat", {}).get("id")
            })
