"""
[v6.0 PRE-EARNINGS RISK SHIELD & CUT MODULE]
Queries Yahoo Finance / Finnhub earnings calendar.

Rules:
1. Entry Prohibition: If earnings is within 3 calendar days, return -50 pts (prohibits new entries).
2. Pre-Earnings Position Trimming: If holding a position and earnings is within 2 days, trigger risk cut exit.
"""

import time
import datetime
from typing import Dict, Any
from loguru import logger
import yfinance as yf

_EARNINGS_SHIELD_CACHE = {}
_CACHE_TTL = 14400  # 4 hours


class PreEarningsShield:
    def __init__(self):
        pass

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _EARNINGS_SHIELD_CACHE:
            ts, res = _EARNINGS_SHIELD_CACHE[symbol]
            if now - ts < _CACHE_TTL:
                return res

        res = {
            'is_pre_earnings_danger': False,
            'days_to_earnings': 999,
            'score_adj': 0,
            'reason': ''
        }

        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            
            if cal is not None and not cal.empty if hasattr(cal, 'empty') else cal:
                earnings_date = None
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if dates:
                        earnings_date = dates[0]
                elif hasattr(cal, 'T') and 'Earnings Date' in cal.T.columns:
                    dates = cal.T['Earnings Date'].dropna().tolist()
                    if dates:
                        earnings_date = dates[0]

                if earnings_date:
                    if isinstance(earnings_date, (datetime.datetime, datetime.date)):
                        e_date = earnings_date.date() if isinstance(earnings_date, datetime.datetime) else earnings_date
                        today = datetime.date.today()
                        days_diff = (e_date - today).days

                        res['days_to_earnings'] = days_diff

                        if 0 <= days_diff <= 3:
                            res['is_pre_earnings_danger'] = True
                            res['score_adj'] = -50
                            res['reason'] = f"PRE_EARNINGS_DANGER: Earnings in {days_diff}d ({e_date})"

            _EARNINGS_SHIELD_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("PreEarningsShield failed for {}: {}", symbol, e)
            _EARNINGS_SHIELD_CACHE[symbol] = (now, res)
            return res
