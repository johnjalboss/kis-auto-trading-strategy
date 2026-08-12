import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from telegram_interactive_bot import TelegramInteractiveBot

bot = TelegramInteractiveBot()
pos = bot._get_positions_dict()
print(f"✅ POSITIONS FETCHED ({len(pos)} items):")
for sym, p in pos.items():
    print(f"  • {sym}: {p.quantity} shares @ ${p.entry_price:.2f}")
