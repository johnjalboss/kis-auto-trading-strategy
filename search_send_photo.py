import os

content = open("telegram_interactive_bot.py", encoding="utf-8").read()
lines = content.split("\n")
for idx, line in enumerate(lines):
    if "send_photo" in line or "send_photo_sync" in line:
        print(f"Line {idx+1}: {line}")
