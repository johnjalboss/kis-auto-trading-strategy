"""
Earnings Calendar
===================
Track and avoid earnings announcements.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger


@dataclass
class EarningsInfo:
    symbol: str
    has_earnings_soon: bool
    earnings_date: Optional[str]
    days_until: int
    recommendation: str  # "AVOID", "CAUTION", "CLEAR"


class EarningsCalendar:
    """
    Earnings Calendar Tracker
    
    Rules:
    - Avoid new positions 3 days before earnings
    - Close or reduce 1 day before
    - Can play earnings with small position if desired
    """
    
    AVOID_DAYS = 3
    CLOSE_DAYS = 1
    
    def __init__(self):
        self._cache = {}
    
    def check(self, symbol: str) -> EarningsInfo:
        """Check earnings for symbol"""
        
        try:
            ticker = yf.Ticker(symbol)
            calendar = ticker.calendar
            
            if calendar is None:
                return EarningsInfo(symbol, False, None, 999, "CLEAR")
            
            # yfinance returns dict in newer versions, DataFrame in older
            earnings_date = None
            
            if isinstance(calendar, dict):
                # New yfinance API: {'Earnings Date': [datetime, datetime], ...}
                dates = calendar.get('Earnings Date', [])
                if dates:
                    earnings_date = dates[0] if isinstance(dates, list) else dates
            elif hasattr(calendar, 'empty'):
                # Old yfinance API: DataFrame
                if calendar.empty:
                    return EarningsInfo(symbol, False, None, 999, "CLEAR")
                if 'Earnings Date' in calendar.index:
                    dates = calendar.loc['Earnings Date']
                    earnings_date = dates.iloc[0] if hasattr(dates, 'iloc') else dates
            
            # Convert to datetime / date
            from datetime import date
            today = date.today()
            
            earnings_d = None
            if hasattr(earnings_date, 'date'):
                earnings_d = earnings_date.date()
            elif isinstance(earnings_date, date):
                earnings_d = earnings_date
            elif isinstance(earnings_date, str):
                try:
                    earnings_d = datetime.strptime(earnings_date[:10], "%Y-%m-%d").date()
                except Exception:
                    pass
            
            if earnings_d is None:
                return EarningsInfo(symbol, False, None, 999, "CLEAR")
            
            days_until = (earnings_d - today).days
            
            # If earnings date is in the past, the event has already passed -> CLEAR
            if days_until < 0:
                return EarningsInfo(symbol, False, str(earnings_d), days_until, "CLEAR")
            
            # Determine recommendation for UPCOMING earnings
            if 0 <= days_until <= self.CLOSE_DAYS:
                recommendation = "AVOID"
            elif 0 <= days_until <= self.AVOID_DAYS:
                recommendation = "CAUTION"
            else:
                recommendation = "CLEAR"
            
            return EarningsInfo(
                symbol=symbol,
                has_earnings_soon=(days_until <= self.AVOID_DAYS),
                earnings_date=str(earnings_d),
                days_until=days_until,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.debug(f"Earnings check failed for {symbol}: {e}")
            return EarningsInfo(symbol, False, None, 999, "CLEAR")
    
    def filter_safe(self, symbols: List[str]) -> List[str]:
        """Filter to only earnings-safe symbols"""
        safe = []
        for sym in symbols:
            info = self.check(sym)
            if info.recommendation != "AVOID":
                safe.append(sym)
        return safe


def get_earnings_calendar() -> EarningsCalendar:
    return EarningsCalendar()


if __name__ == "__main__":
    print("Testing EarningsCalendar...")
    ec = EarningsCalendar()
    
    symbols = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL"]
    
    for sym in symbols:
        info = ec.check(sym)
        print(f"{sym}: {info.recommendation}")
        if info.earnings_date:
            print(f"  Earnings: {info.earnings_date} ({info.days_until} days)")
