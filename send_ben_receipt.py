import sys
sys.path.append('/home/ubuntu/kis-auto-trading')
from telegram_receipt import TelegramReceiptGenerator
from watchdog import send_tg

receipt_msg = TelegramReceiptGenerator.format_buy_receipt(
    symbol='BEN',
    quantity=23,
    price=35.41,
    setup='[CHOPPY SELECTIVE] HIGH_CONVICTION_QUANT: Institutional score 100 | PEAD (+6%)',
    score=100,
    sl_price=33.64,
    atr=1.18,
    macro_regime='CHOPPY'
)
res = send_tg(receipt_msg)
print('Telegram Send Result:', res)