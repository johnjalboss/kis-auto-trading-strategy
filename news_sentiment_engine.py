"""
Real-Time AI Quant News Sentiment Engine (news_sentiment_engine.py)
======================================================================
Theoretical Foundations:
1. Alejandro Lopez-Lira & Yuehua Tang (Journal of Financial Economics 2023):
   - Return Predictability and LLM/NLP News Sentiment Scoring.
2. CFA Institute Market Studies (2024/2025):
   - Detrended Sentiment Scoring (S_tilde = S_symbol - S_SPY) to eliminate macro market bias.
3. Natural Language Deduplication & Exponential Time-Decay:
   - Jaccard token overlap filter (>0.50) to prevent duplicate media echo distortion.
   - Half-life time decay weighting: exp(-dt / 24.0 hours).
"""

import time
import math
import re
from typing import Dict, Any, List, Set
from loguru import logger


class NewsSentimentEngine:
    """Real-Time AI News Sentiment Scanner with Semantic Deduplication & Detrending."""

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
        self._spy_sentiment_cache = (0.0, 0.0)  # (timestamp, score)

    def _extract_tokens(self, text: str) -> Set[str]:
        """Extract alphanumeric word tokens for Jaccard similarity comparison."""
        return set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))

    def _is_duplicate_headline(self, new_tokens: Set[str], processed_token_sets: List[Set[str]], threshold: float = 0.50) -> bool:
        """Determines if a headline is an echo of an already processed story."""
        if not new_tokens:
            return False
        for seen in processed_token_sets:
            if not seen:
                continue
            intersection = len(new_tokens & seen)
            union = len(new_tokens | seen)
            if union > 0 and (intersection / union) >= threshold:
                return True
        return False

    def _get_spy_market_sentiment(self, fc) -> float:
        """Computes baseline market sentiment from SPY to detrend individual stock news."""
        now = time.time()
        ts, cached_spy_score = self._spy_sentiment_cache
        if now - ts < 1800:  # 30-min cache
            return cached_spy_score

        try:
            spy_news = fc.get_company_news("SPY", days_back=2)
            if not spy_news:
                return 0.0

            raw_scores = []
            seen_tokens = []
            for item in spy_news[:8]:
                headline = item.get("headline", "")
                tokens = self._extract_tokens(headline)
                if self._is_duplicate_headline(tokens, seen_tokens):
                    continue
                seen_tokens.append(tokens)

                h_lower = headline.lower()
                s = 0
                for kw in self.BULLISH_KEYWORDS:
                    if kw in h_lower: s += 15; break
                for kw in self.BEARISH_KEYWORDS:
                    if kw in h_lower: s -= 20; break
                raw_scores.append(s)

            avg_spy = float(sum(raw_scores) / len(raw_scores)) if raw_scores else 0.0
            self._spy_sentiment_cache = (now, avg_spy)
            return avg_spy
        except Exception:
            return 0.0

    def analyze_symbol_news(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches, deduplicates, time-decays, and detrends news sentiment for a given symbol.
        """
        now = time.time()
        if symbol in self._cache:
            entry = self._cache[symbol]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["result"]

        weighted_score = 0.0
        total_weight = 0.0
        highlights = []
        unique_news_count = 0

        try:
            from finnhub_client import get_finnhub_client
            fc = get_finnhub_client()
            if fc.is_enabled():
                news_items = fc.get_company_news(symbol, days_back=3)
                processed_tokens: List[Set[str]] = []

                if news_items:
                    for item in news_items[:30]:
                        headline = item.get("headline", "")
                        summary = item.get("summary", "")
                        full_text = f"{headline} {summary}"
                        tokens = self._extract_tokens(headline)

                        # [STEP 1: JACCARD DEDUPLICATION] Filter duplicate news echoes
                        if self._is_duplicate_headline(tokens, processed_tokens, threshold=0.50):
                            continue
                        processed_tokens.append(tokens)
                        unique_news_count += 1

                        # [STEP 2: EXPONENTIAL TIME DECAY] Half-life = 24 hours
                        pub_time = item.get("datetime", now)
                        age_hours = max(0.0, (now - pub_time) / 3600.0)
                        weight = math.exp(-age_hours / 24.0)

                        item_score = 0
                        h_lower = full_text.lower()

                        # Bullish scoring
                        for kw in self.BULLISH_KEYWORDS:
                            if kw in h_lower:
                                item_score += 15
                                highlights.append(f"🟢 {kw.upper()}")
                                break

                        # Bearish scoring
                        for kw in self.BEARISH_KEYWORDS:
                            if kw in h_lower:
                                item_score -= 20
                                highlights.append(f"🔴 {kw.upper()}")
                                break

                        weighted_score += item_score * weight
                        total_weight += weight

                # [STEP 3: DETRENDING AGAINST SPY MARKET SENTIMENT]
                raw_score = (weighted_score / total_weight) if total_weight > 0 else 0.0
                spy_baseline = self._get_spy_market_sentiment(fc) if symbol != "SPY" else 0.0
                detrended_score = raw_score - spy_baseline

                final_score = int(max(-100, min(100, round(detrended_score * 2.5))))
            else:
                final_score = 0
                spy_baseline = 0.0

            sentiment_label = "BULLISH" if final_score >= 15 else ("BEARISH" if final_score <= -15 else "NEUTRAL")

            result = {
                "symbol": symbol,
                "score": final_score,
                "raw_score": round(raw_score, 1) if 'raw_score' in locals() else 0.0,
                "spy_baseline": round(spy_baseline, 1) if 'spy_baseline' in locals() else 0.0,
                "label": sentiment_label,
                "highlights": list(set(highlights))[:5],
                "unique_news_count": unique_news_count
            }

            self._cache[symbol] = {"timestamp": now, "result": result}
            logger.info(
                "📰 [NEWS_SENTIMENT_DETRENDED] {}: Final {:+d} (Raw: {:+.1f}, SPY Base: {:+.1f}, {} Unique Articles) | {}",
                symbol, final_score, result["raw_score"], result["spy_baseline"], unique_news_count, sentiment_label
            )
            return result

        except Exception as e:
            logger.debug("NewsSentimentEngine error for {}: {}", symbol, e)
            result = {"symbol": symbol, "score": 0, "label": "NEUTRAL", "highlights": [], "unique_news_count": 0}
            return result
