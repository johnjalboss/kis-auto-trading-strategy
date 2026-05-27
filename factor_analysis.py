"""
Factor Analysis Engine
========================
Multi-factor quantitative stock analysis.

Factors:
1. Momentum - Price momentum across timeframes
2. Value - Valuation metrics
3. Quality - Financial health
4. Size - Market cap dynamics
5. Volatility - Risk-adjusted returns
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class FactorScores:
    """Individual factor scores"""
    momentum_score: int      # -100 to +100
    value_score: int         # -100 to +100
    quality_score: int       # -100 to +100
    size_score: int          # -100 to +100
    volatility_score: int    # -100 to +100


@dataclass
class FactorSignal:
    """Factor analysis result"""
    symbol: str
    
    factors: FactorScores
    
    # Composite
    composite_score: int     # -100 to +100
    factor_rank: str         # "STRONG", "MODERATE", "WEAK", "AVOID"
    
    # Best factors
    strongest_factors: List[str]
    weakest_factors: List[str]
    
    # Factor details
    pe_ratio: float
    pb_ratio: float
    profit_margin: float
    roe: float
    debt_equity: float
    market_cap: float
    
    signal: str
    details: List[str]


class FactorAnalyzer:
    """
    Quant Factor Analysis
    
    Uses factor investing principles:
    
    1. MOMENTUM (30% weight)
       - 12-month return
       - 6-month return  
       - 1-month return
    
    2. VALUE (25% weight)
       - P/E ratio
       - P/B ratio
       - P/S ratio
    
    3. QUALITY (25% weight)
       - ROE
       - Profit margin
       - Debt/Equity
    
    4. SIZE (10% weight)
       - Market cap (prefer mid-cap)
    
    5. VOLATILITY (10% weight)
       - Low volatility premium
    """
    
    FACTOR_WEIGHTS = {
        'momentum': 0.30,
        'value': 0.25,
        'quality': 0.25,
        'size': 0.10,
        'volatility': 0.10
    }
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
    
    def analyze(self, symbol: str) -> FactorSignal:
        """Analyze all factors"""
        details = []
        
        # Fetch data
        df = self._fetch_price_data(symbol)
        info = self._fetch_info(symbol)
        
        if df is None or len(df) < 20:
            return self._neutral_result(symbol)
        
        # Calculate each factor
        momentum = self._calc_momentum(df)
        value = self._calc_value(info)
        quality = self._calc_quality(info)
        size = self._calc_size(info)
        volatility = self._calc_volatility(df)
        
        factors = FactorScores(
            momentum_score=momentum,
            value_score=value,
            quality_score=quality,
            size_score=size,
            volatility_score=volatility
        )
        
        # Weighted composite
        composite = (
            momentum * self.FACTOR_WEIGHTS['momentum'] +
            value * self.FACTOR_WEIGHTS['value'] +
            quality * self.FACTOR_WEIGHTS['quality'] +
            size * self.FACTOR_WEIGHTS['size'] +
            volatility * self.FACTOR_WEIGHTS['volatility']
        )
        composite = int(composite)
        
        # Identify strongest/weakest
        factor_dict = {
            'Momentum': momentum,
            'Value': value,
            'Quality': quality,
            'Size': size,
            'Volatility': volatility
        }
        
        sorted_factors = sorted(factor_dict.items(), key=lambda x: x[1], reverse=True)
        strongest = [f[0] for f in sorted_factors[:2] if f[1] > 30]
        weakest = [f[0] for f in sorted_factors[-2:] if f[1] < -30]
        
        # Rank
        if composite >= 50:
            rank = "STRONG"
        elif composite >= 20:
            rank = "MODERATE"
        elif composite >= -20:
            rank = "WEAK"
        else:
            rank = "AVOID"
        
        # Signal
        if composite >= 40:
            signal = "STRONG_BUY"
        elif composite >= 15:
            signal = "BUY"
        elif composite <= -40:
            signal = "STRONG_SELL"
        elif composite <= -15:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        # Extract metrics
        pe = info.get('trailingPE', 0) or info.get('forwardPE', 0) or 0
        pb = info.get('priceToBook', 0) or 0
        margin = info.get('profitMargins', 0) or 0
        roe = info.get('returnOnEquity', 0) or 0
        debt_eq = info.get('debtToEquity', 0) or 0
        mcap = info.get('marketCap', 0) or 0
        
        # Build details
        for name, score in factor_dict.items():
            if score > 30:
                details.append(f"{name}:+{score}")
            elif score < -30:
                details.append(f"{name}:{score}")
        
        return FactorSignal(
            symbol=symbol,
            factors=factors,
            composite_score=composite,
            factor_rank=rank,
            strongest_factors=strongest,
            weakest_factors=weakest,
            pe_ratio=pe,
            pb_ratio=pb,
            profit_margin=margin,
            roe=roe,
            debt_equity=debt_eq,
            market_cap=mcap,
            signal=signal,
            details=details
        )
    
    def _calc_momentum(self, df: pd.DataFrame) -> int:
        """Calculate momentum factor"""
        close = df['Close']
        score = 0
        
        # 12-month momentum (if available)
        if len(close) >= 252:
            ret_12m = close.iloc[-1] / close.iloc[-252] - 1
            if ret_12m > 0.30: score += 40
            elif ret_12m > 0.15: score += 30
            elif ret_12m > 0.05: score += 15
            elif ret_12m < -0.15: score -= 30
        
        # 6-month momentum
        if len(close) >= 126:
            ret_6m = close.iloc[-1] / close.iloc[-126] - 1
            if ret_6m > 0.20: score += 30
            elif ret_6m > 0.10: score += 20
            elif ret_6m < -0.15: score -= 25
        elif len(close) >= 60:
            ret_60d = close.iloc[-1] / close.iloc[-60] - 1
            if ret_60d > 0.10: score += 25
            elif ret_60d < -0.10: score -= 20
        
        # 1-month momentum
        if len(close) >= 21:
            ret_1m = close.iloc[-1] / close.iloc[-21] - 1
            if ret_1m > 0.08: score += 20
            elif ret_1m > 0.03: score += 10
            elif ret_1m < -0.05: score -= 15
        
        return max(-100, min(100, score))
    
    def _calc_value(self, info: dict) -> int:
        """Calculate value factor"""
        score = 0
        
        # P/E ratio
        pe = info.get('trailingPE') or info.get('forwardPE')
        if pe:
            if pe < 10: score += 40
            elif pe < 15: score += 25
            elif pe < 20: score += 10
            elif pe > 40: score -= 30
            elif pe > 30: score -= 15
        
        # P/B ratio
        pb = info.get('priceToBook')
        if pb:
            if pb < 1: score += 30
            elif pb < 2: score += 15
            elif pb < 3: score += 5
            elif pb > 10: score -= 25
        
        # P/S ratio
        ps = info.get('priceToSalesTrailing12Months')
        if ps:
            if ps < 1: score += 25
            elif ps < 3: score += 10
            elif ps > 10: score -= 20
        
        # Adjust for sector (tech gets premium)
        sector = info.get('sector', '')
        if 'Tech' in sector:
            score += 10  # Tech deserves higher multiples
        
        return max(-100, min(100, score))
    
    def _calc_quality(self, info: dict) -> int:
        """Calculate quality factor"""
        score = 0
        
        # ROE
        roe = info.get('returnOnEquity')
        if roe:
            if roe > 0.25: score += 35
            elif roe > 0.15: score += 25
            elif roe > 0.10: score += 15
            elif roe < 0: score -= 30
        
        # Profit Margin
        margin = info.get('profitMargins')
        if margin:
            if margin > 0.25: score += 30
            elif margin > 0.15: score += 20
            elif margin > 0.08: score += 10
            elif margin < 0: score -= 25
        
        # Debt/Equity
        debt = info.get('debtToEquity')
        if debt:
            if debt < 30: score += 25
            elif debt < 50: score += 15
            elif debt > 150: score -= 25
            elif debt > 100: score -= 10
        
        # Revenue Growth
        rev_growth = info.get('revenueGrowth')
        if rev_growth:
            if rev_growth > 0.20: score += 20
            elif rev_growth > 0.10: score += 10
            elif rev_growth < 0: score -= 15
        
        return max(-100, min(100, score))
    
    def _calc_size(self, info: dict) -> int:
        """Calculate size factor"""
        mcap = info.get('marketCap', 0) or 0
        
        # Mid-cap sweet spot ($2B - $20B)
        if 2e9 <= mcap <= 20e9:
            return 40  # Optimal size for momentum
        elif 500e6 <= mcap <= 100e9:
            return 20  # Acceptable
        elif mcap < 500e6:
            return -20  # Too small (liquidity risk)
        else:
            return 0  # Large cap (slower growth)
    
    def _calc_volatility(self, df: pd.DataFrame) -> int:
        """Calculate volatility factor (low vol premium)"""
        returns = df['Close'].pct_change().dropna()
        
        if len(returns) < 20:
            return 0
        
        # Annualized volatility
        vol = returns.tail(60).std() * np.sqrt(252)
        
        # Low volatility = higher score
        if vol < 0.20:
            return 40
        elif vol < 0.30:
            return 25
        elif vol < 0.40:
            return 10
        elif vol > 0.60:
            return -30
        elif vol > 0.50:
            return -15
        
        return 0
    
    def _fetch_price_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch price data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _fetch_info(self, symbol: str) -> dict:
        """Fetch info"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except:
            return {}
    
    def _neutral_result(self, symbol: str) -> FactorSignal:
        """Return neutral result"""
        factors = FactorScores(0, 0, 0, 0, 0)
        return FactorSignal(
            symbol=symbol, factors=factors, composite_score=0,
            factor_rank="WEAK", strongest_factors=[], weakest_factors=[],
            pe_ratio=0, pb_ratio=0, profit_margin=0, roe=0, debt_equity=0,
            market_cap=0, signal="HOLD", details=[]
        )


# Global instance
_analyzer = None

def get_factor_analyzer() -> FactorAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = FactorAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing FactorAnalyzer...")
    
    analyzer = FactorAnalyzer()
    
    for symbol in ["AAPL", "NVDA", "TSLA", "META"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Signal: {result.signal} | Rank: {result.factor_rank}")
        print(f"Composite: {result.composite_score:+d}")
        print()
        print("Factor Scores:")
        print(f"  Momentum: {result.factors.momentum_score:+d}")
        print(f"  Value: {result.factors.value_score:+d}")
        print(f"  Quality: {result.factors.quality_score:+d}")
        print(f"  Size: {result.factors.size_score:+d}")
        print(f"  Volatility: {result.factors.volatility_score:+d}")
        print()
        print(f"P/E: {result.pe_ratio:.1f} | P/B: {result.pb_ratio:.1f}")
        print(f"ROE: {result.roe:.1%} | Margin: {result.profit_margin:.1%}")
        print(f"Strongest: {result.strongest_factors}")
