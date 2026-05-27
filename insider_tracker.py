"""
Insider & Institutional Tracker
=================================
Track insider buying/selling and institutional ownership.

Metrics:
1. Insider Buy/Sell Ratio
2. Insider Transaction Size
3. Institutional Ownership %
4. Ownership Change Trend
5. Short Interest Ratio
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class InsiderData:
    """Insider transaction data"""
    name: str
    position: str
    transaction: str  # "Buy", "Sell"
    shares: int
    value: float
    date: datetime


@dataclass
class OwnershipSignal:
    """Ownership analysis result"""
    symbol: str
    
    # Insider activity
    insider_buys_90d: int
    insider_sells_90d: int
    insider_net_value: float  # Net $ bought
    insider_sentiment: str    # "BUYING", "SELLING", "NEUTRAL"
    
    # Institutional
    inst_ownership_pct: float
    inst_change_qtr: float
    
    # Short interest
    short_pct_float: float
    short_ratio: float  # Days to cover
    
    # Scoring
    ownership_score: int  # -100 to +100
    signal: str
    details: List[str]


class InsiderInstitutionalTracker:
    """
    Insider & Institutional Ownership Analysis
    
    Insider Signals:
    - Cluster buying = Very bullish
    - CEO/CFO buying = Strong conviction
    - Selling for diversification = Normal
    - Panic selling = Warning
    
    Institutional:
    - Rising ownership = Accumulation
    - Falling ownership = Distribution
    - Very high ownership = Less upside
    
    Scoring:
    - Net insider buying: +35
    - Multiple insiders buying: +25
    - Net insider selling: -20
    - Inst ownership rising: +20
    - High short interest: +15 (squeeze potential)
    """
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
    
    def analyze(self, symbol: str) -> OwnershipSignal:
        """Analyze ownership"""
        details = []
        score = 0
        
        # Fetch data
        info = self._fetch_info(symbol)
        insiders = self._fetch_insider_transactions(symbol)
        
        # Insider analysis
        insider_buys = 0
        insider_sells = 0
        insider_net = 0
        
        for txn in insiders:
            if txn.transaction.lower() == 'buy':
                insider_buys += 1
                insider_net += txn.value
            elif 'sell' in txn.transaction.lower():
                insider_sells += 1
                insider_net -= txn.value
        
        # Insider scoring
        if insider_net > 1_000_000:
            insider_sentiment = "BUYING"
            score += 35
            details.append(f"INSIDER_NET_BUY:${insider_net/1e6:.1f}M")
        elif insider_net > 100_000:
            insider_sentiment = "BUYING"
            score += 20
        elif insider_net < -5_000_000:
            insider_sentiment = "SELLING"
            score -= 15  # Less negative - selling can be for many reasons
        elif insider_net < -1_000_000:
            insider_sentiment = "SELLING"
            score -= 10
        else:
            insider_sentiment = "NEUTRAL"
        
        # Multiple insiders buying = cluster
        if insider_buys >= 3:
            score += 25
            details.append(f"CLUSTER_BUYING:{insider_buys}_insiders")
        
        # Institutional ownership
        inst_pct = info.get('heldPercentInstitutions', 0) or 0
        inst_pct = inst_pct * 100 if inst_pct < 1 else inst_pct
        
        # Estimate quarterly change (not directly available)
        inst_change = 0  # Would need historical data
        
        if inst_pct > 90:
            details.append("HIGH_INST_OWNERSHIP")
        elif inst_pct > 70:
            score += 10
        elif inst_pct < 30:
            score -= 10
        
        # Short interest
        short_pct = info.get('shortPercentOfFloat', 0) or 0
        short_pct = short_pct * 100 if short_pct < 1 else short_pct
        short_ratio = info.get('shortRatio', 0) or 0
        
        if short_pct > 20:
            score += 15  # Squeeze potential
            details.append(f"HIGH_SHORT_INT:{short_pct:.1f}%")
        elif short_pct > 10:
            score += 5
        
        if short_ratio > 5:
            score += 10
            details.append(f"HIGH_DTC:{short_ratio:.1f}")
        
        # Signal
        if score >= 40:
            signal = "STRONG_ACCUMULATION"
        elif score >= 15:
            signal = "ACCUMULATION"
        elif score <= -30:
            signal = "DISTRIBUTION"
        elif score <= -10:
            signal = "SLIGHT_DISTRIBUTION"
        else:
            signal = "NEUTRAL"
        
        return OwnershipSignal(
            symbol=symbol,
            insider_buys_90d=insider_buys,
            insider_sells_90d=insider_sells,
            insider_net_value=insider_net,
            insider_sentiment=insider_sentiment,
            inst_ownership_pct=inst_pct,
            inst_change_qtr=inst_change,
            short_pct_float=short_pct,
            short_ratio=short_ratio,
            ownership_score=max(-100, min(100, score)),
            signal=signal,
            details=details
        )
    
    def _fetch_info(self, symbol: str) -> dict:
        """Fetch info"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info or {}
        except:
            return {}
    
    def _fetch_insider_transactions(self, symbol: str) -> List[InsiderData]:
        """Fetch insider transactions"""
        try:
            ticker = yf.Ticker(symbol)
            insiders = ticker.insider_transactions
            
            if insiders is None or insiders.empty:
                return []
            
            result = []
            cutoff = datetime.now() - timedelta(days=90)
            
            for _, row in insiders.iterrows():
                try:
                    start_date = row.get('Start Date')
                    if start_date:
                        if isinstance(start_date, str):
                            start_date = pd.to_datetime(start_date)
                        if start_date < cutoff:
                            continue
                    
                    result.append(InsiderData(
                        name=row.get('Insider', 'Unknown'),
                        position=row.get('Position', ''),
                        transaction=row.get('Transaction', ''),
                        shares=int(row.get('Shares', 0) or 0),
                        value=float(row.get('Value', 0) or 0),
                        date=start_date
                    ))
                except:
                    pass
            
            return result[:20]  # Last 20 transactions
        except:
            return []


# Global instance
_tracker = None

def get_insider_tracker() -> InsiderInstitutionalTracker:
    global _tracker
    if _tracker is None:
        _tracker = InsiderInstitutionalTracker()
    return _tracker


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing InsiderInstitutionalTracker...")
    
    tracker = InsiderInstitutionalTracker()
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = tracker.analyze(symbol)
        
        print(f"Signal: {result.signal} ({result.ownership_score:+d})")
        print(f"Insider: {result.insider_sentiment}")
        print(f"  Buys: {result.insider_buys_90d} | Sells: {result.insider_sells_90d}")
        print(f"  Net Value: ${result.insider_net_value:,.0f}")
        print(f"Institutional: {result.inst_ownership_pct:.1f}%")
        print(f"Short: {result.short_pct_float:.1f}% (DTC: {result.short_ratio:.1f})")
        print(f"Details: {result.details}")
