"""
news_catalyst_radar.py
================================================================================
Real-Time News Catalyst & Sentiment Radar
- Searches and extracts market-moving news catalysts for leading stocks & themes
- Identifies critical institutional keywords:
  (FDA 승인, 국방부/방산 계약, 실적 가이던스 상향, AI 파트너십, M&A 인수합병, 반독점 등)
- Injects real fundamental catalysts into Telegram alerts and trade journals
================================================================================
"""

import os
import requests
import datetime
from typing import Dict, List, Any, Optional
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HIGH_IMPACT_KEYWORDS = {
    "fda": "💊 FDA 승인 / 임상 결과",
    "contract": "🎖 국방부 / 대규모 공급 계약",
    "guidance": "📈 실적 가이던스 상향",
    "earnings": "💰 실적 어닝 서프라이즈",
    "partnership": "🤝 글로벌 빅테크 파트너십",
    "acquisition": "🏢 M&A 인수합병",
    "upgrade": "⭐️ 월가 IB 투자의견 상향",
    "patent": "📜 핵심 특허 취득",
    "ai": "🤖 차세대 AI 인프라 수혜"
}

class NewsCatalystRadar:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("FINNHUB_API_KEY")
        if not self.api_key:
            env_candidates = [
                os.path.join(BASE_DIR, ".env"),
                "/home/ubuntu/kis-auto-trading/.env"
            ]
            for ec in env_candidates:
                if os.path.exists(ec):
                    with open(ec, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("FINNHUB_API_KEY="):
                                self.api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                                break

    def get_stock_catalyst(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches top recent news headline and identifies catalyst category."""
        if not self.api_key:
            return None

        try:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            past_str = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={past_str}&to={today_str}&token={self.api_key}"
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                news_items = resp.json()
                if news_items and isinstance(news_items, list):
                    for item in news_items[:5]:
                        headline = item.get("headline", "")
                        summary = item.get("summary", "")
                        combined = (headline + " " + summary).lower()

                        detected_cat = "📰 주요 언론 보도"
                        for kw, label in HIGH_IMPACT_KEYWORDS.items():
                            if kw in combined:
                                detected_cat = label
                                break

                        return {
                            "symbol": symbol,
                            "headline": headline,
                            "category": detected_cat,
                            "source": item.get("source", "Finnhub"),
                            "url": item.get("url", "")
                        }
        except Exception as e:
            logger.debug("Finnhub news query error for {}: {}", symbol, e)
        return None

if __name__ == "__main__":
    radar = NewsCatalystRadar()
    print("Testing Catalyst Radar for NVDA:", radar.get_stock_catalyst("NVDA"))
