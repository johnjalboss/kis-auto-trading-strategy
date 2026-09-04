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
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finnhub_cache.json")
        self.cache = self._load_cache()
        self._disabled_until = 0.0
        self._last_save_time = 0.0

    def is_enabled(self) -> bool:
        if not self.api_key:
            return False
        if time.time() < self._disabled_until:
            return False
        return True

    def _load_cache(self) -> dict:
        default_cache = {
            "company-news": {}, 
            "insider-transactions": {}, 
            "earnings-surprises": {},
            "basic-financials": {},
            "company-profile": {},
            "candles": {}
        }
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k in default_cache:
                            if k not in data:
                                data[k] = {}
                        return data
        except Exception as e:
            logger.warning(f"Finnhub cache corrupt/invalid ({e}) -> self-healing fresh cache initialized")
            try:
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
            except Exception:
                pass
        return default_cache

    def _prune_expired_entries(self):
        # Category TTLs
        ttls = {
            "company-news": 7200,
            "insider-transactions": 43200,
            "earnings-surprises": 86400,
            "basic-financials": 86400,
            "company-profile": 432000,
            "candles": 86400
        }
        now = time.time()
        for category, symbols in list(self.cache.items()):
            if not isinstance(symbols, dict):
                continue
            ttl = ttls.get(category, 86400)
            for symbol, entry in list(symbols.items()):
                # Keep expired entries up to 2x TTL to allow smooth restarts, prune everything older
                if now - entry.get("timestamp", 0.0) > ttl * 2:
                    del self.cache[category][symbol]

    def _save_cache(self, force: bool = False):
        try:
            with self._cache_lock:
                now = time.time()
                if not force and now - getattr(self, "_last_save_time", 0.0) < 10.0:
                    return
                self._last_save_time = now
                self._prune_expired_entries()
                
                # Atomic File Write to prevent JSON corruption during concurrent reads/writes
                temp_file = f"{self.cache_file}.{os.getpid()}.{threading.get_ident()}.tmp"
                os.makedirs(os.path.dirname(os.path.abspath(self.cache_file)), exist_ok=True)
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False)
                os.replace(temp_file, self.cache_file)
        except Exception as e:
            logger.error(f"Failed to atomically save Finnhub cache: {e}")

    def _get_cached(self, endpoint: str, symbol: str) -> Optional[list]:
        symbol = symbol.upper()
        category = endpoint
        if endpoint == "stock/insider-transactions":
            category = "insider-transactions"
        elif endpoint == "stock/earnings":
            category = "earnings-surprises"
        elif endpoint == "company-news":
            category = "company-news"
        elif endpoint == "stock/metric":
            category = "basic-financials"
        elif endpoint == "stock/profile2":
            category = "company-profile"
        elif endpoint in ["stock/candle", "crypto/candle", "forex/candle"]:
            category = "candles"
        
        # News TTL: 2 hours (7200s), Insider TTL: 12 hours (43200s), Earnings TTL: 24 hours (86400s)
        ttl = 7200
        if category == "insider-transactions":
            ttl = 43200
        elif category == "earnings-surprises":
            ttl = 86400
        elif category == "basic-financials":
            ttl = 86400
        elif category == "company-profile":
            ttl = 432000
        elif category == "candles":
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
        elif endpoint == "stock/metric":
            category = "basic-financials"
        elif endpoint == "stock/profile2":
            category = "company-profile"
        elif endpoint in ["stock/candle", "crypto/candle", "forex/candle"]:
            category = "candles"

        with self._cache_lock:
            if category not in self.cache:
                self.cache[category] = {}
            self.cache[category][symbol] = {
                "timestamp": time.time(),
                "data": data
            }
            self._save_cache(force=False)

    def flush_cache(self):
        with self._cache_lock:
            self._save_cache(force=True)

    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        if not self.is_enabled():
            return None
        if params and str(params.get("symbol", "")).startswith("^"):
            return None
        
        # Enforce thread-safe rate limiting (sleep outside the lock to prevent serializing parallel threads)
        sleep_time = 0.0
        with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self._last_call_time
            if elapsed < self._min_interval:
                sleep_time = self._min_interval - elapsed
                self._last_call_time = now + sleep_time
            else:
                self._last_call_time = now
        
        if sleep_time > 0.0:
            time.sleep(sleep_time)
            
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params['token'] = self.api_key
        
        for attempt in range(2):  # Reduced from 3→2 attempts: saves up to 11s on timeout
            try:
                # Reduced timeout 10s→5s: Finnhub is fast when reachable.
                # 5s is still generous; if it times out twice, the endpoint is down.
                response = requests.get(url, params=params, timeout=5)
                
                # Trip circuit breaker on Authentication failures (e.g. invalid key)
                if response.status_code in [401, 403]:
                    logger.error(f"Finnhub API Authentication Failed (HTTP {response.status_code}). Disabling Finnhub for 1 hour to protect latency.")
                    self._disabled_until = time.time() + 3600
                    return None

                if response.status_code == 429:
                    logger.warning("Finnhub API Rate Limited (429). Retrying in 2s...")
                    time.sleep(2)
                    with self._rate_limit_lock:
                        self._last_call_time = time.time()
                    continue
                    
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                logger.warning(f"Finnhub API timeout (endpoint={endpoint}, attempt={attempt+1}/2, limit=5s)")
                if attempt == 0:
                    time.sleep(0.5)  # Reduced from 1s to 0.5s between retries
            except Exception as e:
                logger.error(f"Finnhub API request failed (endpoint={endpoint}, attempt={attempt+1}): {e}")
                if attempt == 0:
                    time.sleep(0.5)
        
        # After 2 failed attempts, disable Finnhub for 5 minutes to prevent cascade
        logger.warning(f"Finnhub endpoint '{endpoint}' failed 2 times. Disabling for 5 min.")
        self._disabled_until = time.time() + 300
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

    def get_earnings_calendar(self, symbol: str, days_ahead: int = 14) -> list:
        """Fetch upcoming earnings calendar for symbol"""
        symbol = symbol.upper()
        cached = self._get_cached("calendar/earnings", symbol)
        if cached is not None:
            return cached

        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        params = {
            "symbol": symbol,
            "from": from_date,
            "to": to_date
        }
        res = self._request("calendar/earnings", params)
        data = []
        if res and isinstance(res, dict):
            data = res.get("earningsCalendar", [])
        self._set_cached("calendar/earnings", symbol, data)
        return data

    def get_basic_financials(self, symbol: str) -> Optional[dict]:
        """Fetch basic financials (metrics) for a symbol"""
        symbol = symbol.upper()
        cached = self._get_cached("stock/metric", symbol)
        if cached is not None:
            return cached

        params = {
            "symbol": symbol,
            "metric": "all"
        }
        res = self._request("stock/metric", params)
        data = res if isinstance(res, dict) else {}
        self._set_cached("stock/metric", symbol, data)
        return data

    def get_company_profile(self, symbol: str) -> Optional[dict]:
        """Fetch company profile for a symbol"""
        symbol = symbol.upper()
        cached = self._get_cached("stock/profile2", symbol)
        if cached is not None:
            return cached

        params = {"symbol": symbol}
        res = self._request("stock/profile2", params)
        data = res if isinstance(res, dict) else {}
        self._set_cached("stock/profile2", symbol, data)
        return data

    def get_candles(self, symbol: str, category: str = "stock", days_back: int = 90) -> Optional[dict]:
        """
        Fetch daily candles for a symbol under stock, crypto, or forex categories.
        """
        symbol = symbol.upper()
        endpoint = f"{category}/candle"
        
        cached = self._get_cached(endpoint, symbol)
        if cached is not None:
            return cached

        to_time = int(time.time())
        from_time = to_time - (days_back * 86400)
        
        params = {
            "symbol": symbol,
            "resolution": "D",
            "from": from_time,
            "to": to_time
        }
        
        res = self._request(endpoint, params)
        data = res if isinstance(res, dict) else {}
        
        if data and data.get("s") == "ok":
            self._set_cached(endpoint, symbol, data)
            return data
        
        return None

_client = None
def get_finnhub_client() -> FinnhubClient:
    global _client
    if _client is None:
        _client = FinnhubClient()
    return _client

