"""
Extended Hours Risk Sentinel (Pre-Market & After-Hours Emergency Defense)
========================================================================
Monitors open positions during Pre-Market (04:00-09:30 ET) and After-Hours (16:00-20:00 ET).
If a stock plunges >= 7.0% or hits catastrophic bad news during extended hours,
this module executes an immediate Extended Hours Exit to prevent -25% overnight disaster crashes!
"""

from datetime import datetime
import pytz
import kis_data as yf
from loguru import logger
import config

_EASTERN_TZ = pytz.timezone("US/Eastern")

class ExtendedHoursRiskSentinel:
    """Pre-Market and After-Hours Capital Protection Sentinel"""
    
    def __init__(self, trader=None, strategy=None):
        self.trader = trader
        self.strategy = strategy

    def get_current_market_session(self) -> str:
        """Determines current US trading session"""
        now_et = datetime.now(_EASTERN_TZ)
        time_et = now_et.time()
        weekday = now_et.weekday()

        if weekday >= 5:  # Weekend
            return "WEEKEND"

        from datetime import time as dt_time
        if dt_time(4, 0) <= time_et < dt_time(9, 30):
            return "PRE_MARKET"
        elif dt_time(9, 30) <= time_et < dt_time(16, 0):
            return "REGULAR"
        elif dt_time(16, 0) <= time_et <= dt_time(20, 0):
            return "AFTER_HOURS"
        else:
            return "OVERNIGHT_CLOSED"

    def check_extended_hours_emergency(self, symbol: str, entry_price: float, current_qty: int) -> dict:
        """Evaluates extended hours emergency gap-down liquidation risk"""
        res = {
            "should_liquidate": False,
            "reason": "",
            "session": self.get_current_market_session(),
            "extended_price": 0.0,
            "pnl_pct": 0.0
        }

        session = res["session"]
        if session not in {"PRE_MARKET", "AFTER_HOURS"}:
            return res

        try:
            # Fetch extended hours real-time price
            ticker = yf.Ticker(symbol)
            df_recent = ticker.history(period="1d", interval="1m")
            if df_recent.empty:
                return res

            ext_price = float(df_recent["Close"].iloc[-1])
            res["extended_price"] = ext_price

            if entry_price > 0 and ext_price > 0:
                pnl_pct = (ext_price - entry_price) / entry_price
                res["pnl_pct"] = pnl_pct

                # Emergency Gap-Down Threshold (-7.0% limit for extended hours)
                EXTENDED_STOP_LOSS_PCT = -0.070
                if pnl_pct <= EXTENDED_STOP_LOSS_PCT:
                    res["should_liquidate"] = True
                    res["reason"] = f"🚨 [{session}_GAP_DOWN_EMERGENCY] Stock dropped {pnl_pct*100:.2f}% (Price: ${ext_price:.2f} vs Entry: ${entry_price:.2f}) - Liquidating in extended hours to prevent -25% crash!"
                    logger.error(res["reason"])

                # Check Gemini AI News Emergency in Extended Hours
                try:
                    from gemini_news_sentinel import GeminiNewsSentinel
                    ai_news = GeminiNewsSentinel().analyze(symbol)
                    if ai_news.get("has_catastrophic_risk", False):
                        res["should_liquidate"] = True
                        res["reason"] = f"🚨 [{session}_AI_NEWS_DISASTER] {ai_news.get('catastrophic_reason')} - Liquidating immediately!"
                        logger.error(res["reason"])
                except Exception as _ai_err:
                    logger.debug("GeminiNewsSentinel check skipped: {}", _ai_err)

        except Exception as e:
            logger.debug(f"ExtendedHoursRiskSentinel check error for {symbol}: {e}")

        return res
