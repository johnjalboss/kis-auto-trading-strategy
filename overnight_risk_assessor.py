"""
Overnight Risk Assessor (overnight_risk_assessor.py)
===================================================
Evaluates overnight holding risk for open positions before US market close (04:30 - 05:00 KST).
Prevents holding into gap-down landmines (pre-market earnings, broken closing technicals, FOMC/CPI shocks).
"""

from typing import Dict, Any, List
from loguru import logger
import pandas as pd
import kis_data

class OvernightRiskAssessor:
    """Institutional Overnight Risk & Gap-Down Protection Evaluator"""

    def __init__(self):
        pass

    def evaluate_position_overnight(self, symbol: str, current_price: float, entry_price: float) -> Dict[str, Any]:
        """
        Evaluates whether a stock is safe to hold overnight.
        Returns safety_score (0-100), warnings list, and should_close_before_bell (bool).
        """
        safety_score = 100
        warnings = []
        should_close = False

        try:
            # 1. Technical Health at Close (Daily OHLCV)
            df = kis_data.get_daily_ohlcv(symbol, days=30)
            if df is not None and not df.empty and len(df) >= 20:
                sma20 = float(df['Close'].rolling(20).mean().iloc[-1])
                today_low = float(df['Low'].iloc[-1])
                curr_close = current_price or float(df['Close'].iloc[-1])

                # Heavy breakdown below SMA20 (-2.5% below)
                if curr_close < sma20 * 0.975:
                    safety_score -= 30
                    warnings.append(f"Broken 20d SMA Support (${sma20:.2f})")
                    logger.warning("⚠️ [OVERNIGHT_WARN] {}: Broken 20d SMA at close (${:.2f} < ${:.2f})", symbol, curr_close, sma20)

                # Closing near daily low (within 0.5% of bottom)
                if today_low > 0 and (curr_close - today_low) / today_low < 0.005:
                    safety_score -= 20
                    warnings.append("Closing on daily lows (heavy institutional selling pressure)")

            # 2. Next-Day Pre-Market Earnings Shock Check
            try:
                from earnings_calendar import get_earnings_calendar
                e_info = get_earnings_calendar().check(symbol)
                if getattr(e_info, 'days_until', 99) <= 1:
                    safety_score -= 50
                    warnings.append("Earnings release scheduled before next market open (50/50 binary risk)")
                    should_close = True
                    logger.warning("🚨 [OVERNIGHT_EARNINGS] {}: Imminent earnings within 24h! Recommending pre-close exit.", symbol)
            except Exception as _e_err:
                logger.debug("Earnings calendar check in overnight assessor skipped: {}", _e_err)

            # 3. Macro Shock Calendar Check
            try:
                from economic_calendar import get_economic_calendar
                cal = get_economic_calendar()
                if hasattr(cal, 'check_tomorrow'):
                    t_events = cal.check_tomorrow().events_today
                    high_impact = [e for e in t_events if getattr(e, 'impact', '') == 'HIGH']
                    if high_impact:
                        safety_score -= 15
                        warnings.append(f"Major Macro Release Tomorrow ({len(high_impact)} High-Impact Events)")
            except Exception as _m_err:
                logger.debug("Economic calendar check in overnight assessor skipped: {}", _m_err)

        except Exception as e:
            logger.debug("Overnight risk assessment error for {}: {}", symbol, e)

        safety_score = max(0, min(100, safety_score))
        if safety_score < 40:
            should_close = True

        return {
            "symbol": symbol,
            "safety_score": safety_score,
            "warnings": warnings,
            "should_close_before_bell": should_close,
            "status": "SAFE" if safety_score >= 70 else ("CAUTION" if safety_score >= 40 else "DANGER_EXIT")
        }

def get_overnight_risk_assessor() -> OvernightRiskAssessor:
    return OvernightRiskAssessor()
