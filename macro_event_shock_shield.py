"""
Macro Event Shock Shield & Whipsaw Defense Engine (macro_event_shock_shield.py)
=============================================================================
Protects the portfolio from algorithmic whipsaws and spread blowouts around high-impact macro releases:
  - CPI (Consumer Price Index)
  - Core PPI (Producer Price Index)
  - FOMC Statement & Interest Rate Decision
  - FOMC Press Conference (Powell Speech)
  - Non-Farm Payrolls (NFP)
  - Core PCE Deflator

Actions during 30-Minute Blackout Window (T-15m to T+15m):
  1. Blocks new BUY entries (Freeze entries to prevent immediate fake breakouts)
  2. Adds a +1.0% temporary volatility cushion to Trailing Stops (Avoid 1-min noise stopouts)
  3. Preserves emergency stops and circuit breakers
"""

import os
import time
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple, Optional
import pytz
from loguru import logger

class MacroEventShockShield:
    """Institutional High-Impact Macro Shock & Whipsaw Protector"""

    def __init__(self, blackout_pre_min: int = 15, blackout_post_min: int = 15):
        self.pre_min = blackout_pre_min
        self.post_min = blackout_post_min
        self.et_tz = pytz.timezone("US/Eastern")
        self.kst_tz = pytz.timezone("Asia/Seoul")

    def _get_annual_event_schedule(self) -> List[Dict[str, Any]]:
        """
        Calculates/Loads the scheduled high-impact macro event calendar dynamically using calendar math.
        """
        from macro_event_horizon import get_dynamic_macro_calendar
        now_et = datetime.now(self.et_tz).date()
        base_events = get_dynamic_macro_calendar(now_et, months_ahead=3)
        events = []
        for ev in base_events:
            t_str = "14:00" if ev["type"] == "FOMC" else "08:30"
            events.append({
                "name": ev["name"],
                "date": ev["date"],
                "time_et": t_str,
                "impact": ev["impact"]
            })
            if ev["type"] == "FOMC":
                events.append({
                    "name": f"{ev['name']} 기자회견",
                    "date": ev["date"],
                    "time_et": "14:30",
                    "impact": ev["impact"]
                })
        return events

    def check_shock_shield_status(self) -> Dict[str, Any]:
        """
        Evaluates whether the current UTC/ET time is within the macro blackout window.
        """
        now_utc = datetime.now(pytz.utc)
        now_et = now_utc.astimezone(self.et_tz)
        schedule = self._get_annual_event_schedule()

        active_blackout = False
        active_event_name = ""
        minutes_to_event = 9999
        minutes_since_event = 9999
        upcoming_events = []

        for ev in schedule:
            try:
                ev_dt_str = f"{ev['date']} {ev['time_et']}"
                ev_dt_naive = datetime.strptime(ev_dt_str, "%Y-%m-%d %H:%M")
                ev_dt_et = self.et_tz.localize(ev_dt_naive)

                diff_sec = (ev_dt_et - now_et).total_seconds()
                diff_min = diff_sec / 60.0

                # Track upcoming events in next 7 days
                if 0 <= diff_min <= 7 * 24 * 60:
                    ev_kst = ev_dt_et.astimezone(self.kst_tz)
                    upcoming_events.append({
                        "name": ev["name"],
                        "time_kst": ev_kst.strftime("%m/%d %H:%M"),
                        "time_et": ev_dt_et.strftime("%m/%d %H:%M ET"),
                        "impact": ev["impact"],
                        "hours_left": round(diff_min / 60.0, 1)
                    })

                # Check Blackout Window: [-pre_min, +post_min]
                if -self.post_min <= diff_min <= self.pre_min:
                    active_blackout = True
                    active_event_name = ev["name"]
                    if diff_min >= 0:
                        minutes_to_event = int(diff_min)
                    else:
                        minutes_since_event = int(abs(diff_min))
            except Exception as e:
                logger.debug("Failed parsing macro event {}: {}", ev, e)

        # Sort upcoming events chronologically
        upcoming_events.sort(key=lambda x: x["hours_left"])

        # Extra Stop-Loss Volatility Buffer
        # If in blackout or within 1 hour of CPI/FOMC, provide +1.0% stop cushion
        stop_cushion_pct = 0.010 if active_blackout else 0.0

        if active_blackout:
            if minutes_to_event != 9999:
                reason = f"🚨 [{active_event_name}] 발표 {minutes_to_event}분 전 -> 휩소 방어 신규 매수 동결"
            else:
                reason = f"🚨 [{active_event_name}] 발표 직후 ({minutes_since_event}분 경과) -> 시장 안정화 대기"
        else:
            reason = "✅ 거시경제 지표 안전 구간 (매매 정상 허용)"

        return {
            "is_blackout_active": active_blackout,
            "active_event_name": active_event_name,
            "minutes_to_event": minutes_to_event if minutes_to_event != 9999 else None,
            "minutes_since_event": minutes_since_event if minutes_since_event != 9999 else None,
            "stop_cushion_pct": stop_cushion_pct,
            "reason": reason,
            "upcoming_events": upcoming_events[:4],
            "evaluated_at": now_et.strftime("%Y-%m-%d %H:%M:%S ET")
        }

    def format_telegram_card(self) -> str:
        """Formats the Macro Event Shock Shield card for Telegram"""
        st = self.check_shock_shield_status()
        
        status_tag = "🔴 <b>신규 매수 일시 동결 (SHOCK SHIELD ACTIVE)</b>" if st["is_blackout_active"] else "🟢 <b>정상 매매 허용 (안전 구간)</b>"

        buffer_desc = "<code>+0.0%</code> (평시 정상 상태)" if not st["is_blackout_active"] else "<code>+1.0%</code> 🛡️ (지표 발표 알고리즘 휩소 방어 쿠션 작동 중)"

        lines = [
            "⏰ <b>[거시경제 지표 발표 충격 쉴드 리포트]</b>",
            "<i>Macro Shock & Whipsaw Anti-Spike Sentinel</i>",
            "━━━━━━━━━━━━━━━━━━━",
            f"🛡️ <b>현재 상태:</b> {status_tag}",
            f"📝 <b>진단:</b> <i>{st['reason']}</i>",
            f"⚡️ <b>스탑로스 완충 버퍼:</b> {buffer_desc}",
            "━━━━━━━━━━━━━━━━━━━",
            "📅 <b>다가오는 핵심 거시 이벤트 (D-7)</b>:"
        ]

        if st["upcoming_events"]:
            for ev in st["upcoming_events"]:
                lines.append(f"  • <b>{ev['name']}</b> [{ev['impact']}]\n    🕒 {ev['time_kst']} (KST) | {ev['hours_left']:.1f}시간 후")
        else:
            lines.append("  • <i>7일 이내 예정된 초특급 충격 이벤트 없음</i>")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>CPI/FOMC 지표 발표 전후 15분간 알고리즘 휩소(1분봉 급등락) 방어를 위해 신규 매수를 동결하고 스탑로스를 +1.0% 임시 완충합니다.</i>")

        return "\n".join(lines)

if __name__ == "__main__":
    shield = MacroEventShockShield()
    res = shield.check_shock_shield_status()
    print("Macro Event Shock Shield Status:\n", json.dumps(res, indent=2, ensure_ascii=False))
    print("\nTelegram Card:\n", shield.format_telegram_card())
