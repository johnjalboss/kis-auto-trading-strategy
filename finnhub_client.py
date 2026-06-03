import os
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "")
        self.base_url = "https://finnhub.io/api/v1"
        self._last_call_time = 0
        self._min_interval = 1.0  # Safe rate limit: 1s between calls (max 60/min)

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        if not self.is_enabled():
            return None
        
        # Enforce local rate limiting to avoid HTTP 429
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
            
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key
        
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=10)
                self._last_call_time = time.time()
                
                if response.status_code == 429:
                    logger.warning("Finnhub API Rate Limited (429). Retrying in 2s...")
                    time.sleep(2)
                    continue
                    
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Finnhub API request failed (endpoint={endpoint}, attempt={attempt+1}): {e}")
                time.sleep(1)
        return None

    def get_company_news(self, symbol: str, days_back: int = 7) -> list:
        """Fetch news for a symbol from a date range"""
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        params = {
            "symbol": symbol.upper(),
            "from": from_date,
            "to": to_date
        }
        res = self._request("company-news", params)
        return res if isinstance(res, list) else []

    def get_insider_transactions(self, symbol: str) -> list:
        """Fetch insider transactions"""
        params = {"symbol": symbol.upper()}
        res = self._request("stock/insider-transaction", params)
        if res and isinstance(res, dict):
            return res.get("data", [])
        return []

    def get_earnings_surprises(self, symbol: str, limit: int = 4) -> list:
        """Fetch earnings surprises history"""
        params = {
            "symbol": symbol.upper(),
            "limit": limit
        }
        res = self._request("stock/earnings", params)
        return res if isinstance(res, list) else []

_client = None
def get_finnhub_client() -> FinnhubClient:
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client
