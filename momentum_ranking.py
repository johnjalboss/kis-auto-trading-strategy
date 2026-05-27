"""
Cross-Sectional Momentum Ranking
==================================
Rank stocks by momentum for relative strength trading.

Strategies:
1. Buy top 10% momentum
2. Avoid bottom 10%
3. Momentum factor exposure
4. Sector-relative momentum
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import kis_data as yf  # KIS API drop-in replacement
from loguru import logger


@dataclass
class MomentumStock:
    """Individual stock momentum data"""
    symbol: str
    return_1m: float
    return_3m: float
    return_6m: float
    return_12m: float
    momentum_score: float
    percentile: float  # 0-100
    tier: str  # "TOP", "MID", "BOTTOM"


@dataclass
class MomentumRankingSignal:
    """Momentum ranking analysis"""
    # Rankings
    top_momentum: List[MomentumStock]
    bottom_momentum: List[MomentumStock]
    
    # Universe stats
    universe_size: int
    avg_1m_return: float
    avg_3m_return: float
    
    # Target stock analysis
    target_symbol: str
    target_momentum: Optional[MomentumStock]
    is_top_decile: bool
    is_bottom_decile: bool
    
    # Strategy
    momentum_strategy: str
    expected_alpha: float
    
    ranking_score: int  # -100 to +100
    details: List[str]


class MomentumRanker:
    """
    Cross-Sectional Momentum Analysis
    
    Momentum Effect:
    - Top decile outperforms by 1-2% monthly
    - Bottom decile underperforms
    - 12-1 momentum (skip recent month) works best
    
    Calculation:
    - 6-month return (primary)
    - Skip most recent month (reversal effect)
    - Sector-adjust for purity
    
    Scoring:
    - Top 10%: +50
    - Top 25%: +30
    - Bottom 25%: -30
    - Bottom 10%: -50
    """
    
    # Universe of stocks to rank
    UNIVERSE = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD",
        "JPM", "BAC", "GS", "MS", "V", "MA",
        "XOM", "CVX", "COP",
        "JNJ", "UNH", "PFE", "MRK",
        "HD", "LOW", "TGT", "WMT",
        "KO", "PEP", "PG", "CL",
        "DIS", "NFLX", "CMCSA",
        "BA", "CAT", "GE", "HON",
    ]
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self, target_symbol: str = None) -> MomentumRankingSignal:
        """Rank all stocks by momentum"""
        details = []
        score = 0
        
        # Calculate momentum for universe
        rankings = []
        
        for symbol in self.UNIVERSE:
            df = self._fetch_data(symbol)
            if df is None or len(df) < 126:  # Need 6 months
                continue
            
            close = df['Close']
            
            # Calculate returns (use float() to avoid DataFrame ambiguity)
            ret_1m = (float(close.iloc[-1]) / float(close.iloc[-21]) - 1) * 100 if len(close) >= 21 else 0
            ret_3m = (float(close.iloc[-1]) / float(close.iloc[-63]) - 1) * 100 if len(close) >= 63 else 0
            ret_6m = (float(close.iloc[-1]) / float(close.iloc[-126]) - 1) * 100 if len(close) >= 126 else 0
            ret_12m = (float(close.iloc[-1]) / float(close.iloc[-252]) - 1) * 100 if len(close) >= 252 else ret_6m
            
            # Momentum score (skip recent month for reversal)
            # 12-1 momentum
            try:
                if len(close) >= 252:
                    p1 = float(close.iloc[-21])
                    p2 = float(close.iloc[-252])
                    momentum = (p1 / p2 - 1) * 100 if p2 > 0 else 0
                else:
                    momentum = float(ret_6m)
            except Exception:
                momentum = 0
            
            rankings.append({
                'symbol': symbol,
                'ret_1m': float(ret_1m),
                'ret_3m': float(ret_3m),
                'ret_6m': float(ret_6m),
                'ret_12m': float(ret_12m),
                'momentum': float(momentum)
            })
        
        if not rankings:
            return self._neutral_result(target_symbol)
        
        # Sort by momentum
        rankings = sorted(rankings, key=lambda x: x['momentum'], reverse=True)
        
        # Calculate percentiles
        n = len(rankings)
        for i, r in enumerate(rankings):
            percentile = (1 - i / n) * 100
            
            if percentile >= 90:
                tier = "TOP"
            elif percentile >= 75:
                tier = "UPPER_MID"
            elif percentile >= 25:
                tier = "MID"
            elif percentile >= 10:
                tier = "LOWER_MID"
            else:
                tier = "BOTTOM"
            
            r['percentile'] = percentile
            r['tier'] = tier
        
        # Convert to MomentumStock objects
        momentum_stocks = [
            MomentumStock(
                symbol=r['symbol'],
                return_1m=r['ret_1m'],
                return_3m=r['ret_3m'],
                return_6m=r['ret_6m'],
                return_12m=r['ret_12m'],
                momentum_score=r['momentum'],
                percentile=r['percentile'],
                tier=r['tier']
            )
            for r in rankings
        ]
        
        top_5 = momentum_stocks[:5]
        bottom_5 = momentum_stocks[-5:]
        
        # Universe stats
        avg_1m = np.mean([r['ret_1m'] for r in rankings])
        avg_3m = np.mean([r['ret_3m'] for r in rankings])
        
        # Target stock analysis
        target = None
        is_top = False
        is_bottom = False
        
        if target_symbol is not None:
            target_data = next((r for r in rankings if r['symbol'] == target_symbol), None)
            if target_data:
                target = MomentumStock(
                    symbol=target_symbol,
                    return_1m=target_data['ret_1m'],
                    return_3m=target_data['ret_3m'],
                    return_6m=target_data['ret_6m'],
                    return_12m=target_data['ret_12m'],
                    momentum_score=target_data['momentum'],
                    percentile=target_data['percentile'],
                    tier=target_data['tier']
                )
                
                is_top = target.percentile >= 90
                is_bottom = target.percentile <= 10
                
                if is_top:
                    score = 50
                    strategy = "STRONG_BUY_MOMENTUM"
                    details.append("TOP_DECILE_MOMENTUM")
                elif target.percentile >= 75:
                    score = 30
                    strategy = "BUY_MOMENTUM"
                    details.append("TOP_QUARTILE")
                elif is_bottom:
                    score = -50
                    strategy = "AVOID_WEAK"
                    details.append("BOTTOM_DECILE")
                elif target.percentile <= 25:
                    score = -30
                    strategy = "CAUTION_WEAK"
                    details.append("BOTTOM_QUARTILE")
                else:
                    score = 0
                    strategy = "NEUTRAL"
                
                details.append(f"RANK:{int(target.percentile)}%")
            else:
                strategy = "NOT_IN_UNIVERSE"
        else:
            strategy = "SCAN_UNIVERSE"
        
        # Expected alpha (based on historical momentum premium)
        expected_alpha = score * 0.02  # Roughly 2% per month for top decile
        
        return MomentumRankingSignal(
            top_momentum=top_5,
            bottom_momentum=bottom_5,
            universe_size=n,
            avg_1m_return=avg_1m,
            avg_3m_return=avg_3m,
            target_symbol=target_symbol or "",
            target_momentum=target,
            is_top_decile=is_top,
            is_bottom_decile=is_bottom,
            momentum_strategy=strategy,
            expected_alpha=expected_alpha,
            ranking_score=max(-100, min(100, score)),
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            self._cache[symbol] = df
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> MomentumRankingSignal:
        """Neutral result"""
        return MomentumRankingSignal(
            top_momentum=[], bottom_momentum=[],
            universe_size=0, avg_1m_return=0, avg_3m_return=0,
            target_symbol=symbol or "", target_momentum=None,
            is_top_decile=False, is_bottom_decile=False,
            momentum_strategy="UNKNOWN", expected_alpha=0,
            ranking_score=0, details=[]
        )


# Global
_ranker = None

def get_momentum_ranker() -> MomentumRanker:
    global _ranker
    if _ranker is None:
        _ranker = MomentumRanker()
    return _ranker


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing MomentumRanker...")
    
    ranker = MomentumRanker()
    result = ranker.analyze("NVDA")
    
    print(f"\n{'='*60}")
    print("MOMENTUM RANKING")
    print('='*60)
    print(f"Universe: {result.universe_size} stocks")
    print(f"Avg 1M: {result.avg_1m_return:.1f}%")
    print(f"Avg 3M: {result.avg_3m_return:.1f}%")
    print()
    print("🚀 Top 5 Momentum:")
    for s in result.top_momentum:
        print(f"  {s.symbol}: {s.momentum_score:+.1f}% ({s.tier})")
    print()
    print("📉 Bottom 5 Momentum:")
    for s in result.bottom_momentum:
        print(f"  {s.symbol}: {s.momentum_score:+.1f}% ({s.tier})")
    print()
    if result.target_momentum:
        t = result.target_momentum
        print(f"Target ({t.symbol}):")
        print(f"  Momentum: {t.momentum_score:+.1f}%")
        print(f"  Percentile: {t.percentile:.0f}%")
        print(f"  Tier: {t.tier}")
    print(f"Strategy: {result.momentum_strategy}")
    print(f"Score: {result.ranking_score:+d}")
    print(f"Details: {result.details}")
