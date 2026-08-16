import os

content = open("orchestrator.py", encoding="utf-8").read()
lines = content.split("\n")
for idx, line in enumerate(lines):
    if "TelegramInteractiveBot" in line or "interactive_bot" in line:
        print(f"Line {idx+1}: {line}")
