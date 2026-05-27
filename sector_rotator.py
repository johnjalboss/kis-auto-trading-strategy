"""
Sector Rotator
================
Automatic sector rotation based on momentum.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class SectorRanking:
    sector: str
    etf: str
    momentum_1m: float
    momentum_3m: float
    relative_strength: float
    rank: int
    recommendation: str  # "OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT"


class SectorRotator:
    """
    Sector Rotation Strategy
    
    Sectors (SPDRs):
    - XLK: Technology
    - XLV: Healthcare
    - XLF: Financials
    - XLY: Consumer Discretionary
    - XLP: Consumer Staples
    - XLE: Energy
    - XLI: Industrials
    - XLB: Materials
    - XLU: Utilities
    - XLRE: Real Estate
    - XLC: Communication
    
    Strategy:
    - Overweight top 3 sectors
    - Underweight bottom 3 sectors
    """
    
    SECTORS = {
        'XLK': 'Technology',
        'XLV': 'Healthcare',
        'XLF': 'Financials',
        'XLY': 'Consumer Disc',
        'XLP': 'Consumer Staples',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLB': 'Materials',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLC': 'Communication'
    }
    
    def __init__(self):
        pass
    
    def analyze(self) -> List[SectorRanking]:
        """Analyze and rank all sectors"""
        
        rankings = []
        spy_data = self._fetch_data("SPY")
        
        for etf, name in self.SECTORS.items():
            data = self._fetch_data(etf)
            
            if data is None or len(data) < 63:
                continue
            
            close = data['Close']
            
            # Momentum
            mom_1m = (close.iloc[-1] / close.iloc[-21] - 1) * 100
            mom_3m = (close.iloc[-1] / close.iloc[-63] - 1) * 100
            
            # Relative strength vs SPY
            if spy_data is not None:
                spy_close = spy_data['Close']
                rs = (close.iloc[-1] / close.iloc[-21]) / (spy_close.iloc[-1] / spy_close.iloc[-21])
            else:
                rs = 1.0
            
            rankings.append(SectorRanking(
                sector=name,
                etf=etf,
                momentum_1m=mom_1m,
                momentum_3m=mom_3m,
                relative_strength=rs,
                rank=0,
                recommendation=""
            ))
        
        # Sort by combined score
        rankings.sort(key=lambda x: x.momentum_1m * 0.6 + x.momentum_3m * 0.4, reverse=True)
        
        # Assign ranks and recommendations
        for i, r in enumerate(rankings):
            r.rank = i + 1
            if i < 3:
                r.recommendation = "OVERWEIGHT"
            elif i >= len(rankings) - 3:
                r.recommendation = "UNDERWEIGHT"
            else:
                r.recommendation = "NEUTRAL"
        
        return rankings
    
    def get_top_sectors(self, n: int = 3) -> List[str]:
        """Get top N sector ETFs"""
        rankings = self.analyze()
        return [r.etf for r in rankings[:n]]
    
    def get_sector_for_stock(self, symbol: str) -> Optional[str]:
        """Get sector ETF for a stock — hardcoded map (KIS 환경 yfinance.info 미지원 대응)"""
        # 1차: 하드코딩 맵 (KIS 환경에서 yfinance.info 실패하므로 우선 사용)
        SYMBOL_SECTOR_MAP = {
            # Technology (XLK)
            'AAPL':'XLK','MSFT':'XLK','NVDA':'XLK','AMD':'XLK','AVGO':'XLK',
            'CRM':'XLK','ORCL':'XLK','ADBE':'XLK','QCOM':'XLK','ARM':'XLK',
            'MU':'XLK','LRCX':'XLK','KLAC':'XLK','ON':'XLK','ASML':'XLK',
            'DELL':'XLK','HPE':'XLK','SNOW':'XLK','DDOG':'XLK','PANW':'XLK',
            'CRWD':'XLK','ZS':'XLK','NET':'XLK','MDB':'XLK','PLTR':'XLK',
            'IONQ':'XLK','RGTI':'XLK','AI':'XLK','VRT':'XLK',
            # Communication (XLC)
            'META':'XLC','NFLX':'XLC','GOOGL':'XLC','DIS':'XLC',
            # Consumer Discretionary (XLY)
            'AMZN':'XLY','TSLA':'XLY','NKE':'XLY','SBUX':'XLY','MCD':'XLY',
            'ABNB':'XLY','UBER':'XLY','LULU':'XLY','SHOP':'XLY',
            # Financials (XLF)
            'JPM':'XLF','GS':'XLF','V':'XLF','MA':'XLF','PYPL':'XLF',
            'AFRM':'XLF','UPST':'XLF','SOFI':'XLF','HOOD':'XLF','COIN':'XLF',
            'NU':'XLF','MSTR':'XLF',
            # Healthcare (XLV)
            'MRNA':'XLV','GILD':'XLV','AMGN':'XLV','VRTX':'XLV',
            'ISRG':'XLV','DXCM':'XLV','PODD':'XLV',
            # Energy (XLE)
            'XOM':'XLE','CVX':'XLE','FANG':'XLE','BKR':'XLE','VST':'XLE',
            # Industrials (XLI)
            'GE':'XLI','CAT':'XLI','BA':'XLI','RKLB':'XLI',
            # Utilities (XLU)
            'FSLR':'XLU','ENPH':'XLU',
            # Consumer Staples (XLP)
            'PG':'XLP','KO':'XLP','PEP':'XLP','WMT':'XLP','COST':'XLP',
            # Real Estate (XLRE)
            'AMT':'XLRE','PLD':'XLRE','EQIX':'XLRE','VTR':'XLRE',
            # Materials (XLB)
            'CELH':'XLB',
        }
        if symbol in SYMBOL_SECTOR_MAP:
            return SYMBOL_SECTOR_MAP[symbol]
        
        # 2차: yfinance fallback (KIS 샘이 아닌 실제 yfinance일 때만 작동)
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            sector = info.get('sector', '') if isinstance(info, dict) else ''
            sector_map = {
                'Technology': 'XLK', 'Healthcare': 'XLV', 'Financial Services': 'XLF',
                'Financial': 'XLF', 'Consumer Cyclical': 'XLY', 'Consumer Defensive': 'XLP',
                'Energy': 'XLE', 'Industrials': 'XLI', 'Basic Materials': 'XLB',
                'Utilities': 'XLU', 'Real Estate': 'XLRE', 'Communication Services': 'XLC',
                'Communication': 'XLC'
            }
            return sector_map.get(sector)
        except:
            return None
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period='6mo', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None


def get_sector_rotator() -> SectorRotator:
    return SectorRotator()


if __name__ == "__main__":
    print("Testing SectorRotator...")
    sr = SectorRotator()
    
    rankings = sr.analyze()
    
    print(f"\n{'='*60}")
    print("SECTOR RANKINGS")
    print('='*60)
    
    for r in rankings:
        print(f"#{r.rank} {r.etf} ({r.sector})")
        print(f"   1M: {r.momentum_1m:+.1f}% | 3M: {r.momentum_3m:+.1f}% | RS: {r.relative_strength:.2f}")
        print(f"   → {r.recommendation}")
    
    print(f"\nTop 3: {sr.get_top_sectors(3)}")


def analyze_sectors():
    return SectorRotator().analyze()
