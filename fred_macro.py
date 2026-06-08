import os
import time
import requests
import json
from loguru import logger
from typing import Dict, Any

class FREDMacroAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY", "")
        self.base_url = "https://api.stlouisfed.org/fred"
        self.cache_file = "fred_cache.json"
        
    def is_enabled(self) -> bool:
        return bool(self.api_key)
        
    def _load_cache(self) -> dict:
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load FRED cache: {e}")
        return {}
        
    def _save_cache(self, cache: dict):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save FRED cache: {e}")
            
    def _fetch_latest_observation(self, series_id: str) -> float:
        """Fetch the single latest observation value for a given FRED series ID"""
        cache = self._load_cache()
        now = time.time()
        
        # 24-hour cache (86400 seconds)
        if series_id in cache:
            entry = cache[series_id]
            if now - entry.get("timestamp", 0) < 86400:
                logger.debug(f"FRED Cache HIT: {series_id} = {entry.get('value')}")
                return entry.get("value")
                
        if not self.is_enabled():
            raise ValueError("FRED_API_KEY is not configured.")
            
        url = f"{self.base_url}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": 1,
            "sort_order": "desc"
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            observations = data.get("observations", [])
            if observations:
                val_str = observations[0].get("value", ".")
                
                # Handle missing or holiday values represented as '.'
                if val_str == ".":
                    params["limit"] = 5
                    resp = requests.get(url, params=params, timeout=10)
                    data = resp.json()
                    for obs in data.get("observations", []):
                        if obs.get("value") != ".":
                            val_str = obs.get("value")
                            break
                            
                val = float(val_str)
                cache[series_id] = {
                    "timestamp": now,
                    "value": val
                }
                self._save_cache(cache)
                logger.info(f"FRED API Fetch: {series_id} = {val}")
                return val
        except Exception as e:
            logger.error(f"FRED API request failed for {series_id}: {e}")
            if series_id in cache:
                return cache[series_id].get("value")
                
        raise ValueError(f"Failed to fetch FRED data for {series_id}")

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze macro conditions based on FRED yield spread and rates.
        Returns:
            Dict containing:
                score: -100 to +100 (Negative means macro risk, positive is favorable)
                t10y2y: yield spread value
                fedfunds: interest rate value
                signals: list of active indicator flags
        """
        score = 0
        signals = []
        t10y2y = 0.0
        fedfunds = 5.0
        
        if not self.is_enabled():
            return {
                "score": 0,
                "t10y2y": 0.0,
                "fedfunds": 5.0,
                "signals": ["FRED_KEY_MISSING"],
                "reason": "FRED API Key is not configured. Falling back to default risk profile."
            }
            
        try:
            # 1. 10Y-2Y Yield Spread (T10Y2Y)
            t10y2y = self._fetch_latest_observation("T10Y2Y")
            if t10y2y < 0:
                # Yield curve inverted -> severe recession warning
                score -= 40
                signals.append("YIELD_CURVE_INVERTED")
            elif t10y2y < 0.2:
                score -= 15
                signals.append("YIELD_CURVE_FLAT")
            else:
                score += 15
                signals.append("YIELD_CURVE_STEEP_HEALTHY")
                
            # 2. Fed Funds Rate (FEDFUNDS)
            fedfunds = self._fetch_latest_observation("FEDFUNDS")
            if fedfunds > 5.0:
                # High interest rates -> contractionary, headwind for growth stocks
                score -= 20
                signals.append("RATES_HIGH")
            elif fedfunds < 2.0:
                score += 15
                signals.append("RATES_LOW_STIMULATIVE")
            else:
                score += 5
                signals.append("RATES_NEUTRAL")
                
        except Exception as e:
            logger.error(f"FRED macro analysis failed: {e}")
            return {
                "score": 0,
                "t10y2y": 0.0,
                "fedfunds": 5.0,
                "signals": ["FRED_ANALYSIS_FAILED"],
                "reason": f"Error resolving FRED data: {e}"
            }
            
        reason = f"Yield Spread: {t10y2y:+.2f}%, Fed Funds: {fedfunds:.2f}%."
        if score < -30:
            reason += " High macro risk detected."
        elif score < 0:
            reason += " Moderate macro headwind."
        else:
            reason += " Healthy macro environment."
            
        return {
            "score": score,
            "t10y2y": t10y2y,
            "fedfunds": fedfunds,
            "signals": signals,
            "reason": reason
        }

_analyzer = None
def get_fred_analyzer() -> FREDMacroAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = FREDMacroAnalyzer()
    return _analyzer

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print("Testing FREDMacroAnalyzer...")
    analyzer = get_fred_analyzer()
    res = analyzer.analyze()
    print(json.dumps(res, indent=2))
