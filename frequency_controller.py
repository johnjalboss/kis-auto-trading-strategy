"""
Trade Frequency Controller
============================
Control trading frequency: Swing-Day Hybrid Mode
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger
import json
import os
import config


class TradingStyle(Enum):
    DAY_TRADING = "DAY_TRADING"        # 하루 5-20회, 보유 수분~수시간
    SWING_DAY_HYBRID = "SWING_DAY"     # 하루 1-3회, 보유 1-3일
    SWING = "SWING"                     # 주 2-5회, 보유 3-10일
    POSITION = "POSITION"               # 월 2-4회, 보유 수주


@dataclass
class FrequencyConfig:
    style: TradingStyle
    
    # Daily limits
    max_trades_per_day: int
    max_entries_per_day: int  # New positions
    max_exits_per_day: int
    
    # Timing
    min_hold_hours: int
    max_hold_days: int
    
    # Entry spacing
    min_minutes_between_trades: int
    
    # Session preferences
    trade_premarket: bool
    trade_afterhours: bool
    avoid_first_15min: bool
    avoid_last_15min: bool
    
    # Scan frequency
    scan_interval_minutes: int


@dataclass
class TradeWindow:
    can_trade: bool
    reason: str
    next_allowed: datetime
    trades_today: int
    trades_remaining: int


class FrequencyController:
    """
    Trade Frequency Controller
    
    Swing-Day Hybrid Mode:
    - 1-3 trades per day
    - Hold 1-3 days typically
    - Scan every 15 minutes
    - Quick exits if wrong
    """
    
    CONFIGS = {
        TradingStyle.DAY_TRADING: FrequencyConfig(
            style=TradingStyle.DAY_TRADING,
            max_trades_per_day=15,
            max_entries_per_day=8,
            max_exits_per_day=15,
            min_hold_hours=0,
            max_hold_days=1,
            min_minutes_between_trades=5,
            trade_premarket=True,
            trade_afterhours=True,
            avoid_first_15min=False,
            avoid_last_15min=False,
            scan_interval_minutes=3
        ),
        TradingStyle.SWING_DAY_HYBRID: FrequencyConfig(
            style=TradingStyle.SWING_DAY_HYBRID,
            max_trades_per_day=40,
            max_entries_per_day=20,
            max_exits_per_day=20,
            min_hold_hours=2,
            max_hold_days=5,
            min_minutes_between_trades=5,
            trade_premarket=True,
            trade_afterhours=False,
            avoid_first_15min=False,
            avoid_last_15min=False,
            scan_interval_minutes=10
        ),
        TradingStyle.SWING: FrequencyConfig(
            style=TradingStyle.SWING,
            max_trades_per_day=5,
            max_entries_per_day=3,
            max_exits_per_day=5,
            min_hold_hours=12,
            max_hold_days=10,
            min_minutes_between_trades=20,
            trade_premarket=False,
            trade_afterhours=False,
            avoid_first_15min=False,
            avoid_last_15min=False,
            scan_interval_minutes=15
        ),
        TradingStyle.POSITION: FrequencyConfig(
            style=TradingStyle.POSITION,
            max_trades_per_day=3,
            max_entries_per_day=2,
            max_exits_per_day=3,
            min_hold_hours=48,
            max_hold_days=30,
            min_minutes_between_trades=60,
            trade_premarket=False,
            trade_afterhours=False,
            avoid_first_15min=True,
            avoid_last_15min=True,
            scan_interval_minutes=30
        )
    }
    
    def __init__(self, style: TradingStyle = TradingStyle.SWING,
                 state_file: str = "frequency_state.json"):
        self.style = style
        self.config = self.CONFIGS[style]
        self.state_file = state_file
        
        self.trades_today: List[datetime] = []
        self.entries_today: int = 0
        self.last_trade_time: datetime = datetime.min
        self.current_date = datetime.now().date()
        
        self._load_state()
        logger.info(f"Frequency mode: {style.value}")
    
    def can_trade(self, is_upgrade: bool = False) -> TradeWindow:
        """Check if trading is allowed now"""
        now = datetime.now()
        
        # Check date reset
        if now.date() != self.current_date:
            self._reset_daily()
            self.current_date = now.date()
        
        # Check daily limit
        if len(self.trades_today) >= self.config.max_trades_per_day:
            tomorrow = now.replace(hour=9, minute=30) + timedelta(days=1)
            return TradeWindow(False, "Daily limit reached", tomorrow,
                              len(self.trades_today), 0)
        
        # Check entry limit
        if self.entries_today >= self.config.max_entries_per_day:
            tomorrow = now.replace(hour=9, minute=30) + timedelta(days=1)
            return TradeWindow(False, "Entry limit reached", tomorrow,
                              len(self.trades_today), 0)
        
        # Check minimum time between trades
        if not is_upgrade:
            minutes_since = (now - self.last_trade_time).total_seconds() / 60
            if minutes_since < self.config.min_minutes_between_trades:
                wait = self.config.min_minutes_between_trades - minutes_since
                next_allowed = now + timedelta(minutes=wait)
                return TradeWindow(False, f"Wait {wait:.0f} min", next_allowed,
                                  len(self.trades_today), 
                                  self.config.max_trades_per_day - len(self.trades_today))
        
        remaining = self.config.max_trades_per_day - len(self.trades_today)
        return TradeWindow(True, "OK", now, len(self.trades_today), remaining)
    
    def record_trade(self, is_entry: bool = True):
        """Record a trade"""
        now = datetime.now()
        self.trades_today.append(now)
        self.last_trade_time = now
        
        if is_entry:
            self.entries_today += 1
        
        self._save_state()
    
    def get_scan_interval(self) -> int:
        """Get scan interval in minutes"""
        return self.config.scan_interval_minutes
    
    def _reset_daily(self):
        """Reset daily counters"""
        self.trades_today = []
        self.entries_today = 0
        logger.info("Daily trade counters reset")
    
    def _save_state(self):
        try:
            state = {
                'date': str(self.current_date),
                'trades_count': len(self.trades_today),
                'entries_today': self.entries_today,
                'last_trade': self.last_trade_time.isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except: pass
    
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                saved_date = state.get('date', '')
                if saved_date == str(datetime.now().date()):
                    self.entries_today = state.get('entries_today', 0)
                    last = state.get('last_trade')
                    if last:
                        self.last_trade_time = datetime.fromisoformat(last)
        except: pass


def get_frequency_controller(style: str = "SWING") -> FrequencyController:
    # Handle common style names
    style_map = {
        "SWING_DAY": "SWING_DAY_HYBRID",
        "SWING-DAY": "SWING_DAY_HYBRID",
        "HYBRID": "SWING_DAY_HYBRID",
    }
    style = style_map.get(style.upper(), style.upper())
    style_enum = TradingStyle[style.replace("-", "_")]
    return FrequencyController(style_enum)


if __name__ == "__main__":
    print("Testing FrequencyController...")
    
    for style in TradingStyle:
        fc = FrequencyController(style)
        config = fc.config
        
        print(f"\n{'='*50}")
        print(f"Style: {style.value}")
        print('='*50)
        print(f"Max Trades/Day: {config.max_trades_per_day}")
        print(f"Max Entries/Day: {config.max_entries_per_day}")
        print(f"Min Hold: {config.min_hold_hours}h")
        print(f"Max Hold: {config.max_hold_days} days")
        print(f"Spacing: {config.min_minutes_between_trades} min")
        print(f"Scan: Every {config.scan_interval_minutes} min")
        
        window = fc.can_trade()
        print(f"\nCan Trade: {window.can_trade} ({window.reason})")
