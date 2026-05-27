"""
Social Sentiment Analyzer
===========================
Analyze sentiment from social media and web sources.

Sources:
1. Reddit (WSB, investing)
2. Twitter/X trends
3. StockTwits
4. Google Trends
5. News Sentiment
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class MentionData:
    """Social mention data"""
    source: str
    mentions_24h: int
    sentiment: str  # "BULLISH", "BEARISH", "NEUTRAL"
    change_24h: float  # % change in mentions


@dataclass
class SocialSignal:
    """Social sentiment analysis"""
    symbol: str
    
    # Overall sentiment
    overall_sentiment: str  # "VERY_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "VERY_BEARISH"
    sentiment_score: float  # -1 to +1
    
    # Metrics
    total_mentions: int
    mention_change_24h: float
    
    # Source breakdown
    sources: List[MentionData]
    
    # Signals
    is_trending: bool
    is_retail_frenzy: bool
    contrarian_signal: str  # "SELL" if too bullish, "BUY" if too bearish
    
    # Historical
    sentiment_7d_avg: float
    sentiment_momentum: str  # "IMPROVING", "DECLINING", "STABLE"
    
    # Combined score
    social_score: int  # -100 to +100
    details: List[str]


class SocialSentimentAnalyzer:
    """
    Social Media Sentiment Analysis
    
    Key Insights:
    1. Extreme bullish = contrarian sell
    2. Extreme bearish = contrarian buy
    3. Volume spike = attention, not direction
    4. WSB mentions correlate with gamma squeezes
    
    Scoring:
    - Moderate bullish + rising: +20
    - Extreme bullish (contrarian): -30
    - Extreme bearish (contrarian): +30
    - Trending: +10
    - Retail frenzy: -20 (caution)
    
    Note: In production, use proper APIs:
    - Reddit API (PRAW)
    - Twitter API
    - StockTwits API
    - Google Trends API
    """
    
    # Simulated popular stocks
    POPULAR_STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "META", "GME", "AMC"]
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> SocialSignal:
        """Analyze social sentiment"""
        details = []
        score = 0
        
        # In production, fetch real social data
        # Here we use stock price momentum and volatility as proxies
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 10:
            return self._neutral_result(symbol)
        
        close = df['Close']
        volume = df['Volume']
        returns = close.pct_change()
        
        # Estimate sentiment from price/volume action
        recent_return = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        volume_surge = volume.iloc[-1] / volume.tail(20).mean()
        volatility = returns.tail(10).std() * 100
        
        # 1. Estimate Overall Sentiment
        if recent_return > 10 and volume_surge > 2:
            sentiment = "VERY_BULLISH"
            sentiment_score = 0.9
        elif recent_return > 5:
            sentiment = "BULLISH"
            sentiment_score = 0.5
        elif recent_return < -10 and volume_surge > 2:
            sentiment = "VERY_BEARISH"
            sentiment_score = -0.9
        elif recent_return < -5:
            sentiment = "BEARISH"
            sentiment_score = -0.5
        else:
            sentiment = "NEUTRAL"
            sentiment_score = 0
        
        # 2. Simulated mention data
        is_popular = symbol in self.POPULAR_STOCKS
        base_mentions = 5000 if is_popular else 500
        mentions = int(base_mentions * (1 + abs(recent_return) / 5))
        mention_change = volume_surge * 50 - 50  # Proxy
        
        sources = [
            MentionData("Reddit", int(mentions * 0.4), sentiment, mention_change),
            MentionData("Twitter", int(mentions * 0.35), sentiment, mention_change * 0.8),
            MentionData("StockTwits", int(mentions * 0.25), sentiment, mention_change * 1.2),
        ]
        
        # 3. Trending detection
        is_trending = volume_surge > 2 or abs(recent_return) > 5
        if is_trending:
            details.append("TRENDING")
            score += 10
        
        # 4. Retail frenzy detection
        is_frenzy = volume_surge > 3 and abs(recent_return) > 8
        if is_frenzy:
            details.append("RETAIL_FRENZY")
            score -= 20  # Caution - volatile
        
        # 5. Contrarian signals
        if sentiment == "VERY_BULLISH":
            contrarian = "SELL"
            score -= 30
            details.append("CONTRARIAN_SELL:Too_Bullish")
        elif sentiment == "VERY_BEARISH":
            contrarian = "BUY"
            score += 30
            details.append("CONTRARIAN_BUY:Capitulation")
        elif sentiment == "BULLISH":
            contrarian = "NONE"
            score += 15
            details.append("POSITIVE_SENTIMENT")
        elif sentiment == "BEARISH":
            contrarian = "NONE"
            score -= 15
        else:
            contrarian = "NONE"
        
        # 6. Sentiment momentum (7-day)
        ret_7d = (close.iloc[-1] / close.iloc[-7] - 1) if len(close) >= 7 else 0
        ret_3d = (close.iloc[-1] / close.iloc[-3] - 1) if len(close) >= 3 else 0
        
        if ret_3d > ret_7d * 0.5 and ret_3d > 0:
            sentiment_momentum = "IMPROVING"
        elif ret_3d < ret_7d * 0.5 and ret_3d < 0:
            sentiment_momentum = "DECLINING"
        else:
            sentiment_momentum = "STABLE"
        
        return SocialSignal(
            symbol=symbol,
            overall_sentiment=sentiment,
            sentiment_score=sentiment_score,
            total_mentions=mentions,
            mention_change_24h=mention_change,
            sources=sources,
            is_trending=is_trending,
            is_retail_frenzy=is_frenzy,
            contrarian_signal=contrarian,
            sentiment_7d_avg=ret_7d,
            sentiment_momentum=sentiment_momentum,
            social_score=max(-100, min(100, score)),
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='30d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _neutral_result(self, symbol: str) -> SocialSignal:
        """Neutral result"""
        return SocialSignal(
            symbol=symbol, overall_sentiment="NEUTRAL", sentiment_score=0,
            total_mentions=0, mention_change_24h=0, sources=[],
            is_trending=False, is_retail_frenzy=False, contrarian_signal="NONE",
            sentiment_7d_avg=0, sentiment_momentum="STABLE",
            social_score=0, details=[]
        )


# Global
_analyzer = None

def get_social_analyzer() -> SocialSentimentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SocialSentimentAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SocialSentimentAnalyzer...")
    
    analyzer = SocialSentimentAnalyzer()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*60}")
        print(f"{symbol}")
        print('='*60)
        
        result = analyzer.analyze(symbol)
        
        print(f"Sentiment: {result.overall_sentiment} ({result.sentiment_score:+.2f})")
        print(f"Social Score: {result.social_score:+d}")
        print()
        print(f"Mentions: {result.total_mentions:,} ({result.mention_change_24h:+.0f}%)")
        print(f"Trending: {result.is_trending}")
        print(f"Retail Frenzy: {result.is_retail_frenzy}")
        print(f"Contrarian: {result.contrarian_signal}")
        print()
        print("Sources:")
        for s in result.sources:
            print(f"  {s.source}: {s.mentions_24h:,} ({s.sentiment})")
        print(f"Details: {result.details}")
