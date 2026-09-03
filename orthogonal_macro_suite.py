"""
Orthogonal Macro Suite (orthogonal_macro_suite.py)
===================================================
Provides non-collinear (orthogonal) market intelligence:
1. CBOE SKEW Index (^SKEW): Institutional Tail-Risk / Black Swan Put Option Hedging.
2. Turn-of-the-Month (TOTM): Passive 401(k) & institutional rebalancing inflow window (Last day to Day +3).
3. Credit Spread Ratio (HYG / IEI): Smart-money bond market risk appetite.

Mathematical Foundation:
    - SKEW >= 140: High institutional tail-risk hedging -> Defensive threshold damping
    - SKEW < 130: Low tail risk -> Green light momentum
    - TOTM Active: +5pt mechanical liquidity inflow boost
"""

import time
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger
import yfinance as yf

@dataclass
class SkewSnapshot:
    skew_value: float
    is_elevated: bool       # >= 140
    is_normal: bool         # 115 <= SKEW < 140
    tail_risk_state: str    # "HIGH_HEDGING", "NORMAL", "LOW"
    description: str

@dataclass
class OrthogonalMacroSnapshot:
    skew: SkewSnapshot
    is_totm_window: bool    # True if within month-end (T-1) to month-start (T+3)
    totm_day_desc: str
    credit_ratio: float     # HYG / IEI
    credit_sentiment: str   # "RISK_ON", "NEUTRAL", "RISK_OFF"
    composite_boost: int    # Net confidence score adjustment (-10 to +10)


class OrthogonalMacroSuite:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrthogonalMacroSuite, cls).__new__(cls)
            cls._instance._cache = None
            cls._instance._last_fetch = 0.0
            cls._instance._ttl = 14400.0  # 4 hours cache
        return cls._instance

    def is_turn_of_the_month(self, target_date: Optional[date] = None) -> tuple:
        """
        Determines if target date falls within the Turn-of-the-Month (TOTM) window.
        TOTM Window: Last trading day of previous month through first 3 trading days of current month.
        """
        d = target_date or date.today()
        
        # Calculate first day of next month
        if d.month == 12:
            next_month_first = date(d.year + 1, 1, 1)
        else:
            next_month_first = date(d.year, d.month + 1, 1)
            
        cur_month_first = date(d.year, d.month, 1)
        
        # 1. Count business days from start of current month
        b_days_from_start = 0
        cur = cur_month_first
        while cur <= d:
            if cur.weekday() < 5:  # Monday to Friday
                b_days_from_start += 1
            cur += timedelta(days=1)
            
        if b_days_from_start <= 3:
            return True, f"TOTM_START_DAY_{b_days_from_start}"

        # 2. Count business days until next month start (check if last trading day of month)
        cur = d
        b_days_remaining = 0
        while cur < next_month_first:
            if cur.weekday() < 5:
                b_days_remaining += 1
            cur += timedelta(days=1)
            
        if b_days_remaining <= 1:
            return True, "TOTM_MONTH_END_EVE"

        return False, "REGULAR_CALENDAR"

    def fetch_skew(self) -> SkewSnapshot:
        """Fetches CBOE SKEW Index (^SKEW)."""
        try:
            ticker = yf.Ticker('^SKEW')
            hist = ticker.history(period='5d')
            if not hist.empty:
                val = float(hist['Close'].iloc[-1])
                if val >= 140.0:
                    return SkewSnapshot(val, True, False, "HIGH_HEDGING", f"SKEW elevated ({val:.1f} >= 140), institutions buying crash puts")
                elif val < 125.0:
                    return SkewSnapshot(val, False, True, "LOW", f"SKEW calm ({val:.1f}), suppressed tail risk")
                else:
                    return SkewSnapshot(val, False, True, "NORMAL", f"SKEW normal ({val:.1f})")
        except Exception as e:
            logger.debug("Failed to fetch ^SKEW: {}", e)

        return SkewSnapshot(130.0, False, True, "NORMAL", "SKEW baseline (130.0)")

    def fetch_credit_spread(self) -> tuple:
        """Calculates HYG / IEI smart-money credit risk ratio."""
        try:
            hyg = yf.Ticker('HYG').history(period='5d')
            iei = yf.Ticker('IEI').history(period='5d')
            if not hyg.empty and not iei.empty:
                r_now = float(hyg['Close'].iloc[-1]) / float(iei['Close'].iloc[-1])
                r_prev = float(hyg['Close'].iloc[-2]) / float(iei['Close'].iloc[-2]) if len(hyg) >= 2 else r_now
                chg = (r_now - r_prev) / r_prev
                if chg >= 0.002:
                    return r_now, "RISK_ON"
                elif chg <= -0.003:
                    return r_now, "RISK_OFF"
                return r_now, "NEUTRAL"
        except Exception as e:
            logger.debug("Failed to fetch credit spread: {}", e)
        return 0.65, "NEUTRAL"

    def get_snapshot(self) -> OrthogonalMacroSnapshot:
        now = time.time()
        if self._cache and (now - self._last_fetch < self._ttl):
            return self._cache

        skew_snap = self.fetch_skew()
        is_totm, totm_desc = self.is_turn_of_the_month()
        cred_ratio, cred_sent = self.fetch_credit_spread()

        boost = 0
        if is_totm:
            boost += 5  # +5pt passive 401(k) / institutional rebalance flow
        if cred_sent == "RISK_ON":
            boost += 3
        elif cred_sent == "RISK_OFF":
            boost -= 5
            
        if skew_snap.is_elevated:
            boost -= 4  # Tail risk dampening

        snap = OrthogonalMacroSnapshot(
            skew=skew_snap,
            is_totm_window=is_totm,
            totm_day_desc=totm_desc,
            credit_ratio=cred_ratio,
            credit_sentiment=cred_sent,
            composite_boost=boost
        )

        self._cache = snap
        self._last_fetch = now
        logger.info("📐 [ORTHOGONAL_MACRO] SKEW={:.1f} ({}), TOTM={} ({}), Credit={}, NetBoost={:+d}pt",
                    skew_snap.skew_value, skew_snap.tail_risk_state, is_totm, totm_desc, cred_sent, boost)
        return snap


def get_orthogonal_macro_suite() -> OrthogonalMacroSuite:
    return OrthogonalMacroSuite()
