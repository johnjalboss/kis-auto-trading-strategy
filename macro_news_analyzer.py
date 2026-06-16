"""
Macro & Geopolitical News Sentiment Analyzer
==============================================
Analyzes global market and geopolitical news headlines using either
Gemini LLM (if API key is present) or a robust rule-based keyword engine.
Updates overall macro risk levels for the trading bot.
"""

import os
import json
import requests
from datetime import datetime
from loguru import logger
from typing import List, Dict, Optional

class MacroNewsAnalyzer:
    # Class-level cache to conserve API quota across dynamic instance creations
    _cache: Optional[Dict] = None
    _last_checked: Optional[datetime] = None
    _cache_ttl = 600  # 10 minutes (Optimized for real-time responsiveness within Free Tier limits)

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.multiplier = self._load_config()
        
    def _load_config(self) -> float:
        try:
            config_path = os.path.join(os.path.dirname(__file__), "macro_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = float(data.get("news_sensitivity_multiplier", 1.0))
                    logger.info("[MACRO_NEWS] Loaded news_sensitivity_multiplier: {}", val)
                    return val
        except Exception as e:
            logger.warning("[MACRO_NEWS] Failed to load macro_config.json: {}", e)
        return 1.0

    def _fetch_general_news(self) -> List[Dict]:
        """Fetch general market news from Finnhub API"""
        try:
            from finnhub_client import get_finnhub_client
            fh = get_finnhub_client()
            if fh.is_enabled():
                # Finnhub general news category
                res = fh._request("news", {"category": "general"})
                return res if isinstance(res, list) else []
        except Exception as e:
            logger.warning(f"[MACRO_NEWS] Finnhub general news fetch failed: {e}")
        return []

    def _analyze_with_gemini(self, headlines: List[str]) -> Optional[Dict]:
        """Use Gemini to analyze global macro news sentiment and identify scheduled/unscheduled events"""
        if not self.gemini_key:
            return None
            
        prompt = (
            "You are a world-class macroeconomic analyst and geopolitical risk monitor.\n"
            "Analyze the following recent global financial and political headlines by dynamically clustering them into major topics.\n"
            "Evaluate the economic transmission path of each major topic, focusing on:\n"
            "1. Supply chain & trade route disruption (e.g., Strait of Hormuz, Red Sea, major port shut downs/strikes).\n"
            "2. Critical energy/commodity shock (e.g., crude oil, natural gas, lithium, coal supply bottlenecks).\n"
            "3. High-tech component bottleneck (e.g., Taiwan Strait tensions affecting semiconductor supply).\n"
            "4. Central bank monetary policy shock (inflation spikes, hawkish FOMC rate decisions).\n\n"
            "Note:\n"
            "- Fully discount long-standing, pre-priced-in conflicts like the Russia-Ukraine war unless a dramatic expansion occurs (give it minimal risk weight like 0 to 5).\n"
            "- Highly penalize sudden disruptions that directly jeopardize global energy hubs or vital supply trade routes.\n\n"
            "Headlines:\n"
            + "\n".join(f"- {h}" for h in headlines) + "\n\n"
            "Provide your assessment in strict JSON format with the following keys:\n"
            "- 'risk_level': one of 'LOW', 'ELEVATED', 'HIGH', 'EXTREME'.\n"
            "- 'penalty': an integer between -20 and 50 representing the impact on the trading bot's macro risk score.\n"
            "- 'events_identified': a list of major identified events/topics (e.g., ['Hormuz Shipping Threat', 'Fed Hawkish Shift']).\n"
            "- 'reason': a short summary explaining the logic behind the penalty (under 120 characters).\n\n"
            "Output JSON only (no markdown block, no ```json):"
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
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
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                res_json = resp.json()
                text = res_json['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(text.strip())
                logger.info("[MACRO_NEWS_GEMINI] Risk Level: {}, Penalty: {}, Reason: {}", 
                            data.get("risk_level"), data.get("penalty"), data.get("reason"))
                return data
        except Exception as e:
            logger.warning(f"[MACRO_NEWS_GEMINI] Gemini analysis failed: {e}")
        return None

    def _analyze_rule_based(self, headlines: List[str]) -> Dict:
        """Quant-weighted rule-based keyword sentiment analyzer for macro news"""
        logger.info("[MACRO_NEWS] Executing Quant-weighted macro news analysis")
        
        # 퀀트 가중치 사전 정의 (단어별 영향력 점수 세분화)
        # 긍정 수치는 리스크 증가(페널티 상승), 부정 수치는 리스크 감소(페널티 하락/시장 안정)
        WEIGHTS = {
            # 지정학적 갈등 (공포 및 실질 위협 요인 분리)
            # 고위험 중동/물류 요충지 (에너지/물류 쇼크 연계)
            'iran': 15.0, 'israel': 15.0, 'lebanon': 12.0, 'hezbollah': 12.0, 
            'hormuz': 18.0, 'red sea': 10.0, 'gaza': 8.0, 'yemen': 8.0, 'houthi': 8.0,
            
            # 선반영된 지정학적 갈등 (우크라이나/러시아 등 저위험)
            'russia': 3.0, 'ukraine': 3.0, 'putin': 3.0,
            
            # 기타 지정학 단어
            'war': 8.0, 'conflict': 5.0, 'bomb': 8.0, 'missile': 8.0, 
            'airstrike': 7.0, 'invasion': 10.0, 'sanction': 6.0, 'tariff': 8.0, 
            'escalat': 5.0, 'attack': 6.0, 'tension': 4.0, 'military': 4.0,
            
            # 평화 / 완화 (안정 요인)
            'ceasefire': -20.0, 'peace agreement': -20.0, 'peace treaty': -25.0, 
            'diplomatic resolution': -15.0, 'peace talk': -10.0, 'accord': -12.0, 
            'de-escalat': -12.0, 'negotiation success': -15.0, 'peace': -10.0,
            
            # 중앙은행 통화정책 및 거시 경제 (변동성 요인)
            'fomc': 8.0, 'rate hike': 12.0, 'fed hike': 12.0, 'hawkish': 10.0, 
            'tightening': 10.0, 'powell hawkish': 15.0, 'boj': 8.0, 'bank of japan': 8.0, 
            'interest rate': 6.0, 'rate cut': -8.0, 'central bank': 5.0, 'fed decision': 8.0, 
            'ecb': 6.0, 'inflation': 10.0, 'cpi': 10.0, 'pce': 8.0, 'recession': 15.0
        }
        
        risk_score = 0.0
        events = []
        conflict_count = 0
        peace_count = 0
        fed_count = 0
        
        # 헤드라인 별로 가중치 매칭 수행 (대소문자 구분 없음 - 키워드별 단 1회만 가중치 적용되도록 중복 방지)
        matched_words = set()
        for h in headlines:
            h_lower = h.lower()
            for word, weight in WEIGHTS.items():
                if word in h_lower and word not in matched_words:
                    risk_score += weight
                    matched_words.add(word)
                    # 통계용 카운트
                    if weight >= 10.0:
                        conflict_count += 1
                        if "Geopolitical Risk" not in events:
                            events.append("Geopolitical Risk")
                    elif weight <= -15.0:
                        peace_count += 1
                        if "Ceasefire/Peace Relief" not in events:
                            events.append("Ceasefire/Peace Relief")
                    elif abs(weight) >= 8.0 and word in ['fomc', 'rate hike', 'powell', 'boj', 'central bank', 'inflation', 'cpi', 'rate cut']:
                        fed_count += 1
                        if "Central Bank Policy" not in events:
                            events.append("Central Bank Policy")

        # 페널티 범위 제한 (-20 ~ 50)
        risk_score = max(-20.0, min(50.0, risk_score))
        
        # Classify risk level
        if risk_score >= 30:
            level = "HIGH"
        elif risk_score >= 10:
            level = "ELEVATED"
        elif risk_score <= -10:
            level = "LOW"
        else:
            level = "NEUTRAL"
            
        reason = f"Quant Score: {risk_score:.1f} (Geo: {conflict_count}, Peace: {peace_count}, Econ: {fed_count})"
        
        return {
            "risk_level": level if level != "NEUTRAL" else "LOW",
            "penalty": int(risk_score),
            "events_identified": events,
            "reason": reason
        }

    def analyze(self) -> Dict:
        """Perform macro news sentiment analysis and return penalty and metadata"""
        # 30-minute class-level cache check
        if MacroNewsAnalyzer._cache and MacroNewsAnalyzer._last_checked:
            elapsed = (datetime.now() - MacroNewsAnalyzer._last_checked).total_seconds()
            if elapsed < MacroNewsAnalyzer._cache_ttl:
                logger.debug("[MACRO_NEWS] Returning cached macro news analysis (Age: {:.1f}s)", elapsed)
                return MacroNewsAnalyzer._cache

        raw_news = self._fetch_general_news()
        if not raw_news:
            logger.info("[MACRO_NEWS] No general news found. Returning default neutral.")
            return {
                "risk_level": "LOW",
                "penalty": 0,
                "events_identified": [],
                "reason": "No news fetched"
            }
            
        headlines = [item.get('headline', '') for item in raw_news if item.get('headline', '')]
        headlines = headlines[:40] # Expanded to Top 40 headlines to ensure no critical macro announcements are missed
        
        # Try Gemini first
        result = self._analyze_with_gemini(headlines)
        if not result:
            # Fallback to rule-based
            result = self._analyze_rule_based(headlines)
            
        # Apply self-tuning sensitivity multiplier
        raw_penalty = result.get("penalty", 0)
        adjusted_penalty = int(raw_penalty * self.multiplier)
        adjusted_penalty = max(-20, min(50, adjusted_penalty))
        
        result["penalty"] = adjusted_penalty
        result["raw_penalty"] = raw_penalty
        result["sensitivity_multiplier"] = self.multiplier
        
        # Update class-level cache
        MacroNewsAnalyzer._cache = result
        MacroNewsAnalyzer._last_checked = datetime.now()
        
        return result

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Testing MacroNewsAnalyzer...")
    analyzer = MacroNewsAnalyzer()
    res = analyzer.analyze()
    print("Result:", res)
