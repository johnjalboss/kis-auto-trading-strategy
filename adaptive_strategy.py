"""
Adaptive Strategy Selector
============================
Automatically switches strategies based on market regime.

Strategies:
- BULL: Trend following, momentum
- BEAR: Inverse, hedging, cash
- SIDEWAYS: Mean reversion, range trading
- HIGH_VOL: Reduce exposure, wider stops
- LOW_VOL: Increase exposure, tighter stops
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


class MarketRegime(Enum):
    BULL_TRENDING = "BULL_TRENDING"
    BULL_VOLATILE = "BULL_VOLATILE"
    BEAR_TRENDING = "BEAR_TRENDING"
    BEAR_VOLATILE = "BEAR_VOLATILE"
    SIDEWAYS_QUIET = "SIDEWAYS_QUIET"
    SIDEWAYS_CHOPPY = "SIDEWAYS_CHOPPY"


class StrategyType(Enum):
    MOMENTUM_LONG = "MOMENTUM_LONG"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MEAN_REVERSION = "MEAN_REVERSION"
    RANGE_TRADING = "RANGE_TRADING"
    DEFENSIVE = "DEFENSIVE"
    CASH = "CASH"
    INVERSE_ETF = "INVERSE_ETF"


@dataclass
class StrategyAllocation:
    """Strategy allocation"""
    primary_strategy: StrategyType
    secondary_strategy: Optional[StrategyType]
    
    # Allocation percentages
    equity_allocation: float  # 0-100%
    cash_allocation: float
    hedge_allocation: float
    
    # Position settings
    max_position_size: float
    stop_loss_multiplier: float  # ATR multiplier
    take_profit_multiplier: float
    
    # Filters
    min_score_threshold: int
    prefer_quality: bool
    prefer_momentum: bool
    avoid_volatility: bool


@dataclass
class AdaptiveSignal:
    """Adaptive strategy result"""
    current_regime: MarketRegime
    regime_confidence: int
    regime_duration_days: int
    
    # Strategy
    allocation: StrategyAllocation
    
    # Market conditions
    trend_strength: float
    volatility_regime: str
    breadth: str
    
    # Recommendations
    action_bias: str  # "LONG", "SHORT", "NEUTRAL"
    sectors_to_favor: List[str]
    sectors_to_avoid: List[str]
    
    details: List[str]


class AdaptiveStrategySelector:
    """
    Adaptive Strategy Selection
    
    Philosophy:
    - Don't fight the market
    - Preserve capital in bad times
    - Maximize when conditions favor
    - Always have a strategy
    
    Regime Detection:
    1. Trend: SMA 50 vs 200
    2. Momentum: 1-month performance
    3. Volatility: VIX level
    4. Breadth: % above SMA
    
    Strategy Matrix:
    
    | Regime           | Primary        | Equity | Stop  |
    |------------------|----------------|--------|-------|
    | Bull Trending    | Momentum       | 80%    | 1.5x  |
    | Bull Volatile    | Trend Follow   | 60%    | 2.5x  |
    | Bear Trending    | Inverse/Cash   | 20%    | 1.0x  |
    | Bear Volatile    | Cash           | 10%    | 0.5x  |
    | Sideways Quiet   | Mean Reversion | 70%    | 1.0x  |
    | Sideways Choppy  | Range Trading  | 50%    | 2.0x  |
    """
    
    # Strategy configurations
    STRATEGY_CONFIG = {
        MarketRegime.BULL_TRENDING: StrategyAllocation(
            primary_strategy=StrategyType.MOMENTUM_LONG,
            secondary_strategy=StrategyType.TREND_FOLLOWING,
            equity_allocation=0.80,
            cash_allocation=0.15,
            hedge_allocation=0.05,
            max_position_size=0.10,
            stop_loss_multiplier=1.5,
            take_profit_multiplier=3.0,
            min_score_threshold=30,
            prefer_quality=False,
            prefer_momentum=True,
            avoid_volatility=False
        ),
        MarketRegime.BULL_VOLATILE: StrategyAllocation(
            primary_strategy=StrategyType.TREND_FOLLOWING,
            secondary_strategy=StrategyType.DEFENSIVE,
            equity_allocation=0.60,
            cash_allocation=0.30,
            hedge_allocation=0.10,
            max_position_size=0.07,
            stop_loss_multiplier=2.5,
            take_profit_multiplier=2.5,
            min_score_threshold=40,
            prefer_quality=True,
            prefer_momentum=True,
            avoid_volatility=True
        ),
        MarketRegime.BEAR_TRENDING: StrategyAllocation(
            primary_strategy=StrategyType.DEFENSIVE,
            secondary_strategy=StrategyType.INVERSE_ETF,
            equity_allocation=0.20,
            cash_allocation=0.60,
            hedge_allocation=0.20,
            max_position_size=0.05,
            stop_loss_multiplier=1.0,
            take_profit_multiplier=2.0,
            min_score_threshold=60,
            prefer_quality=True,
            prefer_momentum=False,
            avoid_volatility=True
        ),
        MarketRegime.BEAR_VOLATILE: StrategyAllocation(
            primary_strategy=StrategyType.CASH,
            secondary_strategy=StrategyType.DEFENSIVE,
            equity_allocation=0.10,
            cash_allocation=0.80,
            hedge_allocation=0.10,
            max_position_size=0.03,
            stop_loss_multiplier=0.5,
            take_profit_multiplier=1.5,
            min_score_threshold=70,
            prefer_quality=True,
            prefer_momentum=False,
            avoid_volatility=True
        ),
        MarketRegime.SIDEWAYS_QUIET: StrategyAllocation(
            primary_strategy=StrategyType.MEAN_REVERSION,
            secondary_strategy=StrategyType.RANGE_TRADING,
            equity_allocation=0.70,
            cash_allocation=0.25,
            hedge_allocation=0.05,
            max_position_size=0.08,
            stop_loss_multiplier=1.0,
            take_profit_multiplier=1.5,
            min_score_threshold=35,
            prefer_quality=True,
            prefer_momentum=False,
            avoid_volatility=False
        ),
        MarketRegime.SIDEWAYS_CHOPPY: StrategyAllocation(
            primary_strategy=StrategyType.RANGE_TRADING,
            secondary_strategy=StrategyType.MEAN_REVERSION,
            equity_allocation=0.50,
            cash_allocation=0.40,
            hedge_allocation=0.10,
            max_position_size=0.05,
            stop_loss_multiplier=2.0,
            take_profit_multiplier=1.5,
            min_score_threshold=50,
            prefer_quality=True,
            prefer_momentum=False,
            avoid_volatility=True
        )
    }
    
    # Sector preferences by regime
    SECTOR_FAVOR = {
        MarketRegime.BULL_TRENDING: ["XLK", "XLY", "XLF"],
        MarketRegime.BULL_VOLATILE: ["XLK", "XLV", "XLI"],
        MarketRegime.BEAR_TRENDING: ["XLU", "XLP", "XLV"],
        MarketRegime.BEAR_VOLATILE: ["XLU", "XLP"],
        MarketRegime.SIDEWAYS_QUIET: ["XLF", "XLI", "XLK"],
        MarketRegime.SIDEWAYS_CHOPPY: ["XLP", "XLV", "XLU"]
    }
    
    SECTOR_AVOID = {
        MarketRegime.BULL_TRENDING: ["XLU"],
        MarketRegime.BULL_VOLATILE: ["XLE", "XLB"],
        MarketRegime.BEAR_TRENDING: ["XLY", "XLK", "XLE"],
        MarketRegime.BEAR_VOLATILE: ["XLY", "XLK", "XLE", "XLF"],
        MarketRegime.SIDEWAYS_QUIET: ["XLE"],
        MarketRegime.SIDEWAYS_CHOPPY: ["XLE", "XLB"]
    }
    
    def __init__(self):
        self._regime_history: List[str] = []
    
    def analyze(self) -> AdaptiveSignal:
        """Analyze market and select strategy"""
        details = []
        
        # Fetch market data
        spy = self._fetch_data("SPY")
        vix = self._fetch_data("^VIX")
        
        if spy is None or len(spy) < 200:
            return self._default_result()
        
        close = spy['Close']
        
        # 1. Detect regime
        regime, confidence, trend_strength, vol_regime, breadth = self._detect_regime(close, vix)
        details.append(f"REGIME:{regime.value}")
        
        # 2. Get strategy allocation
        allocation = self.STRATEGY_CONFIG.get(regime, self.STRATEGY_CONFIG[MarketRegime.SIDEWAYS_QUIET])
        
        # 3. Calculate regime duration
        self._regime_history.append(regime.value)
        if len(self._regime_history) > 50:
            self._regime_history = self._regime_history[-50:]
        
        duration = 1
        for r in reversed(self._regime_history[:-1]):
            if r == regime.value:
                duration += 1
            else:
                break
        
        # 4. Determine action bias
        if regime in [MarketRegime.BULL_TRENDING, MarketRegime.BULL_VOLATILE]:
            bias = "LONG"
        elif regime in [MarketRegime.BEAR_TRENDING, MarketRegime.BEAR_VOLATILE]:
            bias = "SHORT" if allocation.equity_allocation > 0.2 else "NEUTRAL"
        else:
            bias = "NEUTRAL"
        
        # 5. Get sector recommendations
        sectors_favor = self.SECTOR_FAVOR.get(regime, [])
        sectors_avoid = self.SECTOR_AVOID.get(regime, [])
        
        details.append(f"EQUITY:{allocation.equity_allocation:.0%}")
        details.append(f"CASH:{allocation.cash_allocation:.0%}")
        
        return AdaptiveSignal(
            current_regime=regime,
            regime_confidence=confidence,
            regime_duration_days=duration,
            allocation=allocation,
            trend_strength=trend_strength,
            volatility_regime=vol_regime,
            breadth=breadth,
            action_bias=bias,
            sectors_to_favor=sectors_favor,
            sectors_to_avoid=sectors_avoid,
            details=details
        )
    
    def _detect_regime(self, close: pd.Series, vix: Optional[pd.DataFrame]):
        """Detect market regime"""
        # Trend
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        current = close.iloc[-1]
        
        # Trend strength
        if sma200 > 0:
            trend_strength = (sma50 / sma200 - 1) * 100
        else:
            trend_strength = 0
        
        # Uptrend or downtrend
        is_uptrend = current > sma50 > sma200
        is_downtrend = current < sma50 < sma200
        is_sideways = not is_uptrend and not is_downtrend
        
        # Volatility
        vix_level = 20
        if vix is not None and not vix.empty:
            vix_level = float(vix['Close'].iloc[-1])
        
        is_high_vol = vix_level > 25
        is_low_vol = vix_level < 15
        vol_regime = "HIGH" if is_high_vol else ("LOW" if is_low_vol else "NORMAL")
        
        # Breadth (simplified)
        returns_20d = (current / close.iloc[-20] - 1) if len(close) >= 20 else 0
        breadth = "STRONG" if returns_20d > 0.03 else ("WEAK" if returns_20d < -0.03 else "NEUTRAL")
        
        # Determine regime
        if is_uptrend:
            if is_high_vol:
                regime = MarketRegime.BULL_VOLATILE
                confidence = 70
            else:
                regime = MarketRegime.BULL_TRENDING
                confidence = 85
        elif is_downtrend:
            if is_high_vol:
                regime = MarketRegime.BEAR_VOLATILE
                confidence = 80
            else:
                regime = MarketRegime.BEAR_TRENDING
                confidence = 75
        else:
            if is_high_vol:
                regime = MarketRegime.SIDEWAYS_CHOPPY
                confidence = 65
            else:
                regime = MarketRegime.SIDEWAYS_QUIET
                confidence = 70
        
        return regime, confidence, trend_strength, vol_regime, breadth
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self) -> AdaptiveSignal:
        """Default result"""
        regime = MarketRegime.SIDEWAYS_QUIET
        return AdaptiveSignal(
            current_regime=regime,
            regime_confidence=50,
            regime_duration_days=1,
            allocation=self.STRATEGY_CONFIG[regime],
            trend_strength=0,
            volatility_regime="NORMAL",
            breadth="NEUTRAL",
            action_bias="NEUTRAL",
            sectors_to_favor=[],
            sectors_to_avoid=[],
            details=[]
        )


# Global
_selector = None

def get_adaptive_selector() -> AdaptiveStrategySelector:
    global _selector
    if _selector is None:
        _selector = AdaptiveStrategySelector()
    return _selector


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing AdaptiveStrategySelector...")
    
    selector = AdaptiveStrategySelector()
    result = selector.analyze()
    
    print(f"\n{'='*60}")
    print("ADAPTIVE STRATEGY ANALYSIS")
    print('='*60)
    print(f"Regime: {result.current_regime.value}")
    print(f"Confidence: {result.regime_confidence}%")
    print(f"Duration: {result.regime_duration_days} days")
    print()
    print(f"Trend Strength: {result.trend_strength:+.2f}%")
    print(f"Volatility: {result.volatility_regime}")
    print(f"Breadth: {result.breadth}")
    print()
    
    alloc = result.allocation
    print("Strategy Allocation:")
    print(f"  Primary: {alloc.primary_strategy.value}")
    print(f"  Secondary: {alloc.secondary_strategy.value if alloc.secondary_strategy else 'None'}")
    print(f"  Equity: {alloc.equity_allocation:.0%}")
    print(f"  Cash: {alloc.cash_allocation:.0%}")
    print(f"  Hedge: {alloc.hedge_allocation:.0%}")
    print()
    print(f"Position Settings:")
    print(f"  Max Size: {alloc.max_position_size:.0%}")
    print(f"  Stop: {alloc.stop_loss_multiplier}x ATR")
    print(f"  Target: {alloc.take_profit_multiplier}x ATR")
    print(f"  Min Score: {alloc.min_score_threshold}")
    print()
    print(f"Bias: {result.action_bias}")
    print(f"Favor: {result.sectors_to_favor}")
    print(f"Avoid: {result.sectors_to_avoid}")
    print(f"Details: {result.details}")
