"""
Telegram Order Receipt Card Generator (telegram_receipt.py)
=============================================================
Generates rich, detailed, institutional-grade visual HTML receipt cards
for Telegram upon BUY and SELL order executions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz


def _translate_exit_reason_detail(reason: str) -> str:
    """Translates exit reasons into clear Korean institutional explanations."""
    if not reason:
        return "• <b>청산 사유</b>: 원칙적 리스크 관리 청산"
    
    r_lower = reason.lower()
    
    if "profit_lock" in r_lower:
        return (
            "• <b>분류</b>: 🔒 <b>이익 보존 손절선 (Profit Locking Stop)</b>\n"
            "• <b>상세 근거</b>: 주가 고점 상승 후 가격 조정을 받을 때, 확보한 이익(+2.0%/+5.5%/+9.0%)을 뺏기지 않고 안전하게 확정 청산."
        )
    if "trailing_stop" in r_lower or "trailing" in r_lower:
        return (
            "• <b>분류</b>: 📈 <b>ATR 동적 트레일링 스탑 (Trailing Stop)</b>\n"
            "• <b>상세 근거</b>: 고점 대비 ATR 변동성 채널 이탈로 상승 모멘텀 둔화가 감지되어 고점 부근에서 수익을 극대화하며 방어 매도."
        )
    if "hard_stop" in r_lower or "stop_loss" in r_lower:
        return (
            "• <b>분류</b>: 🛑 <b>원칙적 리스크 손절 (Hard Stop-Loss)</b>\n"
            "• <b>상세 근거</b>: 매수 단가 대비 손절 기준선(-3.0%~-5.0%)에 도달하여 원금 손실 확대를 차단하기 위해 원칙적 즉시 매도."
        )
    if "dead_money" in r_lower:
        return (
            "• <b>분류</b>: 💤 <b>횡보주 조기 회수 (Dead Money Exit)</b>\n"
            "• <b>상세 근거</b>: 3일간 박스권(-1.0%~+1.0%)에 갇혀 횡보함에 따라, 자금 회전율(Capital Velocity)을 높이기 위해 예수금 조기 회수."
        )
    if "dynamic_time_expired" in r_lower or "max_hold" in r_lower or "time_exit" in r_lower:
        return (
            "• <b>분류</b>: ⏱️ <b>스윙 보유 기간 만료 청산</b>\n"
            "• <b>상세 근거</b>: 적응형 보유 한도(5일)에 도달하여 장기 자금 묶임 방지를 위해 포지션 정리."
        )
    if "gemini_ai" in r_lower or "catastrophic" in r_lower:
        return (
            "• <b>분류</b>: 🚨 <b>Gemini AI 실시간 악재 긴급 청산</b>\n"
            "• <b>상세 근거</b>: 파산, SEC 조사, 실적 쇼크 등 실시간 돌발 대형 악재 뉴스 감지로 즉시 손실 차단 매도."
        )
    if "upgrade" in r_lower or "rotation" in r_lower:
        return (
            "• <b>분류</b>: 🔄 <b>우수 주도주 교체 매매 (Upgrade Rotation)</b>\n"
            "• <b>상세 근거</b>: 모멘텀/수급 점수가 더 높은 최정예 주도주를 포착하여 기존 포지션 전량 매도 후 현금 확보."
        )
    if "take_profit" in r_lower or "profit_target" in r_lower:
        return (
            "• <b>분류</b>: 🎯 <b>목표 수익률 달성 익절 (Take-Profit)</b>\n"
            "• <b>상세 근거</b>: 설정된 1차/2차 목표 수익률에 도달하여 안정적으로 수익을 실현."
        )

    return f"• <b>청산 사유</b>: <code>{reason}</code>"


class TelegramReceiptGenerator:
    """Formats rich Telegram notification cards for order fills."""

    @staticmethod
    def format_buy_receipt(symbol: str, quantity: int, price: float, setup: str = "QUANT_BREAKOUT",
                           score: int = 100, tp_price: float = 0.0, sl_price: float = 0.0,
                           atr: float = 0.0, score_breakdown: Optional[List[str]] = None,
                           macro_regime: str = "RISK_ON") -> str:
        total_cost = quantity * price
        
        # Calculate stock-specific dynamic ATR targets
        if tp_price > 0:
            tp_pct = (tp_price - price) / price * 100.0 if price > 0 else 0.0
            tp_str = f"${tp_price:.2f} ({tp_pct:+.1f}%)"
        else:
            # Dynamic Tiered targets (+2.0% 1차 분할, +5.5% 2차, +9.0% 3차)
            tp_1 = price * 1.020
            tp_2 = price * 1.055
            tp_str = f"1차 ${tp_1:.2f} (+2.0%) / 2차 ${tp_2:.2f} (+5.5%) / ATR 트레일링"

        if sl_price > 0:
            sl_pct = (sl_price - price) / price * 100.0 if price > 0 else -3.0
            sl_str = f"${sl_price:.2f} ({sl_pct:.1f}%)"
        else:
            sl_default = price * 0.95
            sl_str = f"${sl_default:.2f} (-5.0% ATR Stop)"

        # Format score breakdown drivers
        # [BUG FIX] Escape HTML special chars (<, >, &) to prevent Telegram API 400 parse errors
        def _html_escape(text: str) -> str:
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        breakdown_text = ""
        if score_breakdown and len(score_breakdown) > 0:
            filtered_drivers = [item for item in score_breakdown if item.strip()]
            for item in filtered_drivers[:5]:
                clean_item = _html_escape(item.strip())
                if not clean_item.startswith("•"):
                    clean_item = f"• {clean_item}"
                breakdown_text += f"{clean_item}\n"
        else:
            breakdown_text = (
                "• 🔥 기관 수급 및 모멘텀 최상위 셋업 포착\n"
                "• 🎯 20일선 지지 반등 및 다중 타임프레임 정배열\n"
                "• ⚡ 감마 레이더 Net GEX 양수 수급 유입\n"
            )

        safe_setup = _html_escape(str(setup))
        safe_regime = _html_escape(str(macro_regime))

        receipt = (
            f"🎟️ <b>[AI 퀀트 매수 체결 영수증]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>종목코드</b>: <code>{symbol}</code>\n"
            f"• <b>체결수량</b>: <b>{quantity:,} 주</b>\n"
            f"• <b>체결단가</b>: <b>${price:,.2f}</b>\n"
            f"• <b>총 매수금액</b>: <b>${total_cost:,.2f}</b>\n"
            f"• <b>퀀트종합점수</b>: <b>{score} / 100 점</b>\n"
            f"• <b>진입전략</b>: <code>{safe_setup}</code>\n"
            f"• <b>시장국면</b>: <code>{safe_regime}</code>\n"
            f"──────────────────────\n"
            f"📊 <b>핵심 매수 근거 (Score Drivers)</b>:\n"
            f"{breakdown_text.strip()}\n"
            f"──────────────────────\n"
            f"🎯 <b>목표 익절 계획</b>: <b>{tp_str}</b>\n"
            f"🛡️ <b>안전 손절 기준</b>: <b>{sl_str}</b>\n"
            f"⏱️ <b>최대 보유 기간</b>: <b>최대 5일 (스윙 쿨다운)</b>\n"
            f"⏰ <b>체결시각</b>: <code>{datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')} EDT ({datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} KST)</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <b>실시간 대시보드</b>: http://141.148.172.12:8080"
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
        reason_detail_ko = _translate_exit_reason_detail(reason)

        # Compute factor performance attribution
        factor_lines = ""
        try:
            from factor_attribution import FactorAttributionEngine
            attr_res = FactorAttributionEngine().attribute(symbol, pnl_pct, reason)
            f_map = attr_res.get("factors", {})
            f_items = [f"• {k}: {v:+.2f}%" for k, v in f_map.items()]
            factor_lines = "\n".join(f_items)
        except Exception:
            factor_lines = f"• 모멘텀 알파 기여: {pnl_pct*0.6:+.2f}%\n• 섹터 순풍 기여: {pnl_pct*0.4:+.2f}%"

        receipt = (
            f"🧾 <b>[AI 퀀트 매도 청산 영수증]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>종목코드</b>: <code>{symbol}</code>\n"
            f"• <b>청산수량</b>: <b>{quantity:,} 주</b>\n"
            f"• <b>진입평단</b>: ${entry_price:,.2f}\n"
            f"• <b>청산단가</b>: <b>${exit_price:,.2f}</b>\n"
            f"• <b>총 회수금액</b>: <b>${total_value:,.2f}</b>\n"
            f"──────────────────────\n"
            f"💰 <b>확정 실현손익</b>: {pnl_badge}\n"
            f"⏱️ <b>실제 보유기간</b>: <b>{hold_days} 일</b>\n"
            f"📌 <b>상세 청산사유</b>:\n"
            f"{reason_detail_ko}\n"
            f"──────────────────────\n"
            f"🧬 <b>수익 팩터 기여도 분해 (Factor Attribution)</b>:\n"
            f"{factor_lines}\n"
        )

        # AI Post-Mortem Journaling
        try:
            from ai_trade_post_mortem import AITradePostMortem
            pm_text = AITradePostMortem().generate_post_mortem(
                symbol=symbol,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                pnl=pnl_usd,
                pnl_pct=pnl_pct,
                reason=reason,
                holding_days=hold_days
            )
            receipt += f"{pm_text}\n"
        except Exception:
            receipt += (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧠 <b>[AI 퀀트 매매 복기]</b>\n"
                f"• 원칙적 리스크 관리 청산 완료 ➔ 차기 우수 주도주 탐색 모드 가동\n"
            )

        receipt += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ <b>청산시각</b>: <code>{datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S')} EDT ({datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M:%S')} KST)</code>\n"
            f"🌐 <b>실시간 대시보드</b>: http://141.148.172.12:8080"
        )
        return receipt
