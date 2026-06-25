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
    
    # ── [Quant-Shield] Catastrophic Black-Swan Risk Fields ──
    has_catastrophic_risk: bool = False
    catastrophic_reason: Optional[str] = None


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
        self._cache_ttl = 1800  # 30 minutes (Optimized for faster black-swan detection within Free Tier limits)
    
    def _judge_with_gemini(self, symbol: str, news_items: List[NewsItem]) -> Optional[tuple]:
        """
        Judge news sentiment using Gemini Free Tier API.
        Returns: (sentiment: str, score: float, has_catastrophic: bool, catastrophic_reason: str, reason: str) or None if failed.
        """
        import os
        import json
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.debug("GEMINI_API_KEY not found. Skipping Gemini sentiment analysis.")
            return None
            
        if not news_items:
            return "NEUTRAL", 0.0, False, None, "No news items to judge"
            
        # Limit to top 8 news items to minimize prompt size and token usage
        headlines = [item.title for item in news_items[:8]]
        
        prompt = (
            f"You are an expert financial news sentiment judge. Analyze the short-term market impact of the following news headlines for stock symbol '{symbol}'.\n"
            "Evaluate:\n"
            "1. Overall sentiment: BULLISH (price up in 1-5 days), BEARISH (price down), or NEUTRAL.\n"
            "2. Quant score: An integer score from -100 (extremely bearish/disastrous) to +100 (extremely bullish/stellar).\n"
            "3. Catastrophic Risk: Identify if there is a fatal event threatening corporate survival. Look specifically for bankruptcy (Chapter 11), delisting, major fraud, insolvency, or criminal indictment of executives.\n\n"
            "Provide your output strictly in JSON format with keys:\n"
            "- 'sentiment': exactly one of 'BULLISH', 'BEARISH', 'NEUTRAL'\n"
            "- 'sentiment_score': integer between -100 and 100\n"
            "- 'has_catastrophic_risk': boolean (true if fatal event is detected, false otherwise)\n"
            "- 'catastrophic_reason': string (description of the fatal risk, null if none)\n"
            "- 'reason': short summary under 100 characters.\n\n"
            "Headlines:\n"
            + "\n".join(f"- {h}" for h in headlines) + "\n\n"
            "Output JSON only (no markdown block, no ```json):"
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        try:
            # Short timeout to prevent blocking the trading execution thread
            resp = requests.post(url, headers=headers, json=payload, timeout=6)
            if resp.status_code == 200:
                res_json = resp.json()
                text = res_json['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(text.strip())
                sentiment = data.get("sentiment", "NEUTRAL").upper()
                score = float(data.get("sentiment_score", 0.0))
                has_catastrophic = bool(data.get("has_catastrophic_risk", False))
                catastrophic_reason = data.get("catastrophic_reason", None)
                reason = data.get("reason", "Analyzed by Gemini")
                
                if sentiment not in ["BULLISH", "BEARISH", "NEUTRAL"]:
                    sentiment = "NEUTRAL"
                    
                logger.info("[GEMINI_JUDGE] {} | Sentiment: {} (Score: {}), Catastrophic Risk: {} ({}), Reason: {}", 
                            symbol, sentiment, score, has_catastrophic, catastrophic_reason, reason)
                return sentiment, score, has_catastrophic, catastrophic_reason, reason
        except Exception as e:
            logger.warning("[GEMINI_JUDGE] Failed to judge with Gemini for {}: {}. Falling back to default scoring.", symbol, e)
            
        return None

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
        
        # Try Gemini Sentiment Judge first
        gemini_result = self._judge_with_gemini(symbol, news_items)
        if gemini_result:
            overall, sentiment_score, has_catastrophic, catastrophic_reason, reason = gemini_result
            positive_count = sum(1 for item in news_items if item.sentiment == "POSITIVE")
            negative_count = sum(1 for item in news_items if item.sentiment == "NEGATIVE")
            
            # Check for breaking news (last hour)
            breaking = None
            has_breaking = False
            for item in news_items:
                if (datetime.now() - item.published).seconds < 3600:
                    has_breaking = True
                    breaking = item.title
                    break
            
            if has_catastrophic:
                recommendation = f"🚨 EMERGENCY CATASTROPHIC RISK: {catastrophic_reason}"
            elif overall == "BULLISH":
                recommendation = f"FAVORABLE (Gemini) - {reason}"
            elif overall == "BEARISH":
                recommendation = f"AVOID (Gemini) - {reason}"
            else:
                recommendation = f"NEUTRAL (Gemini) - {reason}"
                
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
                recommendation=recommendation,
                has_catastrophic_risk=has_catastrophic,
                catastrophic_reason=catastrophic_reason
            )
            
            self._cache[symbol] = (result, datetime.now())
            return result

        # Fallback to default keyword-based sentiment scoring & catastrophic filtering
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
        
        # 룰 기반 파멸적 리스크 필터링 (Bankruptcy, Delisting 등)
        catastrophic_keywords = ['bankruptcy', 'chapter 11', 'delisting', 'delisted', 'insolvency', 'insolvent', 'accounting fraud', 'indictment', 'liquidation', 'receivership']
        has_catastrophic = False
        catastrophic_reason = None
        for item in news_items:
            h_lower = item.title.lower()
            for kw in catastrophic_keywords:
                if kw in h_lower:
                    has_catastrophic = True
                    catastrophic_reason = f"Rule-based detection: '{kw}' found in headline: '{item.title}'"
                    break
            if has_catastrophic:
                break
        
        # Determine overall sentiment
        if has_catastrophic:
            overall = "BEARISH"
            sentiment_score = -100.0  # Force maximum panic
        elif sentiment_score > 30:
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
        if has_catastrophic:
            recommendation = f"🚨 EMERGENCY CATASTROPHIC RISK: {catastrophic_reason}"
        elif has_breaking and abs(sentiment_score) > 50:
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
            recommendation=recommendation,
            has_catastrophic_risk=has_catastrophic,
            catastrophic_reason=catastrophic_reason
        )
        
        # Cache result
        self._cache[symbol] = (result, datetime.now())
        
        return result
    
    def _fetch_news(self, symbol: str) -> List[NewsItem]:
        """
        Fetch news from 3 sources in priority order:
        1. Finnhub API (primary — structured, comprehensive)
        2. Finviz RSS  (secondary — cloud-safe, no auth needed, DISABLE_OPTIONS_FLOW 무관)
        3. yfinance    (tertiary — only if available and not blocked)
        """
        news_items = []

        # ── Source 1: Finnhub ──────────────────────────────────────────────────
        try:
            from finnhub_client import get_finnhub_client
            fh = get_finnhub_client()
            if fh.is_enabled():
                raw_news = fh.get_company_news(symbol)
                for item in raw_news[:12]:
                    title = item.get('headline', '')
                    if not title:
                        continue
                    sentiment, score = self._analyze_headline(title)
                    pub_time = datetime.fromtimestamp(item.get('datetime', 0))
                    news_items.append(NewsItem(
                        title=title,
                        source=item.get('source', 'Finnhub'),
                        published=pub_time,
                        sentiment=sentiment,
                        sentiment_score=score,
                        relevance=1.0
                    ))
                if news_items:
                    logger.debug("Finnhub: {} news items for {}", len(news_items), symbol)
                    return news_items
        except Exception as e:
            logger.warning("Finnhub news fetch failed for {}: {}", symbol, e)

        # ── Source 2: Finviz RSS (cloud-safe, no API key, works with DISABLE_OPTIONS_FLOW) ──
        try:
            import re
            import requests as _req
            finviz_url = f"https://finviz.com/quote.ashx?t={symbol.upper()}"
            headers = {"User-Agent": "Mozilla/5.0 (compatible; trading-bot/2.0)"}
            resp = _req.get(finviz_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                # Parse news table from Finviz HTML (lightweight regex)
                pattern = r'class="news-link-container"[^>]*><a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
                matches = re.findall(pattern, resp.text)
                if not matches:
                    # fallback pattern for different Finviz layout versions
                    pattern2 = r'<a[^>]+class="tab-link"[^>]+>([^<]{10,120})</a>'
                    titles = re.findall(pattern2, resp.text)
                    matches = [('finviz.com', t) for t in titles[:12]]
                for url_or_src, title in matches[:12]:
                    title = title.strip()
                    if not title or len(title) < 10:
                        continue
                    sentiment, score = self._analyze_headline(title)
                    news_items.append(NewsItem(
                        title=title,
                        source='Finviz',
                        published=datetime.now(),
                        sentiment=sentiment,
                        sentiment_score=score,
                        relevance=0.9
                    ))
                if news_items:
                    logger.debug("Finviz: {} news items for {}", len(news_items), symbol)
                    return news_items
        except Exception as e:
            logger.debug("Finviz news fetch failed for {}: {}", symbol, e)

        # ── Source 3: yfinance (only if not blocked by DISABLE_OPTIONS_FLOW) ──
        import os
        if os.getenv("DISABLE_OPTIONS_FLOW", "false").lower() == "true":
            logger.debug("yfinance news fetch skipped (DISABLE_OPTIONS_FLOW=true) — Finviz already attempted")
            return []

        try:
            import yfinance as _yf_raw
            _orig_ticker_cls = getattr(_yf_raw, '_OriginalTicker', None) or _yf_raw.Ticker
            ticker = _orig_ticker_cls(symbol)
            raw_news = getattr(ticker, 'news', None) or []
            for item in raw_news[:10]:
                if not isinstance(item, dict):
                    continue
                title = item.get('title', '') or item.get('content', {}).get('title', '')
                if not title:
                    continue
                sentiment, score = self._analyze_headline(title)
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                news_items.append(NewsItem(
                    title=title,
                    source=item.get('publisher', 'yfinance'),
                    published=pub_time,
                    sentiment=sentiment,
                    sentiment_score=score,
                    relevance=1.0
                ))
        except Exception as e:
            logger.debug("yfinance news fetch failed for {}: {}", symbol, e)

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
