"""
[v6.1 PRE-EARNINGS RISK SHIELD & CUT MODULE]
Queries Yahoo Finance / Finnhub earnings calendar using US Eastern market date.

Rules:
1. Entry Prohibition: If upcoming earnings is within 0~3 days, return -50 pts (prohibits new entries).
2. Pre-Earnings Position Trimming: If holding a position and upcoming earnings is within 0~2 days, trigger risk cut exit.
3. Past Earnings: If earnings date has already passed (days_diff < 0), it is NOT in danger.
"""

import time
import datetime
from typing import Dict, Any
from loguru import logger
import yfinance as yf
import pytz

_EARNINGS_SHIELD_CACHE = {}
_CACHE_TTL = 7200  # 2 hours


def _get_us_market_date() -> datetime.date:
    """Returns current date in US Eastern Time (market date)."""
    try:
        return datetime.datetime.now(pytz.timezone('US/Eastern')).date()
    except Exception:
        return datetime.date.today()


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
            
            if cal is not None and not (hasattr(cal, 'empty') and cal.empty):
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
                        today = _get_us_market_date()
                        days_diff = (e_date - today).days

                        res['days_to_earnings'] = days_diff

                        if 0 <= days_diff <= 3:
                            res['is_pre_earnings_danger'] = True
                            res['score_adj'] = -50
                            res['reason'] = f"PRE_EARNINGS_DANGER: Earnings in {days_diff}d ({e_date})"
                        elif days_diff < 0:
                            res['is_pre_earnings_danger'] = False
                            res['score_adj'] = 0
                            res['reason'] = f"EARNINGS_PASSED: Reported {abs(days_diff)}d ago ({e_date})"

            _EARNINGS_SHIELD_CACHE[symbol] = (now, res)
            return res
        except Exception as e:
            logger.debug("PreEarningsShield failed for {}: {}", symbol, e)
            _EARNINGS_SHIELD_CACHE[symbol] = (now, res)
            return res
