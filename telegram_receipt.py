"""
Telegram Order Receipt Card Generator (telegram_receipt.py)
=============================================================
Generates rich, visual HTML receipt cards for Telegram upon BUY and SELL order executions.
"""

from typing import Dict, Any
from datetime import datetime


class TelegramReceiptGenerator:
    """Formats rich Telegram notification cards for order fills."""

    @staticmethod
    def format_buy_receipt(symbol: str, quantity: int, price: float, setup: str = "QUANT_BREAKOUT",
                           tp_price: float = 0.0, sl_price: float = 0.0) -> str:
        total_cost = quantity * price
        tp_str = f"${tp_price:.2f} (+15.0%)" if tp_price > 0 else f"${price * 1.15:.2f} (+15.0%)"
        sl_str = f"${sl_price:.2f} (-4.5%)" if sl_price > 0 else f"${price * 0.955:.2f} (-4.5%)"

        receipt = (
            f"🎟️ <b>[AI 매수 체결 영수증]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>종목코드</b>: <code>{symbol}</code>\n"
            f"• <b>체결수량</b>: <b>{quantity:,} 주</b>\n"
            f"• <b>체결단가</b>: <b>${price:,.2f}</b>\n"
            f"• <b>총 매수금액</b>: <b>${total_cost:,.2f}</b>\n"
            f"• <b>진입전략</b>: <code>{setup}</code>\n"
            f"──────────────────────\n"
            f"🎯 <b>목표 익절가</b>: <b>{tp_str}</b>\n"
            f"🛡️ <b>안전 손절가</b>: <b>{sl_str}</b>\n"
            f"⏰ <b>체결시각</b>: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>실시간 대시보드</b>: https://dee-merger-endorsed-sas.trycloudflare.com"
        )
        return receipt

    @staticmethod
    def format_sell_receipt(symbol: str, quantity: int, entry_price: float, exit_price: float,
                            reason: str = "PROFIT_TARGET", hold_days: int = 1) -> str:
        total_value = quantity * exit_price
        pnl_usd = (exit_price - entry_price) * quantity
        pnl_pct = ((exit_price - entry_price) / entry_price * 100.0) if entry_price > 0 else 0.0

        sign = "🟢" if pnl_usd >= 0 else "🔴"
        pnl_badge = f"{sign} <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)"

        receipt = (
            f"🧾 <b>[AI 매도 청산 영수증]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>종목코드</b>: <code>{symbol}</code>\n"
            f"• <b>청산수량</b>: <b>{quantity:,} 주</b>\n"
            f"• <b>진입평단</b>: ${entry_price:,.2f}\n"
            f"• <b>청산단가</b>: <b>${exit_price:,.2f}</b>\n"
            f"• <b>총 회수금액</b>: <b>${total_value:,.2f}</b>\n"
            f"──────────────────────\n"
            f"💰 <b>실현손익</b>: {pnl_badge}\n"
            f"📌 <b>청산사유</b>: <code>{reason}</code>\n"
            f"⏱️ <b>보유기간</b>: <b>{hold_days} 일</b>\n"
            f"⏰ <b>청산시각</b>: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} EST</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>실시간 대시보드</b>: https://dee-merger-endorsed-sas.trycloudflare.com"
        )
        return receipt
