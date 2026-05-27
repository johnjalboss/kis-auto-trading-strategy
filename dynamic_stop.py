"""
Dynamic Stop Loss Manager
==========================
Volatility-based dynamic stop loss adjustment.

Methods:
1. ATR-based trailing stop
2. Volatility regime adjustment
3. Support level protection
4. Time-based tightening
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


class VolatilityRegime(Enum):
    LOW = "LOW"      # VIX < 15 or ATR < 1.5%
    NORMAL = "NORMAL"  # VIX 15-25 or ATR 1.5-3%
    HIGH = "HIGH"    # VIX > 25 or ATR > 3%
    EXTREME = "EXTREME"  # VIX > 35 or ATR > 5%


@dataclass
class StopLossLevels:
    """Stop loss levels"""
    initial_stop: float
    current_stop: float
    trailing_stop: float
    support_stop: float
    
    recommended_stop: float
    stop_type: str  # "INITIAL", "TRAILING", "SUPPORT"
    
    distance_pct: float
    atr_multiplier: float


@dataclass
class DynamicStopResult:
    """Dynamic stop analysis"""
    symbol: str
    entry_price: float
    current_price: float
    
    volatility_regime: VolatilityRegime
    current_atr: float
    atr_pct: float
    
    stops: StopLossLevels
    
    should_tighten: bool
    tighten_reason: str
    
    take_profit_target: float
    risk_reward: float


class DynamicStopManager:
    """
    Dynamic Stop Loss Management
    
    Volatility-Based Adjustment:
    - Low vol: 1.0x ATR stop
    - Normal vol: 1.5x ATR stop
    - High vol: 2.0x ATR stop
    - Extreme vol: 2.5x ATR stop
    
    Time-Based Tightening:
    - Day 1: Full ATR cushion
    - Day 2-3: Tighten to 0.75x
    - Day 4+: Tighten to 0.5x or breakeven
    
    Trailing Logic:
    - Move stop only in profit direction
    - Never widen stop
    - Lock in gains at key levels
    """
    
    # ATR multipliers by regime
    ATR_MULTIPLIERS = {
        VolatilityRegime.LOW: 1.0,
        VolatilityRegime.NORMAL: 1.5,
        VolatilityRegime.HIGH: 2.0,
        VolatilityRegime.EXTREME: 2.5,
    }
    
    def __init__(self):
        self._positions: Dict[str, dict] = {}
    
    def register_position(self, symbol: str, entry_price: float, 
                         entry_time: datetime, side: str = "LONG"):
        """Register a new position"""
        self._positions[symbol] = {
            'entry_price': entry_price,
            'entry_time': entry_time,
            'side': side,
            'highest_price': entry_price,
            'lowest_price': entry_price,
            'current_stop': entry_price * 0.97,  # Initial 3% stop
        }
    
    def get_stops(self, symbol: str, current_price: float = None) -> DynamicStopResult:
        """Get dynamic stop levels for a position"""
        # Fetch data
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 20:
            return self._default_result(symbol)
        
        if current_price is None:
            current_price = df['Close'].iloc[-1]
        
        # Get position info
        position = self._positions.get(symbol, {
            'entry_price': current_price,
            'entry_time': datetime.now(),
            'side': 'LONG',
            'highest_price': current_price,
            'lowest_price': current_price,
            'current_stop': current_price * 0.97,
        })
        
        entry_price = position['entry_price']
        
        # Update highest/lowest
        if current_price > position['highest_price']:
            position['highest_price'] = current_price
        if current_price < position['lowest_price']:
            position['lowest_price'] = current_price
        
        # Calculate ATR
        atr = self._calculate_atr(df)
        atr_pct = atr / current_price
        
        # Determine volatility regime
        regime = self._determine_regime(atr_pct)
        
        # Get ATR multiplier
        atr_mult = self.ATR_MULTIPLIERS[regime]
        
        # Calculate stop levels
        # 1. Initial stop (from entry)
        initial_stop = entry_price - (atr * atr_mult)
        
        # 2. Trailing stop (from highest price)
        trailing_stop = position['highest_price'] - (atr * atr_mult * 0.75)
        
        # 3. Support-based stop
        support_stop = self._find_support_stop(df, current_price)
        
        # Time-based tightening
        days_held = (datetime.now() - position['entry_time']).days
        should_tighten = False
        tighten_reason = ""
        
        if days_held >= 4:
            # Tighten to breakeven or better
            if current_price > entry_price:
                trailing_stop = max(trailing_stop, entry_price * 1.005)
                should_tighten = True
                tighten_reason = f"Day {days_held}: Moving to breakeven+"
        elif days_held >= 2:
            # Tighten ATR multiplier
            trailing_stop = position['highest_price'] - (atr * atr_mult * 0.5)
            should_tighten = True
            tighten_reason = f"Day {days_held}: Tightening to 0.5x ATR"
        
        # Choose recommended stop (highest of all stops)
        all_stops = [initial_stop, trailing_stop, support_stop, position['current_stop']]
        recommended = max(all_stops)
        
        if recommended == trailing_stop:
            stop_type = "TRAILING"
        elif recommended == support_stop:
            stop_type = "SUPPORT"
        else:
            stop_type = "INITIAL"
        
        # Never lower the stop
        if recommended > position['current_stop']:
            position['current_stop'] = recommended
        else:
            recommended = position['current_stop']
        
        # Take profit target (2:1 R:R minimum)
        risk = entry_price - recommended
        take_profit = entry_price + (risk * 2)
        
        # Calculate risk/reward
        potential_profit = take_profit - current_price
        potential_loss = current_price - recommended
        risk_reward = potential_profit / potential_loss if potential_loss > 0 else 0
        
        stops = StopLossLevels(
            initial_stop=initial_stop,
            current_stop=position['current_stop'],
            trailing_stop=trailing_stop,
            support_stop=support_stop,
            recommended_stop=recommended,
            stop_type=stop_type,
            distance_pct=(current_price - recommended) / current_price,
            atr_multiplier=atr_mult
        )
        
        return DynamicStopResult(
            symbol=symbol,
            entry_price=entry_price,
            current_price=current_price,
            volatility_regime=regime,
            current_atr=atr,
            atr_pct=atr_pct,
            stops=stops,
            should_tighten=should_tighten,
            tighten_reason=tighten_reason,
            take_profit_target=take_profit,
            risk_reward=risk_reward
        )
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def _determine_regime(self, atr_pct: float) -> VolatilityRegime:
        """Determine volatility regime"""
        if atr_pct < 0.015:
            return VolatilityRegime.LOW
        elif atr_pct < 0.03:
            return VolatilityRegime.NORMAL
        elif atr_pct < 0.05:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def _find_support_stop(self, df: pd.DataFrame, current_price: float) -> float:
        """Find support level for stop placement"""
        # Use recent swing lows
        lows = df['Low'].tail(20)
        
        # Find swing lows below current price
        potential_supports = lows[lows < current_price * 0.99]
        
        if len(potential_supports) > 0:
            # Highest recent low = nearest support
            return potential_supports.max() * 0.995  # Slightly below support
        
        return current_price * 0.95  # Default 5% below
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period='30d', interval='1d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self, symbol: str) -> DynamicStopResult:
        """Return default result"""
        stops = StopLossLevels(0, 0, 0, 0, 0, "INITIAL", 0.03, 1.5)
        return DynamicStopResult(
            symbol=symbol, entry_price=0, current_price=0,
            volatility_regime=VolatilityRegime.NORMAL,
            current_atr=0, atr_pct=0, stops=stops,
            should_tighten=False, tighten_reason="",
            take_profit_target=0, risk_reward=0
        )


# Global instance
_manager = None

def get_stop_manager() -> DynamicStopManager:
    global _manager
    if _manager is None:
        _manager = DynamicStopManager()
    return _manager


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing DynamicStopManager...")
    
    manager = DynamicStopManager()
    
    # Simulate position
    manager.register_position("AAPL", 180.0, datetime.now() - timedelta(days=3))
    manager.register_position("TSLA", 250.0, datetime.now() - timedelta(days=1))
    
    for symbol in ["AAPL", "TSLA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = manager.get_stops(symbol)
        
        print(f"Entry: ${result.entry_price:.2f}")
        print(f"Current: ${result.current_price:.2f}")
        print(f"ATR: ${result.current_atr:.2f} ({result.atr_pct:.1%})")
        print(f"Regime: {result.volatility_regime.value}")
        print()
        print("Stops:")
        print(f"  Initial: ${result.stops.initial_stop:.2f}")
        print(f"  Trailing: ${result.stops.trailing_stop:.2f}")
        print(f"  Support: ${result.stops.support_stop:.2f}")
        print(f"  RECOMMENDED: ${result.stops.recommended_stop:.2f} ({result.stops.stop_type})")
        print(f"  Distance: {result.stops.distance_pct:.1%}")
        print()
        print(f"Take Profit: ${result.take_profit_target:.2f}")
        print(f"R/R Ratio: {result.risk_reward:.1f}")
        
        if result.should_tighten:
            print(f"⚠️ {result.tighten_reason}")
