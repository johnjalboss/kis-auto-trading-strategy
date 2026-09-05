"""
AI Trade Post-Mortem & Smart Journaling Engine (v1.0.0)
======================================================
Synthesizes trade entry conviction, holding price dynamics, and exit reasons.
Generates an executive 3-line Wall-Street post-mortem review via Gemini AI.
"""

import os
from typing import Dict, Any, Optional
from loguru import logger
import config

class AITradePostMortem:
    """Generates concise AI trade review notes upon trade completion."""

    def __init__(self):
        self.api_key = getattr(config, 'GEMINI_API_KEY', '')

    def generate_post_mortem(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        quantity: int,
        pnl: float,
        pnl_pct: float,
        reason: str,
        holding_days: int = 3,
        entry_score: int = 90
    ) -> str:
        """
        Generates a 3-bullet executive trade review (HTML formatted for Telegram).
        """
        is_win = pnl >= 0
        pnl_sign = "+" if is_win else ""
        pnl_tag = "수익 익절" if is_win else "손실 방어/손절"

        # Ensure valid holding days string
        if holding_days is not None and isinstance(holding_days, (int, float)) and holding_days > 0:
            h_days_str = f"{holding_days:.1f}일" if isinstance(holding_days, float) and holding_days % 1 != 0 else f"{int(holding_days)}일"
        elif isinstance(holding_days, str) and holding_days.strip():
            h_days_str = holding_days if "일" in holding_days else f"{holding_days}일"
        else:
            h_days_str = "약 3일"

        # 1. Try Gemini AI generation
        ai_review = ""
        if self.api_key:
            try:
                from gemini_client import get_gemini_client
                prompt = (
                    f"너는 세계 최정상 퀀트 트레이더이자 리스크 매니저야. "
                    f"방금 완료된 아래 실전 매매 건에 대해, 다음 3가지 항목으로 구성된 명쾌하고 전문적인 3줄 트레이딩 복기 노트를 작성해줘:\n\n"
                    f"종목: {symbol}\n"
                    f"진입가: ${entry_price:.2f} -> 청산가: ${exit_price:.2f}\n"
                    f"실현손익: {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_pct:.2f}%)\n"
                    f"청산 사유: {reason}\n"
                    f"보유 기간: {h_days_str}, 진입 시 퀀트 스코어: {entry_score}점\n\n"
                    f"작성 규칙:\n"
                    f"1) 정확히 3개 불릿으로 작성 (• 진입 평가: ... / • 보유 흐름: ... / • 청산 총평: ...)\n"
                    f"2) 헤지펀드 매니저 어조로, 승리 시에는 팩터 유효성을 칭찬하고 손실 시에는 리스크 방어 성과를 객관적으로 분석할 것\n"
                    f"3) 총 150자 내외로 매우 간결하게 작성"
                )
                ai_review = get_gemini_client(self.api_key).generate_text(prompt, temperature=0.2)
            except Exception as e:
                logger.debug("Gemini post-mortem generation failed: {}", e)

        # 2. Dynamic Rule-based Quant Fallback Heuristics
        if not ai_review:
            r_lower = reason.lower()
            if "dead_money" in r_lower:
                ai_review = (
                    f"• <b>진입 평가</b>: 고득점(Score: {entry_score}점) 셋업 진입 후 박스권 횡보 지속\n"
                    f"• <b>보유 흐름</b>: {h_days_str}간 추가 상승 모멘텀 둔화로 자금 회전율 저하 감지\n"
                    f"• <b>청산 총평</b>: 기회비용 최소화를 위한 예수금 조기 회수 및 호가 개선 익절({pnl_sign}{pnl_pct:.2f}%) 완수"
                )
            elif "profit_lock" in r_lower or "trailing" in r_lower:
                ai_review = (
                    f"• <b>진입 평가</b>: VCP 수축 돌파 및 잔차 모멘텀(Score: {entry_score}점) 황금 맥점 포착\n"
                    f"• <b>보유 흐름</b>: 고점 상승 후 변동성 조정에 따른 이익 보존선 접근\n"
                    f"• <b>청산 총평</b>: 샹들리에 트레일링 스탑 준수로 고점 부근 이익 보존({pnl_sign}{pnl_pct:.2f}%) 확정"
                )
            elif is_win:
                ai_review = (
                    f"• <b>진입 평가</b>: 5대 필라 종합 점수(Score: {entry_score}점) 우위 셋업 포착\n"
                    f"• <b>보유 흐름</b>: 20일선 지지를 받으며 시장 대비 초과 알파(Alpha)를 지속 발산\n"
                    f"• <b>청산 총평</b>: 목표 수익 도달에 따른 원칙적 분할/래칫 익절({pnl_sign}{pnl_pct:.2f}%) 성공적 완수"
                )
            else:
                ai_review = (
                    f"• <b>진입 평가</b>: 고득점({entry_score}점) 모멘텀 돌파 시도 후 단기 시장 변동성 직면\n"
                    f"• <b>보유 흐름</b>: 지수 급락에 따른 지지선 이탈 즉시 감지 및 리스크 통제\n"
                    f"• <b>청산 총평</b>: 사전 설정된 샹들리에 손절선 준수로 추가 하락 위험 사전 차단"
                )

        # Build card block
        post_mortem_block = (
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>[AI 퀀트 매매 복기 & 오답노트]</b>\n"
            f"{ai_review}"
        )
        return post_mortem_block

if __name__ == "__main__":
    pm = AITradePostMortem()
    print(pm.generate_post_mortem("VTOL", 45.92, 49.80, 5, 19.40, 8.45, "DYNAMIC_RATCHET_TAKE_PROFIT"))
