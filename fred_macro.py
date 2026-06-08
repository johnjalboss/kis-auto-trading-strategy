import os
import time
import requests
import json
import pandas as pd
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

    def fetch_series_df(self, series_id: str, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch historical time series from FRED and return as a pandas DataFrame
        with Open/High/Low/Close/Adj Close/Volume columns to match yfinance format.
        """
        cache = self._load_cache()
        now = time.time()
        cache_key = f"{series_id}_history"
        
        # Check cache (24 hours)
        if cache_key in cache:
            entry = cache[cache_key]
            if now - entry.get("timestamp", 0) < 86400:
                logger.debug(f"FRED History Cache HIT: {series_id}")
                data_list = entry.get("data", [])
                if data_list:
                    return self._convert_to_df(data_list)
                    
        if not self.is_enabled():
            logger.warning(f"FRED_API_KEY is not configured. Cannot fetch history for {series_id}.")
            return pd.DataFrame()
            
        url = f"{self.base_url}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": limit,
            "sort_order": "desc"
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            observations = data.get("observations", [])
            
            # Save raw observation list to cache
            cache[cache_key] = {
                "timestamp": now,
                "data": observations
            }
            self._save_cache(cache)
            logger.info(f"FRED History API Fetch: {series_id} (items={len(observations)})")
            return self._convert_to_df(observations)
        except Exception as e:
            logger.error(f"FRED History API request failed for {series_id}: {e}")
            if cache_key in cache:
                return self._convert_to_df(cache[cache_key].get("data", []))
            return pd.DataFrame()

    def _convert_to_df(self, observations: list) -> pd.DataFrame:
        if not observations:
            return pd.DataFrame()
        dates = []
        values = []
        for obs in observations:
            val_str = obs.get("value", ".")
            if val_str != ".":
                try:
                    dates.append(obs.get("date"))
                    values.append(float(val_str))
                except ValueError:
                    pass
        if not dates:
            return pd.DataFrame()
            
        df = pd.DataFrame({'Close': values}, index=pd.to_datetime(dates))
        df.index.name = 'Date'
        # Sort ascending for technical analysis compatibility
        df = df.sort_index()
        df['Open'] = df['Close']
        df['High'] = df['Close']
        df['Low'] = df['Close']
        df['Adj Close'] = df['Close']
        df['Volume'] = 0.0
        return df

    def get_vix_history(self, days_back: int = 90) -> pd.DataFrame:
        """
        Get historical VIX index from FRED series VIXCLS
        """
        limit = int(days_back * 1.5)
        return self.fetch_series_df("VIXCLS", limit=limit)

    def analyze(self) -> Dict[str, Any]:
        """
        Analyze macro conditions based on 7 FRED macro indicators.
        Returns:
            Dict containing:
                score: -100 to +100 (Negative means macro risk, positive is favorable)
                t10y2y: yield spread value
                fedfunds: interest rate value
                dfii10: 10-year real yield
                m2_yoy: M2 Money Supply YoY% change
                credit_spread: BofA High Yield Credit Spread
                walcl_3mo: Fed Total Assets 3-month% change
                sentiment: Michigan Consumer Sentiment
                signals: list of active indicator flags
                reason: human-readable summary string
        """
        score = 0
        signals = []
        
        t10y2y = 0.0
        fedfunds = 5.0
        dfii10 = 1.0
        m2_yoy = 0.0
        credit_spread = 4.0
        walcl_3mo = 0.0
        sentiment = 70.0
        
        if not self.is_enabled():
            return {
                "score": 0,
                "t10y2y": 0.0,
                "fedfunds": 5.0,
                "dfii10": 1.0,
                "m2_yoy": 0.0,
                "credit_spread": 4.0,
                "walcl_3mo": 0.0,
                "sentiment": 70.0,
                "signals": ["FRED_KEY_MISSING"],
                "reason": "FRED API Key is not configured. Falling back to default risk profile."
            }
            
        try:
            # 1. 10Y-2Y Yield Spread (T10Y2Y)
            t10y2y = self._fetch_latest_observation("T10Y2Y")
            if t10y2y < 0:
                score -= 25
                signals.append("YIELD_CURVE_INVERTED")
            elif t10y2y < 0.2:
                score -= 10
                signals.append("YIELD_CURVE_FLAT")
            elif 0.2 <= t10y2y <= 1.5:
                score += 15
                signals.append("YIELD_CURVE_STEEP_HEALTHY")
            else:
                score += 5
                signals.append("YIELD_CURVE_STEEP_STRESS")
                
            # 2. Fed Funds Rate (FEDFUNDS)
            fedfunds = self._fetch_latest_observation("FEDFUNDS")
            if fedfunds > 5.0:
                score -= 15
                signals.append("RATES_HIGH")
            elif fedfunds < 2.0:
                score += 15
                signals.append("RATES_LOW_STIMULATIVE")
            else:
                score += 5
                signals.append("RATES_NEUTRAL")
                
            # 3. 10-Year Real Yield (DFII10)
            dfii10 = self._fetch_latest_observation("DFII10")
            if dfii10 > 2.0:
                score -= 15
                signals.append("REAL_YIELD_HIGH")
            elif dfii10 < 0.0:
                score += 15
                signals.append("REAL_YIELD_NEGATIVE")
            else:
                score += 5
                signals.append("REAL_YIELD_NEUTRAL")
                
            # 4. M2 Money Supply (M2SL) YoY
            m2_df = self.fetch_series_df("M2SL", limit=15)
            if len(m2_df) >= 12:
                latest_m2 = m2_df['Close'].iloc[-1]
                prev_m2 = m2_df['Close'].iloc[-12]
                m2_yoy = (latest_m2 / prev_m2) - 1.0
                if m2_yoy < 0.0:
                    score -= 15
                    signals.append("M2_CONTRACTING")
                elif m2_yoy > 0.05:
                    score += 15
                    signals.append("M2_EXPANDING")
                else:
                    score += 5
                    signals.append("M2_NEUTRAL")
            else:
                signals.append("M2_DATA_INSUFFICIENT")
                
            # 5. ICE BofA High Yield Spread (BAMLH0A0HYM2)
            credit_spread = self._fetch_latest_observation("BAMLH0A0HYM2")
            if credit_spread > 5.0:
                score -= 25
                signals.append("CREDIT_STRESS_HIGH")
            elif credit_spread > 4.0:
                score -= 10
                signals.append("CREDIT_STRESS_ELEVATED")
            elif credit_spread < 3.5:
                score += 15
                signals.append("CREDIT_STRESS_LOW")
            else:
                score += 5
                signals.append("CREDIT_STRESS_NEUTRAL")
                
            # 6. Federal Reserve Total Assets (WALCL) 3mo
            walcl_df = self.fetch_series_df("WALCL", limit=20)
            if len(walcl_df) >= 12:
                latest_walcl = walcl_df['Close'].iloc[-1]
                prev_walcl = walcl_df['Close'].iloc[-12] # ~12 weeks ago (approx 3 months)
                walcl_3mo = (latest_walcl / prev_walcl) - 1.0
                if walcl_3mo < 0.0:
                    score -= 10
                    signals.append("FED_QT_ACTIVE")
                else:
                    score += 15
                    signals.append("FED_QE_ACTIVE")
            else:
                signals.append("FED_ASSETS_INSUFFICIENT")
                
            # 7. Michigan Consumer Sentiment (UMCSENT)
            sentiment = self._fetch_latest_observation("UMCSENT")
            if sentiment < 60.0:
                score -= 15
                signals.append("CONSUMER_PESSIMISM")
            elif sentiment > 80.0:
                score += 15
                signals.append("CONSUMER_OPTIMISM")
            else:
                score += 5
                signals.append("CONSUMER_NEUTRAL")
                
        except Exception as e:
            logger.error(f"FRED macro analysis failed: {e}")
            return {
                "score": 0,
                "t10y2y": 0.0,
                "fedfunds": 5.0,
                "dfii10": 1.0,
                "m2_yoy": 0.0,
                "credit_spread": 4.0,
                "walcl_3mo": 0.0,
                "sentiment": 70.0,
                "signals": ["FRED_ANALYSIS_FAILED"],
                "reason": f"Error resolving FRED data: {e}"
            }
            
        # Clip score
        score = max(-100, min(100, score))
        
        reason = f"Yield Spread: {t10y2y:+.2f}%, Fed Funds: {fedfunds:.2f}%, Real Yield: {dfii10:.2f}%, M2 YoY: {m2_yoy*100:+.1f}%, Credit Spread: {credit_spread:.2f}%, Fed Assets 3mo: {walcl_3mo*100:+.1f}%, Consumer Sentiment: {sentiment:.1f}."
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
            "dfii10": dfii10,
            "m2_yoy": m2_yoy,
            "credit_spread": credit_spread,
            "walcl_3mo": walcl_3mo,
            "sentiment": sentiment,
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
