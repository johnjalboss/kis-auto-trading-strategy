"""
Drawdown Controller
=====================
Hard limits on losses to protect capital.

Features:
1. Daily loss limit
2. Weekly loss limit
3. Max drawdown limit
4. Position size reduction on losses
5. Forced liquidation on extreme loss
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
import os
import pytz
import numpy as np
import pandas as pd


@dataclass
class DrawdownState:
    """Current drawdown state"""
    # Capital
    initial_capital: float
    current_capital: float
    peak_capital: float
    
    # Drawdowns
    current_drawdown_pct: float
    max_drawdown_pct: float
    
    # Period P&L
    daily_pnl: float
    daily_pnl_pct: float
    weekly_pnl: float
    weekly_pnl_pct: float
    monthly_pnl: float
    monthly_pnl_pct: float
    
    # Status
    trading_allowed: bool
    position_size_multiplier: float
    status: str  # "NORMAL", "CAUTION", "WARNING", "STOP"
    reason: str


class DrawdownController:
    """
    Drawdown Protection System
    
    Limits:
    - Daily loss: -2% → Reduce size
    - Daily loss: -3% → Stop trading today
    - Weekly loss: -5% → Reduce size
    - Weekly loss: -7% → Stop trading this week
    - Max DD: -10% → Reduce to 50% size
    - Max DD: -15% → Stop all trading
    
    Recovery:
    - After stop, need 3 consecutive green days
    - Position size increases gradually
    """
    
    # Default limits
    DAILY_CAUTION = -0.02   # -2%
    DAILY_STOP = -0.03       # -3%
    WEEKLY_CAUTION = -0.05   # -5%
    WEEKLY_STOP = -0.07      # -7%
    MONTHLY_CAUTION = -0.08  # -8%
    MONTHLY_STOP = -0.12     # -12%
    MAX_DD_CAUTION = -0.10   # -10%
    MAX_DD_STOP = -0.15      # -15%
    
    def __init__(self, initial_capital: float = 100000, 
                 state_file: str = "drawdown_state.json"):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.state_file = state_file
        
        # Period tracking
        self.daily_start = initial_capital
        self.weekly_start = initial_capital
        self.monthly_start = initial_capital
        
        # Dates
        self.day_start_date = datetime.now().date()
        self.week_start_date = datetime.now().date()
        self.month_start_date = datetime.now().date()
        
        # Recovery tracking
        self.consecutive_green_days = 0
        self.is_stopped = False
        self.stop_reason = ""
        
        # Load saved state
        self._load_state()
    
    def update_capital(self, new_capital: float) -> DrawdownState:
        """Update capital and check limits"""
        try:
            # Explicitly convert to float to avoid DataFrame/Series ambiguity
            if hasattr(new_capital, 'iloc'): # In case a Series/DataFrame is passed
                new_capital = float(new_capital.iloc[-1])
            else:
                new_capital = float(new_capital)
        except (TypeError, ValueError, AttributeError):
            logger.error(f"Invalid capital type: {type(new_capital)}")
            return self._calculate_state()

        prev_capital = self.current_capital
        self.current_capital = new_capital
        
        # Update peak
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
        
        # Check if new period
        self._check_period_reset()
        
        # Track consecutive days
        daily_change = new_capital - self.daily_start
        if daily_change > 0:
            self.consecutive_green_days += 1
        elif daily_change < 0:
            self.consecutive_green_days = 0
        
        # Calculate metrics
        return self._calculate_state()
    
    def _calculate_state(self) -> DrawdownState:
        """Calculate current drawdown state"""
        # Drawdowns
        current_dd = (self.current_capital - self.peak_capital) / self.peak_capital
        max_dd = (self.peak_capital - self.initial_capital) / self.initial_capital if self.peak_capital > self.initial_capital else current_dd
        
        # Period P&L
        daily_pnl = self.current_capital - self.daily_start
        daily_pnl_pct = daily_pnl / self.daily_start if self.daily_start > 0 else 0
        
        weekly_pnl = self.current_capital - self.weekly_start
        weekly_pnl_pct = weekly_pnl / self.weekly_start if self.weekly_start > 0 else 0
        
        monthly_pnl = self.current_capital - self.monthly_start
        monthly_pnl_pct = monthly_pnl / self.monthly_start if self.monthly_start > 0 else 0
        
        # Determine status
        status = "NORMAL"
        reason = ""
        trading_allowed = True
        size_mult = 1.0
        
        # Check daily limits
        if daily_pnl_pct <= self.DAILY_STOP:
            status = "STOP"
            reason = f"Daily loss {daily_pnl_pct:.1%} exceeded limit"
            trading_allowed = False
        elif daily_pnl_pct <= self.DAILY_CAUTION:
            status = "CAUTION"
            reason = f"Daily loss {daily_pnl_pct:.1%}"
            size_mult = 0.5
        
        # Check weekly limits
        if weekly_pnl_pct <= self.WEEKLY_STOP:
            status = "STOP"
            reason = f"Weekly loss {weekly_pnl_pct:.1%} exceeded limit"
            trading_allowed = False
        elif weekly_pnl_pct <= self.WEEKLY_CAUTION and status != "STOP":
            status = "WARNING"
            reason = f"Weekly loss {weekly_pnl_pct:.1%}"
            size_mult = min(size_mult, 0.5)
        
        # Check monthly limits
        if monthly_pnl_pct <= self.MONTHLY_STOP:
            status = "STOP"
            reason = f"Monthly loss {monthly_pnl_pct:.1%} exceeded limit"
            trading_allowed = False
        elif monthly_pnl_pct <= self.MONTHLY_CAUTION and status not in ["STOP", "WARNING"]:
            status = "CAUTION"
            reason = f"Monthly loss {monthly_pnl_pct:.1%}"
            size_mult = min(size_mult, 0.6)
        
        # Check max drawdown
        if current_dd <= self.MAX_DD_STOP:
            status = "STOP"
            reason = f"Max DD {current_dd:.1%} exceeded limit"
            trading_allowed = False
        elif current_dd <= self.MAX_DD_CAUTION and status not in ["STOP"]:
            status = "WARNING"
            reason = f"Max DD {current_dd:.1%}"
            size_mult = min(size_mult, 0.5)
        
        # Recovery check
        if self.is_stopped and self.consecutive_green_days >= 3:
            self.is_stopped = False
            status = "CAUTION"
            reason = "Recovering from stop"
            trading_allowed = True
            size_mult = 0.3
        
        if not trading_allowed:
            self.is_stopped = True
            self.stop_reason = reason
            size_mult = 0
        
        # Save state
        def to_float(val):
            if val is None: return 0.0
            try:
                if hasattr(val, 'item'): return float(val.item())
                return float(val)
            except: return 0.0

        self.current_capital = to_float(self.current_capital)
        self.peak_capital = to_float(self.peak_capital)
        self.daily_start = to_float(self.daily_start)
        self.weekly_start = to_float(self.weekly_start)
        self.monthly_start = to_float(self.monthly_start)
        self.initial_capital = to_float(self.initial_capital)
        
        self._save_state()
        
        return DrawdownState(
            initial_capital=self.initial_capital,
            current_capital=self.current_capital,
            peak_capital=self.peak_capital,
            current_drawdown_pct=current_dd,
            max_drawdown_pct=max_dd,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            weekly_pnl=weekly_pnl,
            weekly_pnl_pct=weekly_pnl_pct,
            monthly_pnl=monthly_pnl,
            monthly_pnl_pct=monthly_pnl_pct,
            trading_allowed=trading_allowed,
            position_size_multiplier=size_mult,
            status=status,
            reason=reason
        )
    
    def _check_period_reset(self):
        """Check if new period started (US Eastern time)"""
        try:
            et = pytz.timezone('US/Eastern')
            today = datetime.now(et).date()
        except Exception:
            today = datetime.now().date()
        
        # Daily reset
        if today != self.day_start_date:
            self.daily_start = self.current_capital
            self.day_start_date = today
        
        # Weekly reset (Monday)
        if today.weekday() == 0 and today != self.week_start_date:
            self.weekly_start = self.current_capital
            self.week_start_date = today
        
        # Monthly reset
        if today.day == 1 and today != self.month_start_date:
            self.monthly_start = self.current_capital
            self.month_start_date = today
    
    def is_halted(self) -> bool:
        """Check if trading is halted due to drawdown"""
        return self.is_stopped

    def force_stop(self, reason: str):
        """Force stop trading"""
        self.is_stopped = True
        self.stop_reason = reason
        self._save_state()
    
    def reset(self, new_capital: float = None):
        """Reset controller"""
        if new_capital:
            self.initial_capital = new_capital
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.daily_start = self.initial_capital
        self.weekly_start = self.initial_capital
        self.monthly_start = self.initial_capital
        self.consecutive_green_days = 0
        self.is_stopped = False
        self._save_state()
    
    def _save_state(self):
        """Save state to file"""
        try:
            state = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'peak_capital': self.peak_capital,
                'daily_start': self.daily_start,
                'weekly_start': self.weekly_start,
                'monthly_start': self.monthly_start,
                'day_start_date': str(self.day_start_date),
                'week_start_date': str(self.week_start_date),
                'month_start_date': str(self.month_start_date),
                'consecutive_green_days': self.consecutive_green_days,
                'is_stopped': self.is_stopped,
                'stop_reason': self.stop_reason,
                'last_update': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _load_state(self):
        """Load state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.current_capital = state.get('current_capital', self.initial_capital)
                self.peak_capital = state.get('peak_capital', self.initial_capital)
                self.daily_start = state.get('daily_start', self.initial_capital)
                self.weekly_start = state.get('weekly_start', self.initial_capital)
                self.monthly_start = state.get('monthly_start', self.initial_capital)
                self.consecutive_green_days = state.get('consecutive_green_days', 0)
                self.is_stopped = state.get('is_stopped', False)
                self.stop_reason = state.get('stop_reason', '')
                logger.info(f"Loaded state: capital=${self.current_capital:,.2f}")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")


