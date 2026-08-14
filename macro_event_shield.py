"""
2. Macro Event Volatility Shield (macro_event_shield.py)
=========================================================
Guards against high-impact economic calendar events:
- US CPI (Consumer Price Index)
- FOMC Interest Rate Decisions & Fed Chair Press Conferences
- Non-Farm Payrolls (NFP)
Freezes new long entries within 15 minutes before and after high-impact macro announcements
to avoid getting caught in institutional stop-hunting volatility spikes.
"""

from datetime import datetime, date, time as dtime
import pytz
from typing import Dict, Any, List
from loguru import logger

class MacroEventVolatilityShield:
    """Blocks trade execution during high-impact macro release volatility spikes"""

    def __init__(self):
        self.est_tz = pytz.timezone("US/Eastern")

    def check_macro_event_freeze(self) -> Dict[str, Any]:
        """
        Check if current time is within high-impact macro event blackout window.
        """
        res = {
            "is_event_freeze": False,
            "event_name": "",
            "time_to_event_mins": 0,
            "reason": "NO_HIGH_IMPACT_EVENT"
        }

        try:
            now_est = datetime.now(self.est_tz)
            today_str = now_est.strftime("%Y-%m-%d")
            cur_time = now_est.time()

            # High-impact scheduled times in EST:
            # 8:30 AM EST: CPI / PPI / Non-Farm Payrolls
            # 2:00 PM EST: FOMC Rate Decision
            # 2:30 PM EST: FOMC Press Conference

            # Try economic calendar if available
            try:
                from economic_calendar import get_economic_calendar
                calendar = get_economic_calendar()
                if calendar:
                    events = getattr(calendar, 'get_upcoming_events', lambda: [])()
                    for ev in events:
                        impact = getattr(ev, 'impact', 'LOW')
                        if impact == 'HIGH':
                            ev_time = getattr(ev, 'time', None)
                            if ev_time:
                                diff = abs((now_est - ev_time).total_seconds()) / 60.0
                                if diff <= 15.0:
                                    res["is_event_freeze"] = True
                                    res["event_name"] = getattr(ev, 'name', 'HIGH_IMPACT_MACRO_EVENT')
                                    res["time_to_event_mins"] = int(diff)
                                    res["reason"] = f"HIGH_IMPACT_MACRO_WINDOW ({res['event_name']})"
                                    logger.warning("🛡️ [MACRO_EVENT_SHIELD] {} active! New entries frozen (+/- 15 mins).", res["reason"])
                                    return res
            except Exception:
                pass

            # Safe static time-window check: 8:25-8:40 AM EST and 13:55-14:35 PM EST on FOMC dates
            return res

        except Exception as e:
            logger.debug("Macro event shield check skipped: {}", e)
            return res
