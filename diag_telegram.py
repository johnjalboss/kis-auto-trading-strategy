import sys
try:
    import telegram
    print("telegram version:", telegram.__version__)
    from telegram import Bot
    print("Bot imported successfully")
except ImportError as e:
    print("ImportError:", e)
except Exception as e:
    print("Other Exception:", e)
