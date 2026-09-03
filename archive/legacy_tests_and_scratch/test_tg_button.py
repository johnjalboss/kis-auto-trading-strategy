#!/usr/bin/env python3
"""Send complete 18-button menu including chart buttons directly to Telegram."""
import os, json, requests, sys
sys.path.insert(0, "/home/ubuntu/kis-auto-trading")
os.chdir("/home/ubuntu/kis-auto-trading")

from dotenv import load_dotenv
load_dotenv(".env")

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

print(f"Token (last 5): ...{token[-5:]}")
print(f"Chat ID: {chat_id}")

if not token or not chat_id:
    print("ERROR: Token or Chat ID missing!")
    sys.exit(1)

url = f"https://api.telegram.org/bot{token}/sendMessage"
menu_text = (
    "📋 <b>AI 스윙 봇 인터랙티브 제어판</b> [✅ 정상 가동]\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "원하시는 버튼을 터치하시면 실시간 상태, 성과, 차트, 추천주,\n"
    "리스크 제어가 즉시 실행됩니다.\n\n"
    "🌐 <b>실시간 웹 대시보드 주소</b>:\nhttps://dee-merger-endorsed-sas.trycloudflare.com"
)

reply_markup = {
    "inline_keyboard": [
        [
            {"text": "🌐 실시간 웹 대시보드 열기", "url": "https://dee-merger-endorsed-sas.trycloudflare.com"}
        ],
        [
            {"text": "📊 봇 상태 요약", "callback_data": "cmd_status"},
            {"text": "📈 보유 포지션", "callback_data": "cmd_positions"}
        ],
        [
            {"text": "💰 오늘 실현손익", "callback_data": "cmd_today_pnl"},
            {"text": "📅 7일 누적성과", "callback_data": "cmd_weekly_pnl"}
        ],
        [
            {"text": "📅 30일 월간성과", "callback_data": "cmd_monthly_pnl"},
            {"text": "🏆 전체 누적성과", "callback_data": "cmd_total_pnl"}
        ],
        [
            {"text": "🔥 테마 1등주", "callback_data": "cmd_theme"},
            {"text": "🎯 스크리너 픽", "callback_data": "cmd_screener"}
        ],
        [
            {"text": "🌐 시장 레짐", "callback_data": "cmd_regime"},
            {"text": "🛡️ 리스크 현황", "callback_data": "cmd_risk"}
        ],
        [
            {"text": "📊 30일 차트", "callback_data": "cmd_chart30"},
            {"text": "📊 90일 차트", "callback_data": "cmd_chart90"}
        ],
        [
            {"text": "📊 180일 차트", "callback_data": "cmd_chart180"},
            {"text": "📊 1년 차트", "callback_data": "cmd_chart365"}
        ],
        [
            {"text": "📊 전체 수익차트", "callback_data": "cmd_chart_all"}
        ],
        [
            {"text": "⏸️ 매수 일시정지", "callback_data": "cmd_pause"},
            {"text": "▶️ 매수 재개", "callback_data": "cmd_resume"}
        ],
        [
            {"text": "🚨 보유 종목 전량 긴급 청산", "callback_data": "cmd_close_all"}
        ]
    ]
}

payload = {
    "chat_id": chat_id,
    "text": menu_text,
    "parse_mode": "HTML",
    "reply_markup": reply_markup
}

resp = requests.post(url, json=payload, timeout=10)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
