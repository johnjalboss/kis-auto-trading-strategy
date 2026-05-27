"""
Exit Optimizer
================
Optimize exit timing for maximum profit.
"""

from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class ExitSignal:
    should_exit: bool
    urgency: str  # "IMMEDIATE", "SOON", "HOLD"
    reason: str
    
    # Profit taking
    take_partial: bool
    partial_pct: int  # % to sell
    
    # Price levels
    suggested_exit: float
    trailing_stop: float


class ExitOptimizer:
    """
    Exit Timing Optimizer
    
    Exit Signals:
    1. Target reached
    2. Momentum loss
    3. Trend reversal
    4. Time decay
    5. Risk events
    
    Smart Exits:
    - Partial profit taking
    - Trailing stops
    - Time-based rules
    """
    
    def __init__(self):
        pass
    
    def should_exit(self,
                    symbol: str,
                    entry_price: float,
                    current_price: float,
                    days_held: int,
                    target_pct: float = 5.0) -> ExitSignal:
        """Check if should exit position"""
        
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        try:
            df = yf.download(symbol, period='3mo', interval='1d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                return self._hold_signal(current_price)
            
            close = df['Close']
            
            # Calculate indicators
            rsi = self._calculate_rsi(close)
            trend = float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1])
            
            # Exit conditions
            
            # 1. Target reached
            if pnl_pct >= target_pct:
                if pnl_pct >= target_pct * 1.5:
                    return ExitSignal(
                        should_exit=True,
                        urgency="SOON",
                        reason=f"Target exceeded (+{pnl_pct:.1f}% vs {target_pct}% target)",
                        take_partial=True,
                        partial_pct=50,
                        suggested_exit=current_price,
                        trailing_stop=current_price * 0.97
                    )
                return ExitSignal(
                    should_exit=False,
                    urgency="HOLD",
                    reason=f"Target reached, consider trailing stop",
                    take_partial=True,
                    partial_pct=30,
                    suggested_exit=current_price * 1.02,
                    trailing_stop=current_price * 0.95
                )
            
            # 2. RSI overbought after profit
            if pnl_pct > 2 and rsi > 75:
                return ExitSignal(
                    should_exit=False,
                    urgency="SOON",
                    reason=f"RSI overbought ({rsi:.0f}), consider partial exit",
                    take_partial=True,
                    partial_pct=40,
                    suggested_exit=current_price,
                    trailing_stop=current_price * 0.96
                )
            
            # 3. Trend reversal
            if not trend and pnl_pct > 0:
                return ExitSignal(
                    should_exit=False,
                    urgency="SOON",
                    reason="Trend turning, protect profits",
                    take_partial=True,
                    partial_pct=50,
                    suggested_exit=current_price,
                    trailing_stop=entry_price * 1.01
                )
            
            # 4. Time decay (held too long)
            if days_held > 5 and pnl_pct < 1:
                return ExitSignal(
                    should_exit=True,
                    urgency="SOON",
                    reason=f"Dead money: {days_held} days, only +{pnl_pct:.1f}%",
                    take_partial=False,
                    partial_pct=100,
                    suggested_exit=current_price,
                    trailing_stop=entry_price * 0.98
                )
            
            # 5. Stop loss
            if pnl_pct < -3:
                return ExitSignal(
                    should_exit=True,
                    urgency="IMMEDIATE",
                    reason=f"Stop loss hit: {pnl_pct:.1f}%",
                    take_partial=False,
                    partial_pct=100,
                    suggested_exit=current_price,
                    trailing_stop=current_price
                )
            
            # Default: Hold
            return self._hold_signal(current_price)
            
        except Exception as e:
            logger.debug(f"Exit optimizer error: {e}")
            return self._hold_signal(current_price)
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _hold_signal(self, price: float) -> ExitSignal:
        return ExitSignal(
            should_exit=False,
            urgency="HOLD",
            reason="No exit signal",
            take_partial=False,
            partial_pct=0,
            suggested_exit=price * 1.05,
            trailing_stop=price * 0.95
        )


def get_exit_optimizer() -> ExitOptimizer:
    return ExitOptimizer()


if __name__ == "__main__":
    print("Testing ExitOptimizer...")
    eo = ExitOptimizer()
    
    # Test scenarios
    scenarios = [
        ("AAPL", 150, 158, 3, 5),  # 5% gain
        ("NVDA", 500, 485, 2, 5),   # -3% loss
        ("TSLA", 250, 252, 7, 5),   # Dead money
    ]
    
    for sym, entry, current, days, target in scenarios:
        sig = eo.should_exit(sym, entry, current, days, target)
        pnl = (current - entry) / entry * 100
        print(f"\n{sym}: Entry ${entry} → ${current} ({pnl:+.1f}%), {days}d")
        print(f"  Exit: {sig.should_exit} ({sig.urgency})")
        print(f"  Reason: {sig.reason}")
        if sig.take_partial:
            print(f"  Partial: {sig.partial_pct}%")
