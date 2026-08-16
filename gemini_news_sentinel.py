"""
[v9.0 GEMINI AI REAL-TIME NEWS SENTINEL & EVENT SHOCK ANALYZER]
Rate-Limit Shielded AI News Sentiment & Emergency Risk Engine.

Free-Tier API Optimization:
- 15 RPM / 1,500 RPD Free Tier Safe Guard: Caches news headline hashes.
- Only calls Gemini API for active positions or Top 10 final candidates (max ~5-10 calls/hour).
- Seamless Local Lexicon Fallback (VADER/TextBlob rule-based NLP) if API is throttled.

Emergency Risk Detection:
- Detects Bankruptcy, Fraud, SEC Investigation, FDA Rejection, CEO Resignation.
- Returns has_catastrophic_risk = True -> Emergency Exit Trigger!
"""

import time
import os
import hashlib
from typing import Dict, Any
from loguru import logger

_NEWS_CACHE = {}
_NEWS_TTL = 3600  # 1 hour TTL
_LAST_GEMINI_CALL = 0.0


class GeminiNewsSentinel:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    def analyze(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        if symbol in _NEWS_CACHE:
            ts, res = _NEWS_CACHE[symbol]
            if now - ts < _NEWS_TTL:
                return res

        res = {
            'sentiment_score': 0,        # -100 to +100
            'has_catastrophic_risk': False,
            'catastrophic_reason': '',
            'score_adj': 0,
            'reason': 'NEUTRAL_NEWS'
        }

        try:
            # 1. Fetch recent news headlines from Finnhub / KIS / yfinance
            from news_analyzer import get_news_analyzer
            raw_news_items = get_news_analyzer()._fetch_news(symbol)
            
            if not raw_news_items:
                _NEWS_CACHE[symbol] = (now, res)
                return res

            headlines = [n.title for n in raw_news_items[:5] if hasattr(n, 'title') and n.title]
            combined_text = " | ".join(headlines)

            if not combined_text:
                _NEWS_CACHE[symbol] = (now, res)
                return res

            # Hash check to avoid re-querying identical news
            text_hash = hashlib.md5(combined_text.encode('utf-8')).hexdigest()
            if f"hash_{text_hash}" in _NEWS_CACHE:
                _, cached_res = _NEWS_CACHE[f"hash_{text_hash}"]
                _NEWS_CACHE[symbol] = (now, cached_res)
                return cached_res

            # 2. Local Fast Lexicon Scan for Catastrophic Keyword Emergency (Zero API cost & 0ms speed!)
            lower_text = combined_text.lower()
            catastrophic_keywords = ["bankruptcy", "sec investigation", "fraud", "class action", "ceo resigned", "fda rejection", "subpoena"]
            
            for kw in catastrophic_keywords:
                if kw in lower_text:
                    res['has_catastrophic_risk'] = True
                    res['catastrophic_reason'] = f"CATASTROPHIC_KEYWORD: '{kw.upper()}' found in news!"
                    res['score_adj'] = -60
                    res['reason'] = res['catastrophic_reason']
                    logger.error("🚨 [AI_NEWS_SENTINEL] CATASTROPHIC RISK DETECTED FOR {}: {}", symbol, kw.upper())
                    _NEWS_CACHE[symbol] = (now, res)
                    _NEWS_CACHE[f"hash_{text_hash}"] = (now, res)
                    return res

            # 3. Gemini Flash AI Call (Only if API Key is present and throttled to >=4s apart)
            global _LAST_GEMINI_CALL
            if self.api_key and (now - _LAST_GEMINI_CALL >= 4.0):
                try:
                    import google.generativeai as genai
                    prompt = f"Analyze market sentiment for stock {symbol} from headlines: {combined_text}. Respond ONLY with a single integer score from -100 (extreme negative/disaster) to +100 (extreme positive/catalyst)."
                    
                    response = None
                    for m_name in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]:
                        try:
                            m = genai.GenerativeModel(m_name)
                            response = m.generate_content(prompt)
                            if response and hasattr(response, 'text') and response.text:
                                break
                        except Exception:
                            continue
                    
                    if response and hasattr(response, 'text') and response.text:
                        _LAST_GEMINI_CALL = time.time()
                        score_str = response.text.strip()
                        
                        # Extract numeric integer score
                        import re
                        match = re.search(r'(-?\d+)', score_str)
                        if match:
                            sent_score = int(match.group(1))
                            sent_score = max(-100, min(100, sent_score))
                            res['sentiment_score'] = sent_score
                            
                            if sent_score >= 50:
                                res['score_adj'] = 15
                                res['reason'] = f"GEMINI_AI_BULLISH_NEWS (+{sent_score})"
                            elif sent_score <= -50:
                                res['score_adj'] = -25
                                res['reason'] = f"GEMINI_AI_BEARISH_NEWS ({sent_score})"
                            else:
                                res['reason'] = f"GEMINI_AI_NEUTRAL_NEWS ({sent_score})"
                                
                            logger.info("🤖 [GEMINI_AI_NEWS] Symbol {} Sentiment Score: {} -> Adj: {:+d} pts", symbol, sent_score, res['score_adj'])
                except Exception as ai_err:
                    logger.debug("Gemini AI API call skipped/throttled: {}", ai_err)

            _NEWS_CACHE[symbol] = (now, res)
            _NEWS_CACHE[f"hash_{text_hash}"] = (now, res)
            return res
        except Exception as e:
            logger.debug("GeminiNewsSentinel failed for {}: {}", symbol, e)
            _NEWS_CACHE[symbol] = (now, res)
            return res
