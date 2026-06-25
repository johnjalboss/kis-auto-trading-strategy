"""
Scheduler & Market Hours
==========================
Handle trading hours and scheduled tasks.
"""

from datetime import datetime, time, timedelta
from typing import Tuple
import pytz
from loguru import logger


class TradingScheduler:
    """Market hours and scheduling"""
    
    # US Eastern timezone
    TZ = pytz.timezone("US/Eastern")
    
    # Market hours (EST)
    MARKET_OPEN = time(9, 30)
    MARKET_CLOSE = time(16, 0)
    
    # Pre-market
    PREMARKET_OPEN = time(4, 0)
    PREMARKET_CLOSE = time(9, 30)
    
    # After hours
    AFTERHOURS_OPEN = time(16, 0)
    AFTERHOURS_CLOSE = time(20, 0)
    
    # Holidays 2024-2025
    HOLIDAYS = [
        "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
        "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
        "2024-11-28", "2024-12-25",
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
        "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
        "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
        "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
        "2026-11-26", "2026-12-25",
    ]
    US_HOLIDAYS = HOLIDAYS
    
    def __init__(self):
        pass
    
    def now_est(self) -> datetime:
        return datetime.now(self.TZ)
    
    def is_market_open(self) -> bool:
        now = self.now_est()
        if now.weekday() >= 5:  # Weekend
            return False
        if now.strftime("%Y-%m-%d") in self.HOLIDAYS:
            return False
        return self.MARKET_OPEN <= now.time() < self.MARKET_CLOSE
    
    def is_premarket(self) -> bool:
        now = self.now_est()
        if now.weekday() >= 5:
            return False
        return self.PREMARKET_OPEN <= now.time() < self.MARKET_OPEN
    
    def is_afterhours(self) -> bool:
        now = self.now_est()
        if now.weekday() >= 5:
            return False
        return self.AFTERHOURS_OPEN < now.time() <= self.AFTERHOURS_CLOSE
    
    def is_trading_day(self) -> bool:
        now = self.now_est()
        if now.weekday() >= 5:
            return False
        if now.strftime("%Y-%m-%d") in self.HOLIDAYS:
            return False
        return True
    
    def time_to_open(self) -> timedelta:
        """Time until market opens"""
        now = self.now_est()
        today_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        
        if now.time() < self.MARKET_OPEN:
            return today_open - now
        else:
            # Next trading day
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5 or next_day.strftime("%Y-%m-%d") in self.HOLIDAYS:
                next_day += timedelta(days=1)
            next_open = next_day.replace(hour=9, minute=30, second=0, microsecond=0)
            return next_open - now
    
    def time_to_close(self) -> timedelta:
        """Time until market closes"""
        now = self.now_est()
        today_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if now.time() < self.MARKET_CLOSE:
            return today_close - now
        return timedelta(0)
    
    def get_session(self) -> str:
        """Get current session"""
        if self.is_market_open():
            return "MARKET"
        elif self.is_premarket():
            return "PREMARKET"
        elif self.is_afterhours():
            return "AFTERHOURS"
        else:
            return "CLOSED"
    
    def should_trade(self, allow_extended: bool = False) -> Tuple[bool, str]:
        """Check if should trade now"""
        if not self.is_trading_day():
            return False, "Market closed (weekend/holiday)"
        
        if self.is_market_open():
            return True, "Market open"
        
        if allow_extended:
            if self.is_premarket():
                return True, "Pre-market"
            if self.is_afterhours():
                return True, "After-hours"
        
        return False, f"Market closed. Opens in {self.time_to_open()}"


def get_scheduler() -> TradingScheduler:
    return TradingScheduler()


if __name__ == "__main__":
    print("Testing TradingScheduler...")
    s = TradingScheduler()
    
    print(f"Current time (EST): {s.now_est()}")
    print(f"Session: {s.get_session()}")
    print(f"Market open: {s.is_market_open()}")
    print(f"Trading day: {s.is_trading_day()}")
    print(f"Time to open: {s.time_to_open()}")
    print(f"Should trade: {s.should_trade()}")
