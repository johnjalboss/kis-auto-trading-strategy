"""
[v8.0 24/7 PHASE-SPECIFIC MULTI-SESSION RADAR]
Tailors trading rules & confidence thresholds to US Market Sessions:

1. PRE_MARKET (04:00 - 09:30 EST / 17:00 - 22:30 KST):
   - Pre-market Gap Up & Volume Surge (+15 pts for pre-market RVOL > 3.0x).
2. REGULAR_MARKET (09:30 - 15:30 EST / 22:30 - 04:30 KST):
   - Full Options Call/Put Wall + Volume Profile POC + 1H Intraday Alignment.
3. POWER_HOUR_CLOSING (15:30 - 16:00 EST / 04:30 - 05:00 KST):
   - MOC (Market on Close) Institutional Accumulation (+10 pts for day's high closing).
"""

import datetime
import pytz
from typing import Dict, Any
from loguru import logger


class SessionRadar:
    def __init__(self):
        pass

    def get_current_session_info(self) -> Dict[str, Any]:
        res = {
            'session': 'REGULAR_MARKET',
            'score_adj': 0,
            'reason': ''
        }
        try:
            et = pytz.timezone('US/Eastern')
            now_et = datetime.datetime.now(et)
            t = now_et.time()
            weekday = now_et.weekday()

            if weekday >= 5:  # Weekend
                res['session'] = 'WEEKEND'
                res['reason'] = 'WEEKEND_CLOSED'
                return res

            pre_start = datetime.time(4, 0)
            reg_start = datetime.time(9, 30)
            power_start = datetime.time(15, 30)
            reg_end = datetime.time(16, 0)
            post_end = datetime.time(20, 0)

            if pre_start <= t < reg_start:
                res['session'] = 'PRE_MARKET'
                res['score_adj'] = 5
                res['reason'] = 'PRE_MARKET_GAP_RADAR_ACTIVE'
            elif reg_start <= t < power_start:
                res['session'] = 'REGULAR_MARKET'
                res['score_adj'] = 0
                res['reason'] = 'REGULAR_MARKET_FULL_INSPECTION'
            elif power_start <= t < reg_end:
                res['session'] = 'POWER_HOUR_CLOSING'
                res['score_adj'] = 8
                res['reason'] = 'POWER_HOUR_MOC_ACCUMULATION'
            elif reg_end <= t <= post_end:
                res['session'] = 'AFTER_HOURS'
                res['score_adj'] = 0
                res['reason'] = 'AFTER_HOURS_MONITORING'
            else:
                res['session'] = 'OVERNIGHT'
                res['reason'] = 'OVERNIGHT_CLOSED'

            return res
        except Exception as e:
            logger.debug("SessionRadar failed: {}", e)
            return res
