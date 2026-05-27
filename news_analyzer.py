"""
News Sentiment Analyzer
========================
Real-time news analysis for trading signals.

Sources:
1. Yahoo Finance News
2. Finviz News
3. Price Reaction Analysis
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
import re
import yfinance as yf
from loguru import logger


@dataclass
class NewsItem:
    """Individual news item"""
    title: str
    source: str
    published: datetime
    sentiment: str  # "POSITIVE", "NEGATIVE", "NEUTRAL"
    sentiment_score: float  # -1 to +1
    relevance: float  # 0 to 1


@dataclass
class NewsSentiment:
    """News sentiment analysis result"""
    symbol: str
    overall_sentiment: str
    sentiment_score: float  # -100 to +100
    
    news_count: int
    positive_count: int
    negative_count: int
    
    recent_news: List[NewsItem]
    has_breaking_news: bool
    breaking_headline: Optional[str]
    
    recommendation: str


# Sentiment keywords
POSITIVE_KEYWORDS = [
    'surge', 'soar', 'jump', 'rally', 'gain', 'rise', 'up', 'high', 'record',
    'beat', 'exceed', 'upgrade', 'buy', 'bullish', 'growth', 'profit', 'success',
    'breakthrough', 'innovation', 'expand', 'strong', 'positive', 'optimistic',
    'outperform', 'revenue', 'earnings beat', 'raised guidance', 'dividend'
]

NEGATIVE_KEYWORDS = [
    'fall', 'drop', 'crash', 'plunge', 'decline', 'down', 'low', 'miss',
    'downgrade', 'sell', 'bearish', 'loss', 'fail', 'layoff', 'cut',
    'weakness', 'negative', 'pessimistic', 'underperform', 'lawsuit', 'recall',
    'investigation', 'warning', 'concern', 'risk', 'delay', 'debt'
]


class NewsAnalyzer:
    """
    News Sentiment Analysis Engine
    
    Methods:
    1. Keyword-based sentiment scoring
    2. Headline pattern matching
    3. Price reaction confirmation
    
    Scoring:
    - Positive news: +10 to +30 per item
    - Negative news: -10 to -30 per item
    - Breaking news: ±50 impact
    """
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 1800  # 30 minutes
    
    def analyze(self, symbol: str) -> NewsSentiment:
        """Analyze news sentiment for a symbol"""
        # Check cache
        if symbol in self._cache:
            data, timestamp = self._cache[symbol]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        
        # Fetch news
        news_items = self._fetch_news(symbol)
        
        if not news_items:
            return self._neutral_sentiment(symbol)
        
        # Calculate sentiment
        total_score = 0
        positive_count = 0
        negative_count = 0
        
        for item in news_items:
            if item.sentiment == "POSITIVE":
                positive_count += 1
                total_score += item.sentiment_score * 30
            elif item.sentiment == "NEGATIVE":
                negative_count += 1
                total_score += item.sentiment_score * 30
        
        # Normalize score
        sentiment_score = max(-100, min(100, total_score))
        
        # Determine overall sentiment
        if sentiment_score > 30:
            overall = "BULLISH"
        elif sentiment_score < -30:
            overall = "BEARISH"
        else:
            overall = "NEUTRAL"
        
        # Check for breaking news (last hour)
        breaking = None
        has_breaking = False
        for item in news_items:
            if (datetime.now() - item.published).seconds < 3600:
                has_breaking = True
                breaking = item.title
                break
        
        # Generate recommendation
        if has_breaking and abs(sentiment_score) > 50:
            recommendation = "WAIT for volatility to settle"
        elif sentiment_score > 50:
            recommendation = "FAVORABLE - News supports long entry"
        elif sentiment_score < -50:
            recommendation = "AVOID - Negative news pressure"
        else:
            recommendation = "NEUTRAL - No significant news impact"
        
        result = NewsSentiment(
            symbol=symbol,
            overall_sentiment=overall,
            sentiment_score=sentiment_score,
            news_count=len(news_items),
            positive_count=positive_count,
            negative_count=negative_count,
            recent_news=news_items[:5],
            has_breaking_news=has_breaking,
            breaking_headline=breaking,
            recommendation=recommendation
        )
        
        # Cache result
        self._cache[symbol] = (result, datetime.now())
        
        return result
    
    def _fetch_news(self, symbol: str) -> List[NewsItem]:
        """Fetch news from yfinance — KIS 프록시 우회하여 실제 yfinance 사용"""
        news_items = []
        
        try:
            # KISTickerProxy는 .news 미지원 → sys.modules에서 실제 yfinance 직접 호출
            import sys
            _real_yf = sys.modules.get('yfinance._original', None)
            if _real_yf is None:
                # data_proxy.py가 yfinance를 shimming 하지만 원본은 다른 이름으로 보존
                import importlib
                try:
                    import yfinance as _yf_raw
                    # KISTickerProxy가 아닌 원본 Ticker 클래스 직접 사용
                    _orig_ticker_cls = getattr(_yf_raw, '_OriginalTicker', None) or getattr(_yf_raw, 'Ticker', None)
                    ticker = _orig_ticker_cls(symbol)
                except Exception:
                    ticker = yf.Ticker(symbol)
            else:
                ticker = _real_yf.Ticker(symbol)
            
            # .news 접근 — KISTickerProxy라면 AttributeError 발생
            raw_news = getattr(ticker, 'news', None)
            if raw_news is None:
                # fallback: 뉴스 없음으로 처리 (스크리너 페널티 없음)
                return []
            
            for item in raw_news[:10]:  # Last 10 news items
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '') or item.get('content', {}).get('title', '')
                if not title:
                    continue
                
                sentiment, score = self._analyze_headline(title)
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                
                news_items.append(NewsItem(
                    title=title,
                    source=item.get('publisher', 'Unknown'),
                    published=pub_time,
                    sentiment=sentiment,
                    sentiment_score=score,
                    relevance=1.0
                ))
                
        except Exception as e:
            logger.debug("News fetch failed for {}: {}", symbol, e)
        
        return news_items
    
    def _analyze_headline(self, headline: str) -> tuple:
        """Analyze headline sentiment"""
        headline_lower = headline.lower()
        
        pos_count = sum(1 for word in POSITIVE_KEYWORDS if word in headline_lower)
        neg_count = sum(1 for word in NEGATIVE_KEYWORDS if word in headline_lower)
        
        if pos_count > neg_count:
            sentiment = "POSITIVE"
            score = min(1.0, pos_count * 0.3)
        elif neg_count > pos_count:
            sentiment = "NEGATIVE"
            score = -min(1.0, neg_count * 0.3)
        else:
            sentiment = "NEUTRAL"
            score = 0
        
        return sentiment, score
    
    def _neutral_sentiment(self, symbol: str) -> NewsSentiment:
        """Return neutral sentiment"""
        return NewsSentiment(
            symbol=symbol,
            overall_sentiment="NEUTRAL",
            sentiment_score=0,
            news_count=0,
            positive_count=0,
            negative_count=0,
            recent_news=[],
            has_breaking_news=False,
            breaking_headline=None,
            recommendation="No recent news"
        )
    
    def get_market_news_sentiment(self) -> float:
        """Get overall market news sentiment"""
        market_symbols = ['SPY', 'QQQ', 'DIA']
        scores = []
        
        for symbol in market_symbols:
            result = self.analyze(symbol)
            scores.append(result.sentiment_score)
        
        return sum(scores) / len(scores) if scores else 0


# Global instance
_analyzer = None

def get_news_analyzer() -> NewsAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = NewsAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing NewsAnalyzer...")
    
    analyzer = NewsAnalyzer()
    
    for symbol in ["AAPL", "TSLA", "NVDA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Sentiment: {result.overall_sentiment} ({result.sentiment_score:+.0f})")
        print(f"News Count: {result.news_count} (+{result.positive_count}/-{result.negative_count})")
        print(f"Breaking: {result.has_breaking_news}")
        print(f"Recommendation: {result.recommendation}")
        
        if result.recent_news:
            print("\nRecent Headlines:")
            for news in result.recent_news[:3]:
                print(f"  [{news.sentiment}] {news.title[:60]}...")
