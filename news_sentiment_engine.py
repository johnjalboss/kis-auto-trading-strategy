"""
Real-Time AI Quant News Sentiment Engine (news_sentiment_engine.py)
======================================================================
Scans real-time financial news headlines & earnings releases for portfolio and universe tickers.
Calculates Net Sentiment Score (-100 to +100) to provide early entry conviction or news risk penalties.
"""

import time
from typing import Dict, Any, List
from loguru import logger


class NewsSentimentEngine:
    """Real-Time AI News Sentiment Scanner."""

    BULLISH_KEYWORDS = [
        "beat", "surpassed", "record revenue", "upgraded", "outperform",
        "guidance raised", "buyback", "dividend increase", "breakout",
        "fda approval", "partnership", "acquisition", "strong demand"
    ]

    BEARISH_KEYWORDS = [
        "missed", "downgraded", "underperform", "guidance lowered",
        "investigation", "lawsuit", "sec inquiry", "layoffs",
        "recall", "bankrupt", "offering", "dilution", "warning"
    ]

    def __init__(self, cache_ttl_seconds: int = 600):
        self.cache_ttl = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def analyze_symbol_news(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches and scores recent news sentiment for a given symbol.
        """
        now = time.time()
        if symbol in self._cache:
            entry = self._cache[symbol]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["result"]

        score = 0
        highlights = []

        try:
            from finnhub_client import get_finnhub_client
            fc = get_finnhub_client()
            if fc.is_enabled():
                news_items = fc.get_company_news(symbol, days_back=2)
                if news_items:
                    for item in news_items[:10]:
                        headline = (item.get("headline", "") + " " + item.get("summary", "")).lower()
                        
                        # Bullish scoring
                        for kw in self.BULLISH_KEYWORDS:
                            if kw in headline:
                                score += 15
                                highlights.append(f"🟢 {kw.upper()}")
                                break

                        # Bearish scoring
                        for kw in self.BEARISH_KEYWORDS:
                            if kw in headline:
                                score -= 20
                                highlights.append(f"🔴 {kw.upper()}")
                                break

            # Clamp score (-100 to +100)
            final_score = max(-100, min(100, score))
            sentiment_label = "BULLISH" if final_score >= 20 else ("BEARISH" if final_score <= -20 else "NEUTRAL")

            result = {
                "symbol": symbol,
                "score": final_score,
                "label": sentiment_label,
                "highlights": list(set(highlights))[:5],
                "news_count": len(highlights)
            }

            self._cache[symbol] = {"timestamp": now, "result": result}
            logger.info("📰 [NEWS_SENTIMENT] {}: Score {} ({}) | Highlights: {}",
                        symbol, final_score, sentiment_label, result["highlights"])
            return result

        except Exception as e:
            logger.debug("NewsSentimentEngine error for {}: {}", symbol, e)
            result = {"symbol": symbol, "score": 0, "label": "NEUTRAL", "highlights": [], "news_count": 0}
            return result
