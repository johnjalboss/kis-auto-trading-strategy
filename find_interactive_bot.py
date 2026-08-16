import glob

print("Searching where TelegramInteractiveBot is instantiated...")
for f in glob.glob("*.py"):
    try:
        content = open(f, encoding='utf-8', errors='ignore').read()
        if "TelegramInteractiveBot" in content or "telegram_interactive_bot" in content:
            print(f"Found reference in: {f}")
    except Exception:
        pass
