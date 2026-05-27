"""
Economic Calendar
===================
Avoid trading around major economic events.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class EconomicEvent:
    name: str
    date: datetime
    impact: str  # "HIGH", "MEDIUM", "LOW"
    actual: Optional[str]
    forecast: Optional[str]
    previous: Optional[str]


@dataclass
class CalendarCheck:
    has_high_impact: bool
    events_today: List[EconomicEvent]
    events_this_week: List[EconomicEvent]
    
    trading_recommendation: str
    avoid_hours: List[int]


class EconomicCalendar:
    """
    Economic Calendar
    
    High Impact Events:
    - FOMC (Fed) - 8x per year
    - CPI/Inflation - Monthly
    - Employment/NFP - First Friday
    - GDP - Quarterly
    - PCE - Monthly
    
    Strategy:
    - Reduce position before high impact
    - Wide stops during announcements
    - Don't enter 2 hours before/after
    """
    
    # 2026 공식 발표 일정 (ET 기준, 연준/BLS/BEA 공식 발표일)
    HIGH_IMPACT_SCHEDULE = {
        # FOMC — 연준 공식 2026 일정 (발표일 = 2일차 마지막 날)
        # Source: federalreserve.gov
        'FOMC': [
            (1, 28),   # Jan 27-28
            (3, 18),   # Mar 17-18*
            (4, 29),   # Apr 28-29
            (6, 17),   # Jun 16-17*
            (7, 29),   # Jul 28-29
            (9, 16),   # Sep 15-16*
            (10, 28),  # Oct 27-28
            (12, 9),   # Dec 8-9*
        ],
        # CPI — BLS 공식 2026 발표 일정 (8:30 AM ET)
        # Source: bls.gov
        'CPI': [
            (1, 13),   # Dec 2025 data
            (2, 13),   # Jan 2026 data
            (3, 11),   # Feb 2026 data
            (4, 10),   # Mar 2026 data
            (5, 12),   # Apr 2026 data
            (6, 10),   # May 2026 data
            (7, 14),   # Jun 2026 data
            (8, 12),   # Jul 2026 data
            (9, 11),   # Aug 2026 data
            (10, 14),  # Sep 2026 data
            (11, 10),  # Oct 2026 data
            (12, 10),  # Nov 2026 data
        ],
        # NFP (고용보고서) — BLS 공식 2026 발표 일정 (8:30 AM ET)
        # Source: bls.gov Employment Situation schedule
        'NFP': [
            (1, 9),    # Dec 2025 data
            (2, 11),   # Jan 2026 data
            (3, 6),    # Feb 2026 data
            (4, 3),    # Mar 2026 data
            (5, 8),    # Apr 2026 data
            (6, 5),    # May 2026 data
            (7, 2),    # Jun 2026 data
            (8, 7),    # Jul 2026 data
            (9, 4),    # Aug 2026 data
            (10, 2),   # Sep 2026 data
            (11, 6),   # Oct 2026 data
            (12, 4),   # Nov 2026 data
        ],
        # GDP (Advance Estimate) — BEA 분기별 발표 (8:30 AM ET)
        # Q4 2025 → Jan 30 / Q1 2026 → Apr 29 / Q2 → Jul 30 / Q3 → Oct 29 (추정)
        'GDP': [
            (1, 30),   # Q4 2025 advance estimate
            (4, 29),   # Q1 2026 advance estimate
            (7, 30),   # Q2 2026 advance estimate
            (10, 29),  # Q3 2026 advance estimate
        ],
        # PCE (연준 선호 물가지표) — BEA Personal Income 보고서와 함께 발표
        # 매월 말 ~ 익월 초 발표, 근사치
        'PCE': [
            (1, 30),   # Dec 2025 data (GDP와 동일일 발표)
            (2, 27),   # Jan 2026 data
            (3, 27),   # Feb 2026 data
            (4, 30),   # Mar 2026 data
            (5, 29),   # Apr 2026 data
            (6, 26),   # May 2026 data
            (7, 31),   # Jun 2026 data
            (8, 28),   # Jul 2026 data
            (9, 25),   # Aug 2026 data
            (10, 30),  # Sep 2026 data
            (11, 25),  # Oct 2026 data
            (12, 23),  # Nov 2026 data
        ],
    }
    
    def __init__(self):
        self.events_cache: List[EconomicEvent] = []
        self._build_events()
    
    def _build_events(self):
        """Build events for current year"""
        year = datetime.now().year
        
        for event_name, dates in self.HIGH_IMPACT_SCHEDULE.items():
            for month, day in dates:
                try:
                    event_date = datetime(year, month, day)
                    self.events_cache.append(EconomicEvent(
                        name=event_name,
                        date=event_date,
                        impact="HIGH",
                        actual=None,
                        forecast=None,
                        previous=None
                    ))
                except:
                    pass
    
    def check_today(self) -> CalendarCheck:
        """Check economic events for today/week — uses ET (US Eastern) date"""
        import pytz
        
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        today = now_et.date()          # ← ET 날짜 기준 (미국 일정이므로)
        week_end = today + timedelta(days=7)
        
        events_today = []
        events_week = []
        
        for event in self.events_cache:
            event_date = event.date.date()
            
            if event_date == today:
                events_today.append(event)
            elif today < event_date <= week_end:
                events_week.append(event)
        
        has_high = len(events_today) > 0
        
        # Avoid hours
        avoid = []
        if has_high:
            # FOMC usually 2pm, CPI/NFP 8:30am
            avoid = [8, 9, 13, 14, 15]
        
        # Recommendation
        if has_high:
            names = [e.name for e in events_today]
            rec = f"HIGH IMPACT TODAY: {', '.join(names)} - Reduce exposure, widen stops"
        elif events_week:
            names = [e.name for e in events_week[:3]]
            rec = f"High impact this week: {', '.join(names)} - Plan accordingly"
        else:
            rec = "No major events - normal trading"
        
        return CalendarCheck(
            has_high_impact=has_high,
            events_today=events_today,
            events_this_week=events_week,
            trading_recommendation=rec,
            avoid_hours=avoid
        )
    
    def should_reduce_exposure(self) -> tuple:
        """Check if should reduce before event — uses ET time"""
        import pytz
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        
        # Check if event within next 24 hours (ET time)
        for event in self.events_cache:
            event_dt = pytz.timezone('US/Eastern').localize(event.date) if event.date.tzinfo is None else event.date
            hours_until = (event_dt - now).total_seconds() / 3600
            
            if 0 < hours_until < 24:
                return True, f"{event.name} in {hours_until:.0f} hours - reduce exposure"
        
        return False, "No imminent events"
    
    def is_safe_to_trade(self) -> tuple:
        """Check if safe to enter new trades — uses ET timezone"""
        import pytz
        et = pytz.timezone('US/Eastern')
        now_et = datetime.now(et)
        
        check = self.check_today()
        
        # On high-impact days, block during key announcement windows (ET hours)
        # CPI/NFP: 8:30 AM ET, FOMC: 2:00 PM ET
        if check.has_high_impact:
            et_hour = now_et.hour
            if et_hour in check.avoid_hours:
                return False, f"High impact event window ({et_hour}:xx ET) - avoid new entries"
            return False, "High impact day - be cautious with new entries"
        
        return True, "Clear to trade"

    def get_todays_events(self) -> list:
        """Return today's high-impact events (alias for strategy guard compatibility)"""
        return self.check_today().events_today


def get_economic_calendar() -> EconomicCalendar:
    return EconomicCalendar()


if __name__ == "__main__":
    print("Testing EconomicCalendar...")
    ec = EconomicCalendar()
    
    check = ec.check_today()
    
    print(f"\n{'='*50}")
    print("ECONOMIC CALENDAR")
    print('='*50)
    print(f"High Impact Today: {check.has_high_impact}")
    print(f"Events Today: {[e.name for e in check.events_today]}")
    print(f"Events This Week: {[e.name for e in check.events_this_week]}")
    print(f"Avoid Hours: {check.avoid_hours}")
    print(f"Recommendation: {check.trading_recommendation}")
    
    safe, reason = ec.is_safe_to_trade()
    print(f"\nSafe to Trade: {safe}")
    print(f"Reason: {reason}")


def get_upcoming_events():
    return EconomicCalendar().get_upcoming_events()
