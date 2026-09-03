import sys
sys.path.insert(0, '/home/ubuntu/kis-auto-trading')

from telegram_interactive_bot import TelegramInteractiveBot

bot = TelegramInteractiveBot()
pos_dict = bot._get_positions_dict()
print(f"✅ POSITIONS COUNT: {len(pos_dict)}")
for k, v in pos_dict.items():
    entry_p = getattr(v, 'entry_price', getattr(v, 'avg_price', 0.0))
    print(f"  • {k}: {v.quantity} shares @ ${entry_p:.2f}")
