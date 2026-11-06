"""
Sector Rotator
================
Automatic sector rotation based on momentum.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import data_proxy
import yfinance as yf
from loguru import logger
import time

_sector_rankings_cache = None
_sector_cache_time = 0
SECTOR_CACHE_EXPIRY = 3600  # 1 hour cache

@dataclass
class SectorRanking:
    sector: str
    etf: str
    momentum_1m: float
    momentum_3m: float
    relative_strength: float
    rank: int
    recommendation: str  # "OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT", "EARLY_ACCELERATION"
    rs_5d_vel: float = 0.0
    rs_accel: float = 0.0


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
        """Analyze and rank all sectors with a 1-hour global memory cache"""
        global _sector_rankings_cache, _sector_cache_time
        now = time.time()
        
        if _sector_rankings_cache is not None and (now - _sector_cache_time < SECTOR_CACHE_EXPIRY):
            return _sector_rankings_cache.copy()
            
        logger.info("SectorRotator: Cache expired or empty. Running dynamic sector rotation analysis...")
        
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
            
            # Relative strength series & acceleration vs SPY (순환매 초기 포착 RSTA 모델)
            rs_5d_vel = 0.0
            rs_accel = 0.0
            if spy_data is not None:
                spy_close = spy_data['Close']
                # Align dates to prevent mismatch errors
                aligned = pd.concat([close, spy_close], axis=1, keys=['Sector', 'SPY']).dropna()
                if len(aligned) >= 21:
                    aligned['RS'] = aligned['Sector'] / aligned['SPY']
                    rs_series = aligned['RS']
                    
                    # 5-day Relative Strength Velocity (%)
                    rs_5d_vel = float((rs_series.iloc[-1] / rs_series.iloc[-6] - 1) * 100) if len(rs_series) >= 6 else 0.0
                    # 20-day Relative Strength Velocity (%)
                    rs_20d_vel = float((rs_series.iloc[-1] / rs_series.iloc[-21] - 1) * 100)
                    
                    # Acceleration: short-term velocity minus normalized long-term velocity
                    rs_accel = float(rs_5d_vel - (rs_20d_vel / 4.0))
                
                # Standard relative strength multiplier
                rs = float((close.iloc[-1] / close.iloc[-21]) / (spy_close.iloc[-1] / spy_close.iloc[-21]))
            else:
                rs = 1.0
            
            rankings.append(SectorRanking(
                sector=name,
                etf=etf,
                momentum_1m=mom_1m,
                momentum_3m=mom_3m,
                relative_strength=rs,
                rank=0,
                recommendation="",
                rs_5d_vel=rs_5d_vel,
                rs_accel=rs_accel
            ))
        
        # Sort by Triple-Timeframe Dynamic Momentum:
        # - 45% 1-Month Swing Momentum (Core Trend)
        # - 30% 3-Month Medium-Term Foundation (Trend Sustainability)
        # - 25% 5-Day Real-Time Relative Strength Acceleration (Captures rapid sector shifts immediately!)
        rankings.sort(key=lambda x: (x.momentum_1m * 0.45) + (x.momentum_3m * 0.30) + (x.rs_5d_vel * 0.25), reverse=True)
        
        # Assign ranks and recommendations
        for i, r in enumerate(rankings):
            r.rank = i + 1
            if i < 3:
                r.recommendation = "OVERWEIGHT"
            elif i >= len(rankings) - 3:
                r.recommendation = "UNDERWEIGHT"
            else:
                # 중간 순위 중 상대강도 가속도가 발생하고 단기 상승 중인 종목 -> 순환매 초입 지정
                if r.rs_5d_vel > 0.3 and r.rs_accel > 1.0:
                    r.recommendation = "EARLY_ACCELERATION"
                    logger.info("🔥 [EARLY_ROTATION_DETECTED] Sector {} ({}) is accelerating! V_5d: {:.2f}%, Accel: {:.2f}",
                                r.sector, r.etf, r.rs_5d_vel, r.rs_accel)
                else:
                    r.recommendation = "NEUTRAL"
        
        _sector_rankings_cache = rankings.copy()
        _sector_cache_time = now
        return rankings
    
    def get_top_sectors(self, n: int = 3) -> List[str]:
        """Get top N sector ETFs"""
        rankings = self.analyze()
        return [r.etf for r in rankings[:n]]
    
    _DB_SECTOR_CACHE = None

    @classmethod
    def _init_db_sector_map(cls) -> Dict[str, str]:
        """Loads and normalizes sector classifications for 3,000+ US stocks from local SQLite metadata."""
        import sqlite3
        import os
        
        SECTOR_KEYWORDS = {
            'technology': 'XLK', 'tech': 'XLK', 'software': 'XLK', 'semiconductor': 'XLK',
            'healthcare': 'XLV', 'health care': 'XLV', 'biotechnology': 'XLV', 'pharmaceutical': 'XLV',
            'financial': 'XLF', 'finance': 'XLF', 'bank': 'XLF', 'insurance': 'XLF',
            'communication': 'XLC', 'telecom': 'XLC', 'media': 'XLC',
            'consumer discretionary': 'XLY', 'consumer cyclical': 'XLY', 'retail': 'XLY',
            'consumer staples': 'XLP', 'consumer defensive': 'XLP', 'beverage': 'XLP', 'food': 'XLP',
            'energy': 'XLE', 'oil': 'XLE', 'gas': 'XLE',
            'industrials': 'XLI', 'aerospace': 'XLI', 'transportation': 'XLI',
            'utilities': 'XLU', 'power': 'XLU', 'electric': 'XLU',
            'real estate': 'XLRE', 'reit': 'XLRE',
            'materials': 'XLB', 'basic materials': 'XLB', 'chemicals': 'XLB', 'mining': 'XLB'
        }

        db_paths = [
            "/home/ubuntu/us-theme-tracker/us_stocks_data.db",
            "/home/ubuntu/kis-auto-trading/us_stocks_data.db",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "us-theme-tracker", "us_stocks_data.db"),
            r"C:\Users\wngud\.gemini\antigravity\scratch\us-theme-tracker\us_stocks_data.db"
        ]

        mapping = {}
        for dbp in db_paths:
            if os.path.exists(dbp):
                try:
                    conn = sqlite3.connect(dbp)
                    cur = conn.cursor()
                    cur.execute("SELECT ticker, sector, industry FROM stock_metadata WHERE ticker IS NOT NULL;")
                    rows = cur.fetchall()
                    conn.close()
                    for sym, sec, ind in rows:
                        sym_clean = sym.strip().upper()
                        raw = f"{sec or ''} {ind or ''}".strip().lower()
                        for k, v in SECTOR_KEYWORDS.items():
                            if k in raw:
                                mapping[sym_clean] = v
                                break
                    if len(mapping) >= 500:
                        break
                except Exception:
                    pass

        # High-priority manual overrides & key leaders
        OVERRIDES = {
            'AAPL':'XLK','MSFT':'XLK','NVDA':'XLK','AMD':'XLK','AVGO':'XLK',
            'CRM':'XLK','ORCL':'XLK','ADBE':'XLK','QCOM':'XLK','ARM':'XLK',
            'MU':'XLK','LRCX':'XLK','KLAC':'XLK','ON':'XLK','ASML':'XLK',
            'SNOW':'XLK','DDOG':'XLK','PANW':'XLK','CRWD':'XLK','ZS':'XLK',
            'NET':'XLK','MDB':'XLK','PLTR':'XLK','CDNS':'XLK','IDT':'XLC',
            'META':'XLC','NFLX':'XLC','GOOGL':'XLC','GOOG':'XLC','DIS':'XLC',
            'AMZN':'XLY','TSLA':'XLY','NKE':'XLY','SBUX':'XLY','MCD':'XLY',
            'ABNB':'XLY','UBER':'XLY','LULU':'XLY','SHOP':'XLY',
            'JPM':'XLF','GS':'XLF','V':'XLF','MA':'XLF','PYPL':'XLF',
            'HOOD':'XLF','COIN':'XLF','SOFI':'XLF','AFRM':'XLF','UPST':'XLF',
            'LLY':'XLV','UNH':'XLV','JNJ':'XLV','ABBV':'XLV','BIIB':'XLV',
            'MRK':'XLV','PFE':'XLV','GILD':'XLV','AMGN':'XLV','VRTX':'XLV',
            'REGN':'XLV','ISRG':'XLV','COR':'XLV','THC':'XLV','MRNA':'XLV',
            'XOM':'XLE','CVX':'XLE','COP':'XLE','SLB':'XLE','EOG':'XLE','OXY':'XLE',
            'CAT':'XLI','DE':'XLI','BA':'XLI','GE':'XLI','HON':'XLI','RTX':'XLI',
            'NEE':'XLU','DUK':'XLU','SO':'XLU','VST':'XLU','CEG':'XLU',
            'PG':'XLP','KO':'XLP','PEP':'XLP','WMT':'XLP','COST':'XLP','CELH':'XLP',
            'PLD':'XLRE','AMT':'XLRE','EQIX':'XLRE','O':'XLRE',
            'LIN':'XLB','SHW':'XLB','APD':'XLB','FCX':'XLB'
        }
        mapping.update(OVERRIDES)
        return mapping

    def get_sector_for_stock(self, symbol: str) -> Optional[str]:
        """Get sector ETF for a stock — instant in-memory lookup across 3,000+ US stocks"""
        if SectorRotator._DB_SECTOR_CACHE is None:
            SectorRotator._DB_SECTOR_CACHE = SectorRotator._init_db_sector_map()
        return SectorRotator._DB_SECTOR_CACHE.get(symbol.strip().upper(), None)
    
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
