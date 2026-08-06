"""
Event Calendar Module
======================
Track market-moving events for timing and risk management.

Events:
1. Earnings Announcements
2. FOMC Meetings & Rate Decisions
3. Options Expiration (Monthly, Weekly)
4. Economic Data Releases
5. Ex-Dividend Dates
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict
from enum import Enum
import yfinance as yf
from loguru import logger


class EventType(Enum):
    EARNINGS = "EARNINGS"
    FOMC = "FOMC"
    OPEX = "OPEX"  # Options expiration
    ECONOMIC = "ECONOMIC"
    DIVIDEND = "DIVIDEND"


class EventImpact(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class MarketEvent:
    """Market event"""
    event_type: EventType
    date: date
    time: Optional[str]  # "BMO", "AMC", None
    symbol: Optional[str]
    description: str
    impact: EventImpact
    days_until: int


@dataclass  
class EarningsInfo:
    """Earnings information for a stock"""
    symbol: str
    next_earnings_date: Optional[date]
    days_until_earnings: int
    is_before_open: bool
    estimate_eps: Optional[float]
    surprise_history: str  # "BEATS", "MISSES", "MIXED"


@dataclass
class EventCalendarSignal:
    """Event calendar analysis result"""
    symbol: str
    score: int  # -100 to +100
    signal: str  # "AVOID", "CAUTION", "CLEAR"
    
    upcoming_events: List[MarketEvent]
    earnings: Optional[EarningsInfo]
    is_fomc_week: bool
    is_opex_week: bool
    
    recommendations: List[str]


class EventCalendar:
    """
    Market Event Calendar
    
    Risk Scoring:
    - Earnings within 3 days: -40 (high volatility risk)
    - FOMC week: -20 (rate decision volatility)
    - Options expiration week: -15 (gamma risk)
    - Ex-dividend within 2 days: -10 (price adjustment)
    
    Opportunities:
    - Post-earnings momentum (good surprise): +30
    - Post-FOMC clarity: +15
    """
    
    # FOMC 2024 Schedule (approximate - update yearly)
    FOMC_DATES_2024 = [
        date(2024, 1, 31), date(2024, 3, 20), date(2024, 5, 1),
        date(2024, 6, 12), date(2024, 7, 31), date(2024, 9, 18),
        date(2024, 11, 7), date(2024, 12, 18),
    ]
    
    FOMC_DATES_2025 = [
        date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7),
        date(2025, 6, 18), date(2025, 7, 30), date(2025, 9, 17),
        date(2025, 11, 5), date(2025, 12, 17),
    ]
    
    FOMC_DATES_2026 = [
        date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29),
        date(2026, 6, 17), date(2026, 7, 29), date(2026, 9, 16),
        date(2026, 11, 4), date(2026, 12, 16),
    ]
    
    def __init__(self):
        self._earnings_cache: Dict[str, tuple] = {}
        self._cache_ttl = 3600 * 6  # 6 hours
    
    def analyze(self, symbol: str) -> EventCalendarSignal:
        """Analyze event calendar for a symbol"""
        today = date.today()
        score = 0
        recommendations = []
        upcoming = []
        
        # 1. Check earnings
        earnings = self._get_earnings_info(symbol)
        
        if earnings and earnings.next_earnings_date:
            days = earnings.days_until_earnings
            
            if days <= 3:
                score -= 40
                recommendations.append(f"EARNINGS in {days}d - HIGH VOLATILITY")
                upcoming.append(MarketEvent(
                    EventType.EARNINGS, earnings.next_earnings_date,
                    "BMO" if earnings.is_before_open else "AMC",
                    symbol, "Earnings Release", EventImpact.HIGH, days
                ))
            elif days <= 7:
                score -= 20
                recommendations.append(f"EARNINGS in {days}d - Consider reducing size")
            elif days <= 14:
                score -= 10
                recommendations.append(f"EARNINGS in {days}d - Monitor")
        
        # 2. Check FOMC
        fomc_info = self._check_fomc(today)
        
        if fomc_info['days_until'] is not None:
            days = fomc_info['days_until']
            
            if days <= 2:
                score -= 25
                recommendations.append(f"FOMC in {days}d - RATE DECISION")
                upcoming.append(MarketEvent(
                    EventType.FOMC, fomc_info['date'], "14:00 ET",
                    None, "FOMC Rate Decision", EventImpact.HIGH, days
                ))
            elif days <= 7:
                score -= 15
                recommendations.append(f"FOMC in {days}d - Volatility expected")
        
        # 3. Check options expiration
        opex_info = self._check_options_expiry(today)
        
        if opex_info['days_until'] is not None:
            days = opex_info['days_until']
            
            if days <= 2:
                score -= 20
                recommendations.append(f"OPEX in {days}d - GAMMA EXPOSURE")
                upcoming.append(MarketEvent(
                    EventType.OPEX, opex_info['date'], None,
                    None, opex_info['type'], EventImpact.MEDIUM, days
                ))
            elif days <= 4 and opex_info['is_monthly']:
                score -= 10
                recommendations.append(f"Monthly OPEX in {days}d")
        
        # 4. Check ex-dividend
        exdiv = self._check_ex_dividend(symbol)
        
        if exdiv and exdiv <= 2:
            score -= 10
            recommendations.append(f"EX-DIVIDEND in {exdiv}d")
        
        # Determine signal
        if score < -30:
            signal = "AVOID"
        elif score < -10:
            signal = "CAUTION"
        else:
            signal = "CLEAR"
        
        if not recommendations:
            recommendations.append("No major events - CLEAR to trade")
        
        return EventCalendarSignal(
            symbol=symbol,
            score=max(-100, min(100, score)),
            signal=signal,
            upcoming_events=upcoming,
            earnings=earnings,
            is_fomc_week=fomc_info.get('is_this_week', False),
            is_opex_week=opex_info.get('is_this_week', False),
            recommendations=recommendations
        )
    
    def _get_earnings_info(self, symbol: str) -> Optional[EarningsInfo]:
        """Get earnings information"""
        # Check cache
        if symbol in self._earnings_cache:
            data, timestamp = self._earnings_cache[symbol]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is None or calendar.empty:
                return None
            
            # Get earnings date
            if 'Earnings Date' in calendar.index:
                earnings_date = calendar.loc['Earnings Date']
                if isinstance(earnings_date, pd.Series):
                    earnings_date = earnings_date.iloc[0]
                
                if pd.isna(earnings_date):
                    return None
                
                if isinstance(earnings_date, datetime):
                    earnings_date = earnings_date.date()
                elif isinstance(earnings_date, str):
                    earnings_date = datetime.strptime(earnings_date, '%Y-%m-%d').date()
                
                days_until = (earnings_date - date.today()).days
                
                # Get EPS estimate
                eps_est = None
                if 'Earnings Average' in calendar.index:
                    eps_est = calendar.loc['Earnings Average']
                    if isinstance(eps_est, pd.Series):
                        eps_est = eps_est.iloc[0]
                
                # Estimate surprise history
                surprise_history = self._get_surprise_history(ticker)
                
                result = EarningsInfo(
                    symbol=symbol,
                    next_earnings_date=earnings_date,
                    days_until_earnings=days_until,
                    is_before_open=True,  # Assume BMO
                    estimate_eps=eps_est if eps_est and not pd.isna(eps_est) else None,
                    surprise_history=surprise_history
                )
                
                self._earnings_cache[symbol] = (result, datetime.now())
                return result
                
        except Exception as e:
            logger.debug("Earnings fetch failed for {}: {}", symbol, e)
        
        return None
    
    def _get_surprise_history(self, ticker) -> str:
        """Analyze earnings surprise history"""
        try:
            # Get historical earnings
            earnings = ticker.earnings_history
            
            if earnings is None or earnings.empty:
                return "UNKNOWN"
            
            # Count beats vs misses
            if 'epsActual' in earnings.columns and 'epsEstimate' in earnings.columns:
                beats = (earnings['epsActual'] > earnings['epsEstimate']).sum()
                total = len(earnings)
                
                if beats / total > 0.7:
                    return "BEATS"
                elif beats / total < 0.3:
                    return "MISSES"
                return "MIXED"
                
        except Exception as err:
            logger.warning("⚠️ [event_calendar.py] Fallback triggered: {}", err)
        
        return "UNKNOWN"
    
    def _check_fomc(self, today: date) -> dict:
        """Check FOMC schedule"""
        all_dates = self.FOMC_DATES_2024 + self.FOMC_DATES_2025 + self.FOMC_DATES_2026
        
        for fomc_date in sorted(all_dates):
            if fomc_date >= today:
                days_until = (fomc_date - today).days
                is_this_week = days_until <= 7
                
                return {
                    'date': fomc_date,
                    'days_until': days_until,
                    'is_this_week': is_this_week
                }
        
        return {'date': None, 'days_until': None, 'is_this_week': False}
    
    def _check_options_expiry(self, today: date) -> dict:
        """Check options expiration"""
        # Monthly expiry: 3rd Friday
        # Weekly expiry: Every Friday
        
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            next_friday = today
        else:
            next_friday = today + timedelta(days=days_until_friday)
        
        # Check if it's 3rd Friday (monthly)
        is_monthly = 15 <= next_friday.day <= 21 and next_friday.weekday() == 4
        
        days_until = (next_friday - today).days
        
        return {
            'date': next_friday,
            'days_until': days_until,
            'is_monthly': is_monthly,
            'is_this_week': days_until <= 5,
            'type': "Monthly OPEX" if is_monthly else "Weekly OPEX"
        }
    
    def _check_ex_dividend(self, symbol: str) -> Optional[int]:
        """Check ex-dividend date"""
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is not None and 'Ex-Dividend Date' in calendar.index:
                exdiv = calendar.loc['Ex-Dividend Date']
                if isinstance(exdiv, pd.Series):
                    exdiv = exdiv.iloc[0]
                
                if pd.isna(exdiv):
                    return None
                
                if isinstance(exdiv, datetime):
                    exdiv = exdiv.date()
                
                days_until = (exdiv - date.today()).days
                return days_until if days_until >= 0 else None
                
        except Exception as err:
            logger.warning("⚠️ [event_calendar.py] Fallback triggered: {}", err)
        
        return None
    
    def get_market_events_today(self) -> List[MarketEvent]:
        """Get all market-wide events for today"""
        today = date.today()
        events = []
        
        # Check FOMC
        fomc = self._check_fomc(today)
        if fomc['days_until'] == 0:
            events.append(MarketEvent(
                EventType.FOMC, today, "14:00 ET", None,
                "FOMC Rate Decision", EventImpact.HIGH, 0
            ))
        
        # Check OPEX
        opex = self._check_options_expiry(today)
        if opex['days_until'] == 0:
            events.append(MarketEvent(
                EventType.OPEX, today, "16:00 ET", None,
                opex['type'], EventImpact.MEDIUM, 0
            ))
        
        return events


import pandas as pd

# Global instance
_calendar = None

def get_event_calendar() -> EventCalendar:
    global _calendar
    if _calendar is None:
        _calendar = EventCalendar()
    return _calendar


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing EventCalendar...")
    
    calendar = EventCalendar()
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        signal = calendar.analyze(symbol)
        
        print(f"Signal: {signal.signal} (Score: {signal.score:+d})")
        print(f"FOMC Week: {signal.is_fomc_week}")
        print(f"OPEX Week: {signal.is_opex_week}")
        
        if signal.earnings:
            e = signal.earnings
            print(f"Earnings: {e.next_earnings_date} ({e.days_until_earnings}d)")
            print(f"Surprise History: {e.surprise_history}")
        
        print(f"Recommendations: {signal.recommendations}")
