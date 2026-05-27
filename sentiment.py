"""
Sentiment Analysis Module
==========================
Analyze market sentiment from multiple sources.

Sources:
1. Fear & Greed Index (CNN)
2. Reddit WSB Mentions (estimated)
3. News Sentiment
4. Social Media Momentum
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import requests
import re
from loguru import logger


@dataclass
class FearGreedData:
    """Fear & Greed Index data"""
    value: int  # 0-100
    label: str  # "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
    signal: str  # "BUY", "SELL", "HOLD"


@dataclass
class RedditSentiment:
    """Reddit WSB sentiment estimate"""
    symbol: str
    mentions: int
    sentiment: str  # "BULLISH", "BEARISH", "NEUTRAL"
    is_trending: bool
    score: int  # -100 to +100


@dataclass
class SentimentSignal:
    """Combined sentiment signal"""
    symbol: str
    score: int  # -100 to +100
    signal: str  # "BULLISH", "BEARISH", "NEUTRAL"
    
    fear_greed: Optional[FearGreedData]
    retail_sentiment: str
    news_sentiment: str
    
    details: List[str]


class SentimentAnalyzer:
    """
    Multi-Source Sentiment Analyzer
    
    Scoring:
    - Fear & Greed <25 (Extreme Fear): +30 (contrarian buy)
    - Fear & Greed >75 (Extreme Greed): -30 (contrarian sell)
    - High retail bullish: -15 (fade retail)
    - High retail bearish: +15 (fade retail)
    - Positive news flow: +20
    - Negative news flow: -20
    """
    
    def __init__(self):
        self._fg_cache: Optional[Tuple[FearGreedData, datetime]] = None
        self._cache_ttl = 3600  # 1 hour
    
    def analyze(self, symbol: str = None) -> SentimentSignal:
        """Analyze overall market sentiment"""
        score = 0
        details = []
        
        # 1. Fear & Greed Index
        fg = self._get_fear_greed()
        
        if fg:
            if fg.value < 25:
                score += 30
                details.append(f"F&G:{fg.value} EXTREME_FEAR (BUY)")
            elif fg.value < 40:
                score += 15
                details.append(f"F&G:{fg.value} FEAR")
            elif fg.value > 75:
                score -= 30
                details.append(f"F&G:{fg.value} EXTREME_GREED (SELL)")
            elif fg.value > 60:
                score -= 15  
                details.append(f"F&G:{fg.value} GREED")
            else:
                details.append(f"F&G:{fg.value} NEUTRAL")
        
        # 2. VIX-based sentiment proxy
        vix_sentiment = self._get_vix_sentiment()
        if vix_sentiment == "FEAR":
            score += 15  # Contrarian
            details.append("VIX_HIGH (Contrarian BUY)")
        elif vix_sentiment == "COMPLACENT":
            score -= 10
            details.append("VIX_LOW (Caution)")
        
        # 3. Put/Call Ratio sentiment (market wide)
        pc_sentiment = self._get_pc_sentiment()
        if pc_sentiment == "BEARISH":
            score += 10  # Contrarian
            details.append("P/C_HIGH (Contrarian BUY)")
        elif pc_sentiment == "BULLISH":
            score -= 5
            details.append("P/C_LOW (Caution)")
        
        # 4. Estimate retail sentiment (proxy)
        retail_sentiment = self._estimate_retail_sentiment(symbol)
        if retail_sentiment == "EXTREME_BULLISH":
            score -= 15  # Fade retail
            details.append("RETAIL_BULLISH (Fade)")
        elif retail_sentiment == "EXTREME_BEARISH":
            score += 15  # Fade retail
            details.append("RETAIL_BEARISH (Fade)")
        
        # 5. News sentiment estimate
        news_sentiment = self._estimate_news_sentiment(symbol) if symbol is not None else "NEUTRAL"
        if news_sentiment == "POSITIVE":
            score += 10
            details.append("NEWS_POSITIVE")
        elif news_sentiment == "NEGATIVE":
            score -= 10
            details.append("NEWS_NEGATIVE")
        
        # Determine signal
        if score > 25:
            signal = "BULLISH"
        elif score < -25:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
        
        return SentimentSignal(
            symbol=symbol or "MARKET",
            score=max(-100, min(100, score)),
            signal=signal,
            fear_greed=fg,
            retail_sentiment=retail_sentiment,
            news_sentiment=news_sentiment,
            details=details
        )
    
    def _get_fear_greed(self) -> Optional[FearGreedData]:
        """Get CNN Fear & Greed Index"""
        # Check cache
        if self._fg_cache:
            data, timestamp = self._fg_cache
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        
        try:
            # Use alternative.me API (free)
            url = "https://api.alternative.me/fng/?limit=1"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                result = resp.json()
                if result.get('data'):
                    item = result['data'][0]
                    value = int(item['value'])
                    label = item['value_classification']
                    
                    if value < 25:
                        signal = "BUY"
                    elif value > 75:
                        signal = "SELL"
                    else:
                        signal = "HOLD"
                    
                    fg = FearGreedData(value=value, label=label, signal=signal)
                    self._fg_cache = (fg, datetime.now())
                    return fg
                    
        except Exception as e:
            logger.debug("Fear & Greed fetch failed: {}", e)
        
        # Fallback - estimate from VIX
        return self._estimate_fear_greed_from_vix()
    
    def _estimate_fear_greed_from_vix(self) -> Optional[FearGreedData]:
        """Estimate Fear & Greed from VIX proxy (VIXY ETF via KIS API)"""
        try:
            import kis_data
            df = kis_data.download("VIXY", period="10d", progress=False)
            
            if df is None or df.empty or len(df) < 3:
                return None
            
            current_vixy = float(df['Close'].iloc[-1])
            sma = float(df['Close'].mean())
            
            # VIXY 비율로 공포/탐욕 추정
            ratio = current_vixy / sma if sma > 0 else 1.0
            
            if ratio > 1.3:
                return FearGreedData(value=15, label="Extreme Fear", signal="BUY")
            elif ratio > 1.1:
                return FearGreedData(value=35, label="Fear", signal="BUY")
            elif ratio < 0.8:
                return FearGreedData(value=80, label="Extreme Greed", signal="SELL")
            elif ratio < 0.9:
                return FearGreedData(value=65, label="Greed", signal="HOLD")
            else:
                return FearGreedData(value=50, label="Neutral", signal="HOLD")
            
        except Exception:
            return None
    
    def _get_vix_sentiment(self) -> str:
        """Get VIX-based sentiment via VIXY ETF proxy"""
        try:
            import kis_data
            df = kis_data.download("VIXY", period="60d", progress=False)
            
            if df is None or df.empty or len(df) < 20:
                return "NEUTRAL"
            
            current = float(df['Close'].iloc[-1])
            sma_20 = float(df['Close'].tail(20).mean())
            
            if sma_20 > 0 and current > sma_20 * 1.2:
                return "FEAR"
            elif sma_20 > 0 and current < sma_20 * 0.8:
                return "COMPLACENT"
            return "NEUTRAL"
            
        except Exception:
            return "NEUTRAL"
    
    def _get_pc_sentiment(self) -> str:
        """Get Put/Call ratio sentiment — KIS API doesn't support options, use price proxy"""
        try:
            import kis_data
            # SPY의 최근 가격 변동으로 추정
            df = kis_data.download("SPY", period="10d", progress=False)
            if df is None or df.empty or len(df) < 5:
                return "NEUTRAL"
            
            ret_5d = (float(df['Close'].iloc[-1]) / float(df['Close'].iloc[-5]) - 1)
            vol = df['Close'].pct_change().std()
            
            # 하락 + 높은 변동성 = 풋 매수 활발 (베어리시)
            if ret_5d < -0.03 and float(vol) > 0.015:
                return "BEARISH"
            elif ret_5d > 0.03 and float(vol) < 0.01:
                return "BULLISH"
            return "NEUTRAL"
            
        except Exception:
            return "NEUTRAL"
    
    def _estimate_retail_sentiment(self, symbol: str = None) -> str:
        """Estimate retail/social sentiment via KIS API price data"""
        try:
            import kis_data
            
            if symbol is None:
                symbol = "SPY"
            
            df = kis_data.download(symbol, period="10d", progress=False)
            if df is None or df.empty or len(df) < 5:
                return "NEUTRAL"
            
            # Use recent volume and price action as proxy
            vol_ratio = float(df['Volume'].iloc[-1]) / max(float(df['Volume'].mean()), 1)
            price_change = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[0])) / float(df['Close'].iloc[0])
            
            # High volume + big up move = extreme bullish retail
            if vol_ratio > 2 and price_change > 0.05:
                return "EXTREME_BULLISH"
            elif vol_ratio > 2 and price_change < -0.05:
                return "EXTREME_BEARISH"
            elif price_change > 0.03:
                return "BULLISH"
            elif price_change < -0.03:
                return "BEARISH"
            
            return "NEUTRAL"
            
        except Exception:
            return "NEUTRAL"
    
    def _estimate_news_sentiment(self, symbol: str) -> str:
        """Estimate news sentiment from price action"""
        try:
            import kis_data
            
            # Use price momentum as a proxy for news sentiment
            price_data = kis_data.get_current_price(symbol)
            if price_data:
                change_pct = price_data.get('pchg', 0)
                if change_pct > 3:
                    return "POSITIVE"
                elif change_pct < -3:
                    return "NEGATIVE"
            
            return "NEUTRAL"
            
        except:
            return "NEUTRAL"


# Need pandas import
import pandas as pd

# Global instance
_analyzer = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SentimentAnalyzer...")
    
    analyzer = SentimentAnalyzer()
    
    # Market-wide sentiment
    print("\n" + "="*50)
    print("MARKET SENTIMENT")
    print("="*50)
    
    signal = analyzer.analyze()
    
    print(f"Signal: {signal.signal} (Score: {signal.score:+d})")
    
    if signal.fear_greed:
        print(f"Fear & Greed: {signal.fear_greed.value} ({signal.fear_greed.label})")
    
    print(f"Retail: {signal.retail_sentiment}")
    print(f"News: {signal.news_sentiment}")
    print(f"Details: {signal.details}")
    
    # Stock-specific
    for symbol in ["AAPL", "TSLA"]:
        print(f"\n{symbol}:")
        stock_signal = analyzer.analyze(symbol)
        print(f"  Score: {stock_signal.score:+d} ({stock_signal.signal})")
