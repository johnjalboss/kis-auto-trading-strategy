"""
Monthly OpEx & Quadruple Witching Gamma Pin Sentinel (opex_gamma_pin_sentinel.py)
==================================================================================
Monitors Monthly Options Expiration (3rd Friday of every month) and
Quarterly Quadruple Witching Days (March, June, September, December 3rd Friday).

Market Microstructure Mechanics:
1. OpEx Week (Monday to Friday of 3rd Friday week):
   - Option Market Makers have massive gamma exposure.
   - They delta-hedge by aggressively pinning the index/equities near Max Pain strike prices.
   - Volatility is compressed until Friday 14:00 ET.
2. Post-OpEx Unpinning Surge / Breakdown (Friday 15:30 ET to following Monday):
   - Trillions in expired options are cleared from the tape.
   - Gamma pin collapses, unleashing explosive multi-day directional momentum waves.

Signal:
- "OPEX_PIN_COMPRESSION": Wednesday-Friday of OpEx week (avoid chasing breakouts before unpinning).
- "QUADRUPLE_WITCHING_ALERT": March/June/Sept/Dec OpEx week (Trillion-dollar institutional rebalancing).
- "POST_OPEX_UNPINNING_SURGE": Monday after OpEx (High momentum breakout boost +10 pts).
"""

import time
from datetime import datetime, date, timedelta
import pytz
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from loguru import logger

_EASTERN_TZ = pytz.timezone("US/Eastern")
_OPEX_CACHE = {}


@dataclass
class OpExSignal:
    current_date: date
    is_opex_week: bool
    is_quadruple_witching: bool
    days_to_third_friday: int
    opex_phase: str            # "NORMAL_TRADING", "OPEX_PIN_COMPRESSION", "POST_OPEX_UNPINNING_SURGE"
    score_adj: int             # -5 to +10 pts
    guidance: str


class OpExGammaPinSentinel:
    """Detects Options Expiration cycles, Gamma Pinning, and Quadruple Witching."""

    @staticmethod
    def get_third_friday(year: int, month: int) -> date:
        """Finds the 3rd Friday of a given month."""
        # 1st day of month
        first_day = date(year, month, 1)
        # Friday is weekday 4 (Monday is 0)
        first_friday_offset = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=first_friday_offset)
        # 3rd Friday is 14 days later
        return first_friday + timedelta(days=14)

    def evaluate_cycle(self, target_dt: Optional[datetime] = None) -> OpExSignal:
        now_et = target_dt or datetime.now(_EASTERN_TZ)
        today = now_et.date()

        third_friday = self.get_third_friday(today.year, today.month)
        is_quad = today.month in (3, 6, 9, 12)

        days_to_opex = (third_friday - today).days

        is_opex_week = False
        opex_phase = "NORMAL_TRADING"
        score_adj = 0
        guidance = "Normal non-OpEx market conditions."

        if 0 <= days_to_opex <= 4 and today.weekday() <= 4:
            is_opex_week = True
            if days_to_opex <= 2:  # Wednesday to Friday
                opex_phase = "OPEX_PIN_COMPRESSION"
                score_adj = -3  # Mild penalty against breakout chasing during gamma pin
                guidance = (
                    f"⚠️ [OPEX_GAMMA_PIN] Monthly Options Expiration in {days_to_opex} days. "
                    f"Market makers pinning strikes near Max Pain. Expect choppy volatility compression."
                )
            else:
                opex_phase = "OPEX_WEEK_EARLY"
                guidance = f"📅 OpEx week active (Friday: {third_friday.strftime('%Y-%m-%d')})."
        elif days_to_opex in (-1, -2, -3):  # Weekend / Monday right after OpEx
            opex_phase = "POST_OPEX_UNPINNING_SURGE"
            score_adj = +10
            guidance = "🚀 [POST_OPEX_UNPINNING] Options pin released! Explosive directional trend waves unlocked (+10 pts)."

        if is_quad and is_opex_week:
            guidance += " 🏛️ [QUADRUPLE_WITCHING] Massive quarterly index futures & options rebalancing."

        return OpExSignal(
            current_date=today,
            is_opex_week=is_opex_week,
            is_quadruple_witching=is_quad,
            days_to_third_friday=days_to_opex,
            opex_phase=opex_phase,
            score_adj=score_adj,
            guidance=guidance
        )


def get_opex_sentinel() -> OpExGammaPinSentinel:
    return OpExGammaPinSentinel()
