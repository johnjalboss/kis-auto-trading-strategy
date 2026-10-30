"""
[v7.0 PRE-EARNINGS RISK SHIELD & CUT MODULE]
Queries Yahoo Finance earnings calendar using US Eastern market date.

Rules:
1. HARD BLOCK (NEW): If earnings within 5 calendar days → 'entry_blocked' = True.
   This is an absolute veto regardless of score. Score penalty alone (-50) was
   insufficient because a +100 signal could still pass as +50.
2. Entry Score Penalty: If earnings within 5 days, score_adj = -999 (effectively blocks new entries).
3. Pre-Earnings Position Trimming: If holding a position and upcoming earnings is within 0~2 days,
   trigger risk cut exit (handled by OvernightRiskAssessor).
4. Past Earnings: If earnings date has already passed (days_diff < 0), it is NOT in danger.
5. POST-EARNINGS COOLDOWN (NEW): After OVERNIGHT_RISK_DEFENSE exit triggered by earnings,
   block re-entry into the same symbol for 2 calendar days to prevent buy→sell→buy loop.
"""

import time
import datetime
from typing import Dict, Any
from loguru import logger
import yfinance as yf
import pytz

_EARNINGS_SHIELD_CACHE = {}
_CACHE_TTL = 7200  # 2 hours

# Post-earnings-exit cooldown: symbol -> UTC timestamp of OVERNIGHT_RISK_DEFENSE exit
# Block re-entry for 2 calendar days after being forced out due to earnings
_POST_EARNINGS_EXIT_COOLDOWN: dict = {}
_POST_EARNINGS_COOLDOWN_DAYS = 2


def record_earnings_exit(symbol: str):
    """
    Call this when OVERNIGHT_RISK_DEFENSE triggers on a symbol.
    Prevents re-entry for _POST_EARNINGS_COOLDOWN_DAYS calendar days.
    """
    import time as _time
    _POST_EARNINGS_EXIT_COOLDOWN[symbol] = _time.time()
    logger.info("🛡️ [PRE_EARNINGS_COOLDOWN] {} marked for {}-day re-entry block after earnings exit.",
                symbol, _POST_EARNINGS_COOLDOWN_DAYS)


def is_post_earnings_cooldown(symbol: str) -> tuple:
    """
    Returns (blocked: bool, reason: str).
    True if symbol was recently force-sold due to earnings and cooldown period not yet elapsed.
    """
    import time as _time
    ts = _POST_EARNINGS_EXIT_COOLDOWN.get(symbol)
    if ts is None:
        return False, ''
    elapsed_days = (_time.time() - ts) / 86400.0
    if elapsed_days < _POST_EARNINGS_COOLDOWN_DAYS:
        remaining = _POST_EARNINGS_COOLDOWN_DAYS - elapsed_days
        return True, f"POST_EARNINGS_COOLDOWN: {symbol} force-sold due to earnings {elapsed_days:.1f}d ago. Re-entry blocked for {remaining:.1f}d more."
    # Cooldown expired - clean up
    del _POST_EARNINGS_EXIT_COOLDOWN[symbol]
    return False, ''


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
            'entry_blocked': False,        # NEW: hard veto flag (True = no entry allowed regardless of score)
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

                        if 0 <= days_diff <= 5:
                            # HARD BLOCK: earnings within 5 calendar days
                            # -999 score ensures signal never passes even at +100 composite score.
                            # entry_blocked=True is checked directly in orchestrator as absolute veto.
                            res['is_pre_earnings_danger'] = True
                            res['entry_blocked'] = True
                            res['score_adj'] = -999
                            res['reason'] = (
                                f"PRE_EARNINGS_HARD_BLOCK: Earnings in {days_diff}d ({e_date}). "
                                f"New entries PROHIBITED within 5d of earnings to avoid binary event risk."
                            )
                            logger.info("🚫 [PRE_EARNINGS_BLOCK] {}: Earnings in {}d ({}) — entry hard-blocked.",
                                        symbol, days_diff, e_date)
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
