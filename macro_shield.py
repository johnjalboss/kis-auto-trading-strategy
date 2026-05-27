"""
Macro-Defense Shield: Multi-Dimensional Macro Risk Management System
=====================================================================
Institutional-grade risk filter system for algorithmic trading.

Filters:
1. VIX Regime (Fear Switch) - VIX vs 60-day SMA
2. Sector Sentiment (Greed Switch) - XLK/XLP ratio vs 20-day SMA
3. Market Breadth (Health Switch) - RSP/SPY relative strength
4. Macro Headwinds - DXY trend & TNX RSI

Output: Macro Score (0-100) → Position Sizing
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger


# ==============================================
# Enums and Data Classes
# ==============================================

class RiskLevel(Enum):
    """Risk level classification"""
    HIGH_RISK = "HIGH_RISK"      # Score < 50: No buy, sell all
    MEDIUM_RISK = "MEDIUM_RISK"  # Score 50-80: Half size
    LOW_RISK = "LOW_RISK"        # Score > 80: Full size


@dataclass
class FilterResult:
    """Individual filter result"""
    name: str
    is_bullish: bool
    score: float  # 0-25 contribution
    metric_value: float
    threshold: float
    description: str


@dataclass
class MacroScore:
    """Aggregated macro risk assessment"""
    total_score: float  # 0-100
    risk_level: RiskLevel
    position_multiplier: float  # Position size multiplier
    filters: List[FilterResult]
    timestamp: datetime
    recommendation: str
    
    def __str__(self):
        emoji = "🟢" if self.risk_level == RiskLevel.LOW_RISK else \
                "🟡" if self.risk_level == RiskLevel.MEDIUM_RISK else "🔴"
        return f"{emoji} Macro Score: {self.total_score:.0f}/100 | {self.risk_level.value} | x{self.position_multiplier:.1f}"


@dataclass
class SafeBasket:
    """Defensive sector allocation"""
    symbols: List[str] = field(default_factory=lambda: ["XLU", "XLP", "XLV"])
    weights: List[float] = field(default_factory=lambda: [0.34, 0.33, 0.33])


# ==============================================
# Technical Indicators
# ==============================================

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period, min_periods=1).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_relative_strength(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Relative Strength: A / B ratio normalized"""
    return series_a / series_b


# ==============================================
# MacroRiskManager Class
# ==============================================

