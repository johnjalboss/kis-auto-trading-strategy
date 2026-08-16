"""
Send detailed MRK trade explanation card to Telegram.
"""
from notification import get_notifier
from telegram_receipt import TelegramReceiptGenerator

notifier = get_notifier()

score_breakdown = [
    "🔥 [C-Level 임원진 대량 자사주 매수] 내부자 클러스터 매수 포착 (+25점)",
    "🚀 [섹터 주도주 순풍] 오늘 장 주도 섹터 1위(Healthcare) (+20점)",
    "⚡ [감마 레이더] Net GEX 양수 & 강세 풋콜비율(PCR 0.47) (+25점)",
    "🌊 [기관 오더플로우 집중 매집] 거래량 비율 3.62배 폭발 (+20점)",
    "🎯 [20일선 지지 반등] 20일 이동평균선 황금 맥점 지지 (+25점)"
]

receipt = TelegramReceiptGenerator.format_buy_receipt(
    symbol="MRK",
    quantity=1,
    price=135.16,
    setup="🚀 STRONG_BUY (기관 주도주 스윙 돌파)",
    score=100,
    sl_price=127.47,
    score_breakdown=score_breakdown,
    macro_regime="RISK_ON (성장/방어 순환매)"
)

success = notifier.send_sync(receipt)
print(f"MRK Detailed Report Sent to Telegram: {success}")
