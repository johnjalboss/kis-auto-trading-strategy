"""
Sector Rotation Analyzer
=========================
Track money flow between market sectors.

Sectors:
- XLK: Technology
- XLF: Financials  
- XLE: Energy
- XLV: Healthcare
- XLI: Industrials
- XLP: Consumer Staples
- XLY: Consumer Discretionary
- XLU: Utilities
- XLRE: Real Estate
- XLB: Materials
- XLC: Communications
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class SectorData:
    """Individual sector data"""
    symbol: str
    name: str
    return_1d: float
    return_5d: float
    return_20d: float
    relative_strength: float  # vs SPY
    volume_ratio: float  # vs 20-day avg
    momentum_rank: int


@dataclass
class SectorRotationSignal:
    """Sector rotation analysis result"""
    market_regime: str  # "RISK_ON", "RISK_OFF", "MIXED"
    leading_sectors: List[SectorData]
    lagging_sectors: List[SectorData]
    recommended_sectors: List[str]
    avoid_sectors: List[str]
    rotation_score: int  # -100 to +100
    details: List[str]


# Sector ETF mappings
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLF': 'Financials',
    'XLE': 'Energy',
    'XLV': 'Healthcare',
    'XLI': 'Industrials',
    'XLP': 'Consumer Staples',
    'XLY': 'Consumer Discretionary',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLB': 'Materials',
    'XLC': 'Communications',
}

# Risk-on sectors (outperform in bull markets)
RISK_ON_SECTORS = ['XLK', 'XLY', 'XLF', 'XLI', 'XLC']

# Defensive sectors (outperform in bear markets)
DEFENSIVE_SECTORS = ['XLP', 'XLU', 'XLV', 'XLRE']


class SectorRotationAnalyzer:
    """
    Sector Rotation Analysis
    
    Signals:
    1. Risk-On: Tech, Consumer Disc, Financials leading
    2. Risk-Off: Utilities, Staples, Healthcare leading
    3. Rotation: Money moving between sectors
    
    Strategy:
    - Go long sectors with positive momentum + relative strength
    - Avoid sectors with negative momentum + weak relative strength
    """
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_time: Optional[datetime] = None
    
    def analyze(self) -> SectorRotationSignal:
        """Analyze sector rotation"""
        # Fetch all sector data
        sector_data = self._fetch_sector_data()
        
        if not sector_data:
            return self._default_signal()
        
        # Calculate rankings
        sorted_by_momentum = sorted(sector_data, 
                                    key=lambda x: x.return_20d, reverse=True)
        
        for i, s in enumerate(sorted_by_momentum):
            s.momentum_rank = i + 1
        
        # Identify leading/lagging sectors
        leading = sorted_by_momentum[:3]
        lagging = sorted_by_momentum[-3:]
        
        # Determine market regime
        risk_on_strength = sum(1 for s in leading if s.symbol in RISK_ON_SECTORS)
        defensive_strength = sum(1 for s in leading if s.symbol in DEFENSIVE_SECTORS)
        
        if risk_on_strength >= 2:
            regime = "RISK_ON"
            rotation_score = 50 + (risk_on_strength - defensive_strength) * 15
        elif defensive_strength >= 2:
            regime = "RISK_OFF"
            rotation_score = -50 - (defensive_strength - risk_on_strength) * 15
        else:
            regime = "MIXED"
            rotation_score = (risk_on_strength - defensive_strength) * 20
        
        # Generate recommendations
        recommended = [s.symbol for s in leading if s.relative_strength > 1 and s.return_5d > 0]
        avoid = [s.symbol for s in lagging if s.relative_strength < 0.98 and s.return_5d < 0]
        
        # Build details
        details = [
            f"Regime: {regime}",
            f"Leaders: {[s.symbol for s in leading]}",
            f"Laggards: {[s.symbol for s in lagging]}",
        ]
        
        if regime == "RISK_ON":
            details.append("🟢 Favor growth/cyclical sectors")
        elif regime == "RISK_OFF":
            details.append("🔴 Favor defensive sectors")
        
        return SectorRotationSignal(
            market_regime=regime,
            leading_sectors=leading,
            lagging_sectors=lagging,
            recommended_sectors=recommended,
            avoid_sectors=avoid,
            rotation_score=max(-100, min(100, rotation_score)),
            details=details
        )
    
    def get_sector_for_stock(self, symbol: str) -> Optional[str]:
        """Get sector for a stock (basic mapping)"""
        # This is simplified - in production, use yfinance sector info
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('sector', None)
        except:
            return None
    
    def is_sector_favorable(self, sector: str) -> Tuple[bool, str]:
        """Check if sector is currently favorable"""
        signal = self.analyze()
        
        # Map sector name to ETF
        sector_to_etf = {
            'Technology': 'XLK',
            'Financial Services': 'XLF',
            'Energy': 'XLE',
            'Healthcare': 'XLV',
            'Industrials': 'XLI',
            'Consumer Defensive': 'XLP',
            'Consumer Cyclical': 'XLY',
            'Utilities': 'XLU',
            'Real Estate': 'XLRE',
            'Basic Materials': 'XLB',
            'Communication Services': 'XLC',
        }
        
        etf = sector_to_etf.get(sector)
        
        if etf in signal.recommended_sectors:
            return True, f"FAVORABLE ({signal.market_regime})"
        elif etf in signal.avoid_sectors:
            return False, f"AVOID ({signal.market_regime})"
        else:
            return True, f"NEUTRAL ({signal.market_regime})"
    
    def _fetch_sector_data(self) -> List[SectorData]:
        """Fetch data for all sectors"""
        # Check cache
        if self._cache_time and (datetime.now() - self._cache_time).seconds < 3600:
            return self._parse_cached_data()
        
        sectors = []
        
        # Get SPY for relative strength
        try:
            spy = yf.download('SPY', period='30d', progress=False)
            if isinstance(spy.columns, pd.MultiIndex):
                spy.columns = spy.columns.get_level_values(0)
            spy_return_20d = (spy['Close'].iloc[-1] / spy['Close'].iloc[-20] - 1) if len(spy) >= 20 else 0
        except:
            spy_return_20d = 0
        
        for symbol, name in SECTOR_ETFS.items():
            try:
                df = yf.download(symbol, period='30d', progress=False)
                if df.empty or len(df) < 20:
                    continue
                
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                close = df['Close']
                volume = df['Volume']
                
                return_1d = (close.iloc[-1] / close.iloc[-2] - 1) if len(close) >= 2 else 0
                return_5d = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) >= 5 else 0
                return_20d = (close.iloc[-1] / close.iloc[-20] - 1) if len(close) >= 20 else 0
                
                vol_avg = volume.tail(20).mean()
                vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 1
                
                # Relative strength vs SPY
                rel_strength = (1 + return_20d) / (1 + spy_return_20d) if spy_return_20d > -1 else 1
                
                sector = SectorData(
                    symbol=symbol,
                    name=name,
                    return_1d=return_1d,
                    return_5d=return_5d,
                    return_20d=return_20d,
                    relative_strength=rel_strength,
                    volume_ratio=vol_ratio,
                    momentum_rank=0
                )
                sectors.append(sector)
                self._cache[symbol] = df
                
            except Exception as e:
                logger.debug("Failed to fetch {}: {}", symbol, e)
        
        self._cache_time = datetime.now()
        return sectors
    
    def _parse_cached_data(self) -> List[SectorData]:
        """Parse cached data"""
        # Re-run analysis on cached data
        return self._fetch_sector_data()
    
    def _default_signal(self) -> SectorRotationSignal:
        """Return default signal"""
        return SectorRotationSignal(
            market_regime="MIXED",
            leading_sectors=[],
            lagging_sectors=[],
            recommended_sectors=[],
            avoid_sectors=[],
            rotation_score=0,
            details=["Unable to analyze sectors"]
        )


# Global instance
_analyzer = None

def get_sector_analyzer() -> SectorRotationAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SectorRotationAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SectorRotationAnalyzer...")
    
    analyzer = SectorRotationAnalyzer()
    signal = analyzer.analyze()
    
    print(f"\n{'='*50}")
    print("SECTOR ROTATION ANALYSIS")
    print('='*50)
    print(f"Market Regime: {signal.market_regime}")
    print(f"Rotation Score: {signal.rotation_score:+d}")
    print()
    print("Leading Sectors:")
    for s in signal.leading_sectors:
        print(f"  {s.symbol} ({s.name}): {s.return_20d:+.1%} | RS: {s.relative_strength:.2f}")
    print()
    print("Lagging Sectors:")
    for s in signal.lagging_sectors:
        print(f"  {s.symbol} ({s.name}): {s.return_20d:+.1%} | RS: {s.relative_strength:.2f}")
    print()
    print(f"Recommended: {signal.recommended_sectors}")
    print(f"Avoid: {signal.avoid_sectors}")
    print(f"Details: {signal.details}")
