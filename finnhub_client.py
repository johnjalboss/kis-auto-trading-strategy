import os
import time
import requests
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "")
        self.base_url = "https://finnhub.io/api/v1"
        self._last_call_time = 0.0
        self._min_interval = 1.0  # Safe rate limit: 1s between calls (max 60/min)
        self._rate_limit_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self.cache_file = "finnhub_cache.json"
        self.cache = self._load_cache()

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def _load_cache(self) -> dict:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load Finnhub cache: {e}")
        return {"company-news": {}, "insider-transactions": {}, "earnings-surprises": {}}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Finnhub cache: {e}")

    def _get_cached(self, endpoint: str, symbol: str) -> Optional[list]:
        symbol = symbol.upper()
        category = endpoint
        if endpoint == "stock/insider-transactions":
            category = "insider-transactions"
        elif endpoint == "stock/earnings":
            category = "earnings-surprises"
        elif endpoint == "company-news":
            category = "company-news"
        
        # News TTL: 2 hours (7200s), Insider TTL: 12 hours (43200s), Earnings TTL: 24 hours (86400s)
        ttl = 7200
        if category == "insider-transactions":
            ttl = 43200
        elif category == "earnings-surprises":
            ttl = 86400

        with self._cache_lock:
            if category in self.cache and symbol in self.cache[category]:
                entry = self.cache[category][symbol]
                elapsed = time.time() - entry.get("timestamp", 0.0)
                if elapsed < ttl:
                    logger.debug("Finnhub Cache HIT: {} for {}, age={:.1f}s", category, symbol, elapsed)
                    return entry.get("data")
        return None

    def _set_cached(self, endpoint: str, symbol: str, data: list):
        symbol = symbol.upper()
        category = endpoint
        if endpoint == "stock/insider-transactions":
            category = "insider-transactions"
        elif endpoint == "stock/earnings":
            category = "earnings-surprises"
        elif endpoint == "company-news":
            category = "company-news"

        with self._cache_lock:
            if category not in self.cache:
                self.cache[category] = {}
            self.cache[category][symbol] = {
                "timestamp": time.time(),
                "data": data
            }
            self._save_cache()

    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        if not self.is_enabled():
            return None
        
        # Enforce thread-safe rate limiting
        with self._rate_limit_lock:
            elapsed = time.time() - self._last_call_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call_time = time.time()
            
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key
        
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 429:
                    logger.warning("Finnhub API Rate Limited (429). Retrying in 2s...")
                    time.sleep(2)
                    with self._rate_limit_lock:
                        self._last_call_time = time.time()
                    continue
                    
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Finnhub API request failed (endpoint={endpoint}, attempt={attempt+1}): {e}")
                time.sleep(1)
        return None

    def get_company_news(self, symbol: str, days_back: int = 7) -> list:
        """Fetch news for a symbol from a date range"""
        symbol = symbol.upper()
        cached = self._get_cached("company-news", symbol)
        if cached is not None:
            return cached
            
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        params = {
            "symbol": symbol,
            "from": from_date,
            "to": to_date
        }
        res = self._request("company-news", params)
        data = res if isinstance(res, list) else []
        self._set_cached("company-news", symbol, data)
        return data

    def get_insider_transactions(self, symbol: str) -> list:
        """Fetch insider transactions"""
        symbol = symbol.upper()
        cached = self._get_cached("stock/insider-transactions", symbol)
        if cached is not None:
            return cached

        params = {"symbol": symbol}
        res = self._request("stock/insider-transactions", params)
        data = []
        if res and isinstance(res, dict):
            data = res.get("data", [])
        self._set_cached("stock/insider-transactions", symbol, data)
        return data

    def get_earnings_surprises(self, symbol: str, limit: int = 4) -> list:
        """Fetch earnings surprises history"""
        symbol = symbol.upper()
        cached = self._get_cached("stock/earnings", symbol)
        if cached is not None:
            return cached

        params = {
            "symbol": symbol,
            "limit": limit
        }
        res = self._request("stock/earnings", params)
        data = res if isinstance(res, list) else []
        self._set_cached("stock/earnings", symbol, data)
        return data

_client = None
def get_finnhub_client() -> FinnhubClient:
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client