# Global
_controller = None

def get_drawdown_controller(initial_capital: float = 100000) -> DrawdownController:
    global _controller
    if _controller is None:
        _controller = DrawdownController(initial_capital)
    return _controller


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing DrawdownController...")
    
    controller = DrawdownController(initial_capital=100000)
    
    # Simulate trading days
    scenarios = [
        ("Day 1: Small profit", 101000),
        ("Day 2: Small loss", 99500),
        ("Day 3: Big loss", 97000),  # -3% daily
        ("Day 4: Recovery", 98500),
        ("Day 5: Another loss", 95000),  # Deep DD
    ]
    
    for name, capital in scenarios:
        print(f"\n{'='*50}")
        print(name)
        print('='*50)
        
        state = controller.update_capital(capital)
        
        print(f"Capital: ${state.current_capital:,.2f}")
        print(f"Peak: ${state.peak_capital:,.2f}")
        print(f"Current DD: {state.current_drawdown_pct:.1%}")
        print()
        print(f"Daily P/L: ${state.daily_pnl:+,.2f} ({state.daily_pnl_pct:+.2%})")
        print(f"Weekly P/L: ${state.weekly_pnl:+,.2f} ({state.weekly_pnl_pct:+.2%})")
        print()
        print(f"Status: {state.status}")
        print(f"Trading Allowed: {state.trading_allowed}")
        print(f"Position Size: {state.position_size_multiplier:.0%}")
        if state.reason:
            print(f"Reason: {state.reason}")
