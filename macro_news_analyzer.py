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
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        
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
            "Analyze the following recent global financial and political headlines.\n"
            "Evaluate:\n"
            "1. Geopolitical risk level (e.g., escalating war/tensions vs. ceasefires/peace treaties like an Iran peace agreement).\n"
            "2. Central bank policy risk (e.g., upcoming FOMC meetings, hawkish rate hikes vs. dovish cuts).\n"
            "3. Macro economic shocks (inflation, currency crises, energy supply cuts).\n\n"
            "Headlines:\n"
            + "\n".join(f"- {h}" for h in headlines) + "\n\n"
            "Provide your assessment in strict JSON format with the following keys:\n"
            "- 'risk_level': one of 'LOW', 'ELEVATED', 'HIGH', 'EXTREME'.\n"
            "- 'penalty': an integer between -20 and 50 representing the impact on the trading bot's macro risk score (negative for peace/bullish, positive for tensions/bearish).\n"
            "- 'events_identified': a list of major identified events (e.g., ['Upcoming FOMC', 'Iran Peace Agreement']).\n"
            "- 'reason': a short summary under 120 characters.\n\n"
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
            # 지정학적 갈등 (공포 요인)
            'war': 15.0, 'conflict': 8.0, 'bomb': 12.0, 'missile': 12.0, 
            'airstrike': 10.0, 'invasion': 15.0, 'sanction': 8.0, 'tariff': 10.0, 
            'escalat': 7.0, 'attack': 8.0, 'tension': 5.0, 'military': 6.0,
            
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
        
        # 헤드라인 별로 가중치 매칭 수행 (대소문자 구분 없음)
        for h in headlines:
            h_lower = h.lower()
            for word, weight in WEIGHTS.items():
                if word in h_lower:
                    risk_score += weight
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
        headlines = headlines[:15] # Top 15 headlines
        
        # Try Gemini first
        gemini_result = self._analyze_with_gemini(headlines)
        if gemini_result:
            return gemini_result
            
        # Fallback to rule-based
        return self._analyze_rule_based(headlines)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Testing MacroNewsAnalyzer...")
    analyzer = MacroNewsAnalyzer()
    res = analyzer.analyze()
    print("Result:", res)
