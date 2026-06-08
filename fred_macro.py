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
        
        # 7-day cache (604800 seconds) — survive API outages without falling blind
        if series_id in cache:
            entry = cache[series_id]
            if now - entry.get("timestamp", 0) < 604800:
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
        
        # Check cache (7 days)
        if cache_key in cache:
            entry = cache[cache_key]
            if now - entry.get("timestamp", 0) < 604800:
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
        Analyze macro conditions based on 10 FRED macro/market-stress indicators.
        Uses resilient individual try-except wrappers and blind-penalty circuit breaker.
        Returns:
            Dict containing scores and each sub-indicator value
        """
        score = 0
        signals = []
        success_count = 0
        
        t10y2y = 0.0
        t10y3m = 0.0
        fedfunds = 5.0
        dfii10 = 1.0
        m2_yoy = 0.0
        credit_spread = 4.0
        walcl_3mo = 0.0
        sentiment = 70.0
        financial_stress = 0.0
        sahm_recession = 0.0
        
        if not self.is_enabled():
            policy = os.getenv("MACRO_BLIND_POLICY", "PENALTY").upper()
            score_fallback = -25
            if policy == "BLOCK":
                score_fallback = -100
            elif policy == "NEUTRAL":
                score_fallback = 0

            return {
                "score": score_fallback,
                "t10y2y": 0.0,
                "t10y3m": 0.0,
                "fedfunds": 5.0,
                "dfii10": 1.0,
                "m2_yoy": 0.0,
                "credit_spread": 4.0,
                "walcl_3mo": 0.0,
                "sentiment": 70.0,
                "financial_stress": 0.0,
                "sahm_recession": 0.0,
                "signals": ["FRED_KEY_MISSING", f"MACRO_BLIND_{policy}"],
                "reason": f"FRED API Key is not configured. Fallback to {policy} policy (score={score_fallback})."
            }

        # ── Pre-warm cache for auxiliary series ──────────────────────────
        # VIXCLS and T10Y3M_history are fetched by vix_structure.py and
        # other modules. Pre-warming here ensures they are always cached
        # so downstream modules get instant cache hits (< 1ms).
        try:
            self.fetch_series_df("VIXCLS", limit=130)    # ~6 months daily VIX
        except Exception:
            pass
        try:
            self.fetch_series_df("T10Y3M", limit=70)     # 10Y-3M spread history
        except Exception:
            pass

            
        # 1. 10Y-2Y Yield Spread (T10Y2Y) & Un-inversion Velocity
        try:
            t10y2y = self._fetch_latest_observation("T10Y2Y")
            success_count += 1
            
            t10y2y_df = self.fetch_series_df("T10Y2Y", limit=70)
            t10y2y_change_90d = 0.0
            if len(t10y2y_df) >= 60:
                t10y2y_change_90d = t10y2y_df['Close'].iloc[-1] - t10y2y_df['Close'].iloc[-60]
                
            fedfunds_df = self.fetch_series_df("FEDFUNDS", limit=5)
            fedfunds_change_3mo = 0.0
            if len(fedfunds_df) >= 3:
                fedfunds_change_3mo = fedfunds_df['Close'].iloc[-1] - fedfunds_df['Close'].iloc[-3]
                
            if t10y2y_change_90d > 0.5 and t10y2y >= 0.0 and fedfunds_change_3mo < 0.0:
                score -= 30
                signals.append("RECESSION_UNINVERSION_STEEP")
            elif t10y2y < 0:
                score -= 20
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
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch T10Y2Y: {e}")
            signals.append("T10Y2Y_FETCH_FAILED")
            
        # 2. 10Y-3M Yield Spread (T10Y3M)
        try:
            t10y3m = self._fetch_latest_observation("T10Y3M")
            success_count += 1
            if t10y3m < 0:
                score -= 15
                signals.append("T10Y3M_INVERTED")
            elif t10y3m < 0.2:
                score -= 5
                signals.append("T10Y3M_FLAT")
            else:
                score += 10
                signals.append("T10Y3M_STEEP_HEALTHY")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch T10Y3M: {e}")
            signals.append("T10Y3M_FETCH_FAILED")

        # 3. Fed Funds Rate (FEDFUNDS)
        try:
            fedfunds = self._fetch_latest_observation("FEDFUNDS")
            success_count += 1
            if fedfunds > 5.0:
                score -= 15
                signals.append("RATES_HIGH")
            elif fedfunds < 2.0:
                score += 15
                signals.append("RATES_LOW_STIMULATIVE")
            else:
                score += 5
                signals.append("RATES_NEUTRAL")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch FEDFUNDS: {e}")
            signals.append("FEDFUNDS_FETCH_FAILED")
            
        # 4. 10-Year Real Yield (DFII10)
        try:
            dfii10 = self._fetch_latest_observation("DFII10")
            success_count += 1
            if dfii10 > 2.0:
                score -= 20
                signals.append("REAL_YIELD_HIGH")
            elif dfii10 < 0.0:
                score += 10
                signals.append("REAL_YIELD_NEGATIVE")
            elif 0.0 <= dfii10 <= 1.5:
                score += 15
                signals.append("REAL_YIELD_GOLDILOCKS")
            else:
                score += 5
                signals.append("REAL_YIELD_NEUTRAL")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch DFII10: {e}")
            signals.append("DFII10_FETCH_FAILED")
            
        # 5. M2 Money Supply (M2SL)
        try:
            m2_df = self.fetch_series_df("M2SL", limit=15)
            if len(m2_df) >= 12:
                success_count += 1
                latest_m2 = m2_df['Close'].iloc[-1]
                prev_m2 = m2_df['Close'].iloc[-12]
                m2_yoy = (latest_m2 / prev_m2) - 1.0
                if m2_yoy < 0.0:
                    score -= 20
                    signals.append("M2_CONTRACTING")
                elif 0.02 <= m2_yoy <= 0.07:
                    score += 15
                    signals.append("M2_HEALTHY_GROWTH")
                elif m2_yoy > 0.10:
                    score -= 10
                    signals.append("M2_OVEREXPANSION_INFLATION")
                else:
                    score += 5
                    signals.append("M2_NEUTRAL")
            else:
                signals.append("M2_DATA_INSUFFICIENT")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch M2SL: {e}")
            signals.append("M2SL_FETCH_FAILED")
            
        # 6. ICE BofA High Yield Spread (BAMLH0A0HYM2)
        try:
            credit_spread = self._fetch_latest_observation("BAMLH0A0HYM2")
            success_count += 1
            
            credit_df = self.fetch_series_df("BAMLH0A0HYM2", limit=30)
            credit_change_30d = 0.0
            if len(credit_df) >= 20:
                credit_change_30d = credit_df['Close'].iloc[-1] - credit_df['Close'].iloc[-20]
                
            if credit_spread > 5.0:
                score -= 30
                signals.append("CREDIT_STRESS_HIGH")
            elif credit_spread > 4.0 and credit_change_30d > 0.5:
                score -= 25
                signals.append("CREDIT_STRESS_SPIKE")
            elif credit_spread < 3.5:
                score += 15
                signals.append("CREDIT_STRESS_LOW")
            else:
                score += 5
                signals.append("CREDIT_STRESS_NEUTRAL")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch BAMLH0A0HYM2: {e}")
            signals.append("BAMLH0A0HYM2_FETCH_FAILED")
            
        # 7. Federal Reserve Total Assets (WALCL)
        try:
            walcl_df = self.fetch_series_df("WALCL", limit=20)
            if len(walcl_df) >= 12:
                success_count += 1
                latest_walcl = walcl_df['Close'].iloc[-1]
                prev_walcl = walcl_df['Close'].iloc[-12]
                walcl_3mo = (latest_walcl / prev_walcl) - 1.0
                if walcl_3mo < -0.015:
                    score -= 15
                    signals.append("FED_QT_STRONG")
                elif walcl_3mo < 0.0:
                    score -= 5
                    signals.append("FED_QT_MILD")
                else:
                    score += 15
                    signals.append("FED_QE_ACTIVE")
            else:
                signals.append("FED_ASSETS_INSUFFICIENT")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch WALCL: {e}")
            signals.append("WALCL_FETCH_FAILED")
            
        # 8. Michigan Consumer Sentiment (UMCSENT)
        try:
            sentiment = self._fetch_latest_observation("UMCSENT")
            success_count += 1
            if sentiment < 55.0:
                score -= 10
                signals.append("CONSUMER_PESSIMISM")
            elif sentiment > 75.0:
                score += 10
                signals.append("CONSUMER_OPTIMISM")
            else:
                score += 5
                signals.append("CONSUMER_NEUTRAL")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch UMCSENT: {e}")
            signals.append("UMCSENT_FETCH_FAILED")
            
        # 9. St. Louis Fed Financial Stress Index (STLFSI4)
        try:
            financial_stress = self._fetch_latest_observation("STLFSI4")
            success_count += 1
            if financial_stress > 1.0:
                score -= 30
                signals.append("FINANCIAL_STRESS_SEVERE")
            elif financial_stress > 0.0:
                score -= 10
                signals.append("FINANCIAL_STRESS_ELEVATED")
            elif financial_stress < -0.5:
                score += 10
                signals.append("FINANCIAL_STRESS_VERY_LOW")
            else:
                score += 5
                signals.append("FINANCIAL_STRESS_NORMAL")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch STLFSI4: {e}")
            signals.append("STLFSI4_FETCH_FAILED")
            
        # 10. Sahm Rule Recession Indicator (SAHMREALTIME)
        try:
            sahm_recession = self._fetch_latest_observation("SAHMREALTIME")
            success_count += 1
            if sahm_recession >= 0.5:
                score -= 30
                signals.append("SAHM_RECESSION_ACTIVE")
            elif sahm_recession >= 0.3:
                score -= 10
                signals.append("SAHM_RECESSION_ALERT")
            else:
                score += 10
                signals.append("SAHM_SAFE_ZONE")
        except Exception as e:
            logger.warning(f"FRED analyze: failed to fetch SAHMREALTIME: {e}")
            signals.append("SAHMREALTIME_FETCH_FAILED")
            
        # Circuit Breaker: If we failed to get at least 7 indicators, apply MACRO_BLIND_POLICY
        if success_count < 7:
            policy = os.getenv("MACRO_BLIND_POLICY", "PENALTY").upper()
            if policy == "BLOCK":
                score = -100
            elif policy == "NEUTRAL":
                score = 0
            else:  # PENALTY (default)
                score = -25
            signals.append(f"MACRO_BLIND_{policy}")
            logger.error(
                f"FRED macro blind circuit breaker tripped: Only {success_count}/10 indicators succeeded. "
                f"Policy={policy}, score={score}."
            )
            reason = (
                f"Macro Blind! Only {success_count}/10 macro indicators resolved. "
                f"Policy={policy} → score={score}. "
                f"Partial signals: {', '.join(signals[:-1]) if len(signals) > 1 else 'none'}."
            )
        else:
            # Clip score
            score = max(-100, min(100, score))
            
            reason = (f"Yield Spread 10Y-2Y: {t10y2y:+.2f}%, 10Y-3M: {t10y3m:+.2f}%, Fed Funds: {fedfunds:.2f}%, "
                      f"Real Yield: {dfii10:.2f}%, M2 YoY: {m2_yoy*100:+.1f}%, Credit Spread: {credit_spread:.2f}%, "
                      f"Fed Assets 3mo: {walcl_3mo*100:+.1f}%, Consumer Sentiment: {sentiment:.1f}, "
                      f"Financial Stress Index: {financial_stress:.2f}, Sahm Indicator: {sahm_recession:.2f}.")
                      
            if score < -30:
                reason += " High macro risk detected."
            elif score < 0:
                reason += " Moderate macro headwind."
            else:
                reason += " Healthy macro environment."
            
        return {
            "score": score,
            "t10y2y": t10y2y,
            "t10y3m": t10y3m,
            "fedfunds": fedfunds,
            "dfii10": dfii10,
            "m2_yoy": m2_yoy,
            "credit_spread": credit_spread,
            "walcl_3mo": walcl_3mo,
            "sentiment": sentiment,
            "financial_stress": financial_stress,
            "sahm_recession": sahm_recession,
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
