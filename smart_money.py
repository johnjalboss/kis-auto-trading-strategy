"""
Smart Money Tracking Module
============================
Track institutional activity through dark pool prints,
block trades, and 13F filings.

Data Sources (Free):
- Finviz (Insider/Institutional ownership)
- Yahoo Finance (Major holders)
- SEC EDGAR (13F filings - cached)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import requests
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class DarkPoolSignal:
    """Dark pool activity signal"""
    symbol: str
    signal_type: str  # "ACCUMULATION", "DISTRIBUTION", "NEUTRAL"
    volume_ratio: float  # Dark pool vs exchange volume
    block_trades: int
    avg_block_size: float
    confidence: int  # 0-100


@dataclass
class InstitutionalActivity:
    """Institutional ownership changes"""
    symbol: str
    inst_ownership_pct: float
    inst_change_qoq: float  # Quarter over quarter change
    insider_ownership_pct: float
    insider_buys_90d: int
    insider_sells_90d: int
    net_insider_sentiment: str  # "BULLISH", "BEARISH", "NEUTRAL"
    major_holders: List[str]


@dataclass  
class SmartMoneySignal:
    """Combined smart money signal"""
    symbol: str
    score: int  # -100 to +100
    dark_pool: Optional[DarkPoolSignal]
    institutional: Optional[InstitutionalActivity]
    signals: List[str]


class SmartMoneyTracker:
    """
    Track Smart Money Activity
    
    Scoring System:
    - Institutional buying: +30
    - Insider buying: +25
    - Dark pool accumulation: +25
    - High block trade activity: +20
    
    Negative signals:
    - Institutional selling: -30
    - Insider selling: -25
    - Dark pool distribution: -25
    """
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # symbol -> (data, timestamp)
        self._cache_ttl = 3600  # 1 hour cache
    
    def analyze(self, symbol: str) -> SmartMoneySignal:
        """Analyze smart money activity for a symbol"""
        signals = []
        score = 0
        
        # Get institutional data
        inst_data = self._get_institutional_data(symbol)
        
        # Get dark pool proxy (volume analysis)
        dark_pool = self._analyze_dark_pool_proxy(symbol)
        
        if inst_data:
            # Institutional ownership scoring
            if inst_data.inst_change_qoq > 0.05:
                score += 30
                signals.append(f"INST_BUYING:+{inst_data.inst_change_qoq:.1%}")
            elif inst_data.inst_change_qoq < -0.05:
                score -= 30
                signals.append(f"INST_SELLING:{inst_data.inst_change_qoq:.1%}")
            
            # Insider activity scoring
            if inst_data.net_insider_sentiment == "BULLISH":
                score += 25
                signals.append("INSIDER_BULLISH")
            elif inst_data.net_insider_sentiment == "BEARISH":
                score -= 25
                signals.append("INSIDER_BEARISH")
            
            # Healthy institutional ownership (30-70%)
            if 0.30 <= inst_data.inst_ownership_pct <= 0.70:
                score += 10
        
        if dark_pool:
            if dark_pool.signal_type == "ACCUMULATION":
                score += 25
                signals.append(f"DARKPOOL_ACCUM:{dark_pool.volume_ratio:.1f}x")
            elif dark_pool.signal_type == "DISTRIBUTION":
                score -= 25
                signals.append("DARKPOOL_DIST")
            
            # Block trade activity
            if dark_pool.block_trades > 5:
                score += 15
                signals.append(f"BLOCK_TRADES:{dark_pool.block_trades}")
        
        return SmartMoneySignal(
            symbol=symbol,
            score=max(-100, min(100, score)),
            dark_pool=dark_pool,
            institutional=inst_data,
            signals=signals
        )
    
    def _get_institutional_data(self, symbol: str) -> Optional[InstitutionalActivity]:
        """Get institutional ownership proxy data via KIS API
        
        KIS API doesn't provide institutional ownership directly,
        so we use volume patterns and price stability as proxies.
        """
        try:
            import kis_data
            df = kis_data.download(symbol, period="90d", progress=False)
            
            if df is None or df.empty or len(df) < 30:
                return None
            
            # Proxy: large cap stocks with stable price = high institutional ownership
            avg_volume = float(df['Volume'].mean())
            recent_volume = float(df['Volume'].tail(5).mean())
            price_volatility = float(df['Close'].pct_change().std())
            
            # Price momentum over 3 months as proxy for inst sentiment
            price_change_3mo = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[0])) / float(df['Close'].iloc[0])
            
            # Estimate institutional ownership from price stability
            # Low volatility = more institutional ownership (proxy)
            if price_volatility < 0.015:
                est_inst_pct = 0.70
            elif price_volatility < 0.025:
                est_inst_pct = 0.50
            elif price_volatility < 0.04:
                est_inst_pct = 0.30
            else:
                est_inst_pct = 0.15
            
            # Estimate inst buying/selling from volume+price correlation
            inst_change = price_change_3mo * 0.3  # Dampened correlation
            
            # Volume surge with price up = insider/inst buying
            vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            recent_return = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[-5])) / float(df['Close'].iloc[-5])
            
            if vol_ratio > 1.5 and recent_return > 0.02:
                sentiment = "BULLISH"
                buys, sells = 5, 1
            elif vol_ratio > 1.5 and recent_return < -0.02:
                sentiment = "BEARISH"
                buys, sells = 1, 5
            else:
                sentiment = "NEUTRAL"
                buys, sells = 2, 2
            
            return InstitutionalActivity(
                symbol=symbol,
                inst_ownership_pct=est_inst_pct,
                inst_change_qoq=inst_change,
                insider_ownership_pct=0.05,  # Default estimate
                insider_buys_90d=buys,
                insider_sells_90d=sells,
                net_insider_sentiment=sentiment,
                major_holders=[]
            )
            
        except Exception as e:
            logger.debug("Institutional data fetch failed for {}: {}", symbol, e)
            return None
    
    def _analyze_dark_pool_proxy(self, symbol: str) -> Optional[DarkPoolSignal]:
        """
        Analyze dark pool activity proxy via KIS API
        
        Uses volume patterns from daily OHLCV as proxy for
        off-exchange activity and block trades.
        """
        try:
            import kis_data
            df = kis_data.download(symbol, period="30d", progress=False)
            
            if df is None or df.empty or len(df) < 10:
                return None
            
            # Analyze volume patterns
            avg_volume = float(df['Volume'].mean())
            recent_volume = float(df['Volume'].tail(5).mean())
            
            # Volume anomaly detection
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Estimate block trades (volume spikes)
            volume_std = float(df['Volume'].std())
            spikes = df[df['Volume'] > avg_volume + 2 * volume_std]
            block_count = len(spikes)
            
            # Calculate average spike size
            avg_block = float(spikes['Volume'].mean()) / avg_volume if block_count > 0 else 0
            
            # Determine signal type based on price action during high volume
            if block_count > 0:
                high_vol_days = df[df['Volume'] > avg_volume * 1.5]
                up_days = len(high_vol_days[high_vol_days['Close'] > high_vol_days['Open']])
                down_days = len(high_vol_days) - up_days
                
                if up_days > down_days * 1.5:
                    signal_type = "ACCUMULATION"
                elif down_days > up_days * 1.5:
                    signal_type = "DISTRIBUTION"
                else:
                    signal_type = "NEUTRAL"
            else:
                signal_type = "NEUTRAL"
            
            confidence = min(100, int(volume_ratio * 30 + block_count * 10))
            
            return DarkPoolSignal(
                symbol=symbol,
                signal_type=signal_type,
                volume_ratio=volume_ratio,
                block_trades=block_count,
                avg_block_size=avg_block,
                confidence=confidence
            )
            
        except Exception as e:
            logger.debug("Dark pool analysis failed for {}: {}", symbol, e)
            return None
    
    def get_top_institutional_buys(self, symbols: List[str], top_n: int = 5) -> List[str]:
        """Get symbols with strongest institutional buying"""
        scored = []
        
        for symbol in symbols:
            signal = self.analyze(symbol)
            if signal.score > 0:
                scored.append((symbol, signal.score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:top_n]]


# Global instance
_tracker = None

def get_smart_money_tracker() -> SmartMoneyTracker:
    global _tracker
    if _tracker is None:
        _tracker = SmartMoneyTracker()
    return _tracker


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SmartMoneyTracker...")
    
    tracker = SmartMoneyTracker()
    
    for symbol in ["AAPL", "TSLA", "AMD"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        signal = tracker.analyze(symbol)
        
        print(f"Score: {signal.score:+d}")
        print(f"Signals: {signal.signals}")
        
        if signal.institutional:
            inst = signal.institutional
            print(f"Institutional: {inst.inst_ownership_pct:.1%}")
            print(f"Insider Sentiment: {inst.net_insider_sentiment}")
        
        if signal.dark_pool:
            dp = signal.dark_pool
            print(f"Dark Pool: {dp.signal_type}")
            print(f"Block Trades: {dp.block_trades}")
