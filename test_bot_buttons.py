import sys
from telegram_interactive_bot import TelegramInteractiveBot

bot = TelegramInteractiveBot()
print("Triggering _handle_quant_status...")
bot._handle_quant_status()
print("QUANT STATUS SUCCESSFUL!")