class MacroRiskManager:
    """
    Multi-Dimensional Macro Risk Management System
    
    Analyzes market conditions through 4 independent filters and produces
    an integrated Macro Score (0-100) that determines position sizing.
    
    Filters (each contributes 0-25 points):
    1. VIX Regime: VIX < 60-day SMA = Bullish (+25)
    2. Sector Sentiment: XLK/XLP > 20-day SMA = Bullish (+25)
    3. Market Breadth: RSP/SPY > 20-day SMA = Bullish (+25)
    4. Macro Headwinds: No DXY/TNX stress = Bullish (+25)
    """
    
    # Tickers to fetch
    MARKET_TICKERS = ["SPY", "RSP"]
    RISK_TICKERS = ["^VIX"]
    SECTOR_TICKERS = ["XLK", "XLP", "XLU", "XLV", "XLY"]
    MACRO_TICKERS = ["UUP", "^TNX"]  # UUP = Dollar ETF (DX-Y.NYB not on KIS)
    
    ALL_TICKERS = MARKET_TICKERS + RISK_TICKERS + SECTOR_TICKERS + MACRO_TICKERS
    
    # Filter parameters
    VIX_SMA_PERIOD = 60
    SECTOR_SMA_PERIOD = 20
    BREADTH_SMA_PERIOD = 20
    DXY_SMA_PERIOD = 50
    TNX_RSI_THRESHOLD = 70
    
    def __init__(self, lookback_days: int = 365):
        """
        Initialize MacroRiskManager
        
        Args:
            lookback_days: Number of days of historical data to fetch
        """
        self.lookback_days = lookback_days
        self._data: Dict[str, pd.DataFrame] = {}
        self._last_update: Optional[datetime] = None
        self._last_score: Optional[MacroScore] = None
        self.safe_basket = SafeBasket()
        
    def fetch_data(self, force_refresh: bool = False) -> bool:
        """
        Fetch 1-year historical data for all tickers
        
        Args:
            force_refresh: Force data refresh even if cached
            
        Returns:
            bool: True if successful
        """
        # Check if refresh needed
        if not force_refresh and self._last_update:
            if datetime.now() - self._last_update < timedelta(hours=1):
                logger.debug("Using cached data (updated {})", self._last_update)
                return True
        
        logger.info("Fetching macro data for {} tickers...", len(self.ALL_TICKERS))
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days)
            
            for ticker in self.ALL_TICKERS:
                logger.debug("Fetching {}", ticker)
                try:
                    data = yf.download(
                        ticker, 
                        start=start_date, 
                        end=end_date,
                        progress=False,
                        auto_adjust=True
                    )
                    if len(data) > 0:
                        self._data[ticker] = data
                    else:
                        logger.warning("No data for {}", ticker)
                except Exception as e:
                    logger.warning("Failed to fetch {}: {}", ticker, e)
            
            self._last_update = datetime.now()
            logger.success("Fetched data for {} tickers", len(self._data))
            return True
            
        except Exception as e:
            logger.error("Data fetch failed: {}", e)
            return False
    
    def _get_close(self, ticker: str) -> Optional[pd.Series]:
        """Get closing prices for a ticker"""
        if ticker not in self._data:
            return None
        df = self._data[ticker]
        
        # Handle different yfinance return formats
        if "Close" in df.columns:
            close = df["Close"]
            # If it's a DataFrame (multi-column), get first column
            if isinstance(close, pd.DataFrame):
                return close.iloc[:, 0]
            return close
        return None
    
    # ==============================================
    # Filter 1: VIX Regime (Fear Switch)
    # ==============================================
    
    def filter_vix_regime(self) -> FilterResult:
        """
        VIX Regime Filter (Fear Switch)
        
        Logic: VIX < 60-day SMA = RISK-ON (Bullish)
        
        Returns:
            FilterResult with score 0-25
        """
        vix = self._get_close("^VIX")
        
        if vix is None or len(vix) < self.VIX_SMA_PERIOD:
            return FilterResult(
                name="VIX Regime",
                is_bullish=False,
                score=0,
                metric_value=0,
                threshold=0,
                description="Insufficient VIX data"
            )
        
        current_vix = vix.iloc[-1]
        vix_sma = calculate_sma(vix, self.VIX_SMA_PERIOD).iloc[-1]
        
        # VIX below SMA = Low fear = Bullish
        is_bullish = current_vix < vix_sma
        
        # Score: Full points if VIX is significantly below SMA
        if is_bullish:
            # More bullish as VIX drops further below SMA
            ratio = (vix_sma - current_vix) / vix_sma
            score = min(25, 15 + ratio * 100)  # 15-25 range
        else:
            # Penalty based on how far above SMA
            ratio = (current_vix - vix_sma) / vix_sma
            score = max(0, 15 - ratio * 50)  # 0-15 range
        
        return FilterResult(
            name="VIX Regime",
            is_bullish=is_bullish,
            score=score,
            metric_value=current_vix,
            threshold=vix_sma,
            description=f"VIX {current_vix:.1f} {'<' if is_bullish else '>'} 60d SMA {vix_sma:.1f}"
        )
    
    # ==============================================
    # Filter 2: Sector Sentiment (Greed Switch)
    # ==============================================
    
    def filter_sector_sentiment(self) -> FilterResult:
        """
        Sector Sentiment Filter (Greed Switch)
        
        Logic: XLK/XLP ratio > 20-day SMA = Risk appetite (Bullish)
        When tech outperforms staples, investors are risk-seeking.
        
        Returns:
            FilterResult with score 0-25
        """
        xlk = self._get_close("XLK")
        xlp = self._get_close("XLP")
        
        if xlk is None or xlp is None:
            return FilterResult(
                name="Sector Sentiment",
                is_bullish=False,
                score=0,
                metric_value=0,
                threshold=0,
                description="Insufficient sector data"
            )
        
        # Calculate XLK/XLP ratio
        ratio = calculate_relative_strength(xlk, xlp)
        current_ratio = ratio.iloc[-1]
        ratio_sma = calculate_sma(ratio, self.SECTOR_SMA_PERIOD).iloc[-1]
        
        # Ratio above SMA = Tech outperforming = Bullish
        is_bullish = current_ratio > ratio_sma
        
        if is_bullish:
            deviation = (current_ratio - ratio_sma) / ratio_sma
            score = min(25, 15 + deviation * 200)
        else:
            deviation = (ratio_sma - current_ratio) / ratio_sma
            score = max(0, 15 - deviation * 100)
        
        return FilterResult(
            name="Sector Sentiment",
            is_bullish=is_bullish,
            score=score,
            metric_value=current_ratio,
            threshold=ratio_sma,
            description=f"XLK/XLP {current_ratio:.3f} {'>' if is_bullish else '<'} 20d SMA {ratio_sma:.3f}"
        )
    
    # ==============================================
    # Filter 3: Market Breadth (Health Switch)
    # ==============================================
    
    def filter_market_breadth(self) -> FilterResult:
        """
        Market Breadth Filter (Health Switch)
        
        Logic: RSP/SPY (equal-weight vs cap-weight) > 20-day SMA = Healthy breadth
        If cap-weighted outperforms, rally is narrow (unhealthy).
        
        Returns:
            FilterResult with score 0-25
        """
        rsp = self._get_close("RSP")
        spy = self._get_close("SPY")
        
        if rsp is None or spy is None:
            return FilterResult(
                name="Market Breadth",
                is_bullish=False,
                score=0,
                metric_value=0,
                threshold=0,
                description="Insufficient breadth data"
            )
        
        # Calculate RSP/SPY relative strength
        rs = calculate_relative_strength(rsp, spy)
        current_rs = rs.iloc[-1]
        rs_sma = calculate_sma(rs, self.BREADTH_SMA_PERIOD).iloc[-1]
        
        # Breadth improving = Equal weight catching up = Bullish
        is_bullish = current_rs > rs_sma
        
        if is_bullish:
            deviation = (current_rs - rs_sma) / rs_sma
            score = min(25, 15 + deviation * 500)
        else:
            deviation = (rs_sma - current_rs) / rs_sma
            score = max(0, 15 - deviation * 300)
        
        return FilterResult(
            name="Market Breadth",
            is_bullish=is_bullish,
            score=score,
            metric_value=current_rs,
            threshold=rs_sma,
            description=f"RSP/SPY {current_rs:.4f} {'>' if is_bullish else '<'} 20d SMA {rs_sma:.4f}"
        )
    
    # ==============================================
    # Filter 4: Macro Headwinds
    # ==============================================
    
    def filter_macro_headwinds(self) -> FilterResult:
        """
        Macro Headwinds Filter
        
        Checks two conditions:
        1. DXY (Dollar) above 50-day SMA and rising = Headwind
        2. TNX (10Y Yield) RSI > 70 = Overbought yields = Headwind
        
        Either condition triggers partial penalty.
        Both conditions = Full headwind.
        
        Returns:
            FilterResult with score 0-25
        """
        dxy = self._get_close("UUP")  # Dollar ETF
        tnx = self._get_close("^TNX")
        
        headwinds = []
        penalty_count = 0
        
        # Check DXY
        dxy_headwind = False
        dxy_value = 0
        dxy_sma = 0
        
        if dxy is not None and len(dxy) >= self.DXY_SMA_PERIOD:
            dxy_value = dxy.iloc[-1]
            dxy_sma = calculate_sma(dxy, self.DXY_SMA_PERIOD).iloc[-1]
            dxy_trend = dxy.iloc[-1] > dxy.iloc[-5]  # Rising over 5 days
            
            if dxy_value > dxy_sma and dxy_trend:
                dxy_headwind = True
                penalty_count += 1
                headwinds.append(f"DXY {dxy_value:.1f} > 50d SMA {dxy_sma:.1f} ↑")
        
        # Check TNX RSI
        tnx_headwind = False
        tnx_rsi = 0
        
        if tnx is not None and len(tnx) >= 20:
            rsi = calculate_rsi(tnx, 14)
            tnx_rsi = rsi.iloc[-1]
            
            if tnx_rsi > self.TNX_RSI_THRESHOLD:
                tnx_headwind = True
                penalty_count += 1
                headwinds.append(f"TNX RSI {tnx_rsi:.1f} > {self.TNX_RSI_THRESHOLD}")
        
        # Calculate score (full points if no headwinds)
        is_bullish = penalty_count == 0
        
        if penalty_count == 0:
            score = 25  # No headwinds
        elif penalty_count == 1:
            score = 12  # One headwind
        else:
            score = 0   # Both headwinds
        
        description = " | ".join(headwinds) if headwinds else "No macro headwinds"
        
        return FilterResult(
            name="Macro Headwinds",
            is_bullish=is_bullish,
            score=score,
            metric_value=penalty_count,
            threshold=0,
            description=description
        )
    
    # ==============================================
    # Integrated Scoring
    # ==============================================
    
    def calculate_macro_score(self) -> MacroScore:
        """
        Calculate integrated Macro Score (0-100)
        
        Aggregates all 4 filters and determines position sizing.
        
        Returns:
            MacroScore with recommendation
        """
        # Ensure data is fresh
        if not self._data:
            self.fetch_data()
        
        # Run all filters
        filter_results = [
            self.filter_vix_regime(),
            self.filter_sector_sentiment(),
            self.filter_market_breadth(),
            self.filter_macro_headwinds()
        ]
        
        # Calculate total score
        total_score = sum(f.score for f in filter_results)
        total_score = max(0, min(100, total_score))  # Clamp to 0-100
        
        # Determine risk level and position multiplier
        if total_score >= 80:
            risk_level = RiskLevel.LOW_RISK
            position_multiplier = 1.0
            recommendation = "✅ FULL SIZE: All systems green. Aggressive positioning."
        elif total_score >= 50:
            risk_level = RiskLevel.MEDIUM_RISK
            position_multiplier = 0.5
            recommendation = "⚠️ HALF SIZE: Mixed signals. Reduce exposure."
        else:
            risk_level = RiskLevel.HIGH_RISK
            position_multiplier = 0.0
            recommendation = f"🚫 NO BUY: High risk. Consider Safe Basket: {self.safe_basket.symbols}"
        
        macro_score = MacroScore(
            total_score=total_score,
            risk_level=risk_level,
            position_multiplier=position_multiplier,
            filters=filter_results,
            timestamp=datetime.now(),
            recommendation=recommendation
        )
        
        self._last_score = macro_score
        
        # Log results
        logger.info("=" * 60)
        logger.info("MACRO-DEFENSE SHIELD ANALYSIS")
        logger.info("=" * 60)
        
        for f in filter_results:
            emoji = "🟢" if f.is_bullish else "🔴"
            logger.info("{} {} | Score: {:.0f}/25 | {}", 
                       emoji, f.name, f.score, f.description)
        
        logger.info("-" * 60)
        logger.info("{}", macro_score)
        logger.info(recommendation)
        logger.info("=" * 60)
        
        return macro_score
    
    @property
    def last_score(self) -> Optional[MacroScore]:
        """Get last calculated score"""
        return self._last_score
    
    def get_position_size(self, base_amount: float) -> float:
        """
        Calculate position size based on last macro score
        
        Args:
            base_amount: Base position size in USD
            
        Returns:
            Adjusted position size
        """
        if self._last_score is None:
            logger.warning("No macro score available, using 50% position")
            return base_amount * 0.5
        
        return base_amount * self._last_score.position_multiplier
    
    def should_rotate_to_safe(self) -> bool:
        """Check if should rotate to safe basket"""
        if self._last_score is None:
            return False
        return self._last_score.risk_level == RiskLevel.HIGH_RISK
    
    def get_safe_basket(self) -> SafeBasket:
        """Get safe basket allocation"""
        return self.safe_basket


# ==============================================
# Test
# ==============================================

if __name__ == "__main__":
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    print("=" * 60)
    print("MACRO-DEFENSE SHIELD TEST")
    print("=" * 60)
    
    manager = MacroRiskManager(lookback_days=365)
    
    # Fetch data
    print("\n📊 Fetching macro data...")
    manager.fetch_data()
    
    # Calculate score
    print("\n🔍 Analyzing market conditions...")
    score = manager.calculate_macro_score()
    
    # Summary
    print("\n📋 SUMMARY")
    print("-" * 40)
    print(f"Total Score: {score.total_score:.0f}/100")
    print(f"Risk Level: {score.risk_level.value}")
    print(f"Position Multiplier: {score.position_multiplier:.1f}x")
    print(f"Should Rotate to Safe: {manager.should_rotate_to_safe()}")
    
    if manager.should_rotate_to_safe():
        basket = manager.get_safe_basket()
        print(f"Safe Basket: {basket.symbols}")
