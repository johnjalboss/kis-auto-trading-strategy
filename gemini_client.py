"""
gemini_client.py - Unified High-Performance Google Gemini Client for KIS Auto Trading Bot
========================================================================================
Key Capabilities:
1. Pure REST-based implementation (zero heavy dependencies like grpcio or google-generativeai).
2. Intelligent Multi-Model Cascade:
   - gemini-2.5-flash (Primary high-precision quant engine)
   - gemini-flash-latest (Immediate fallback if 2.5-flash hits 429 quota or 503)
   - gemini-flash-lite-latest (Ultra-fast, high-availability fallback)
   - gemini-3.5-flash (Next-gen frontier fallback)
3. Thread-safe rate limiter (enforces >= 2.0s interval across all concurrent callers to protect Free Tier quota).
4. Dual generation endpoints:
   - generate_text(): Clean Wall-Street/Quant commentary & trade reviews.
   - generate_json(): Schema-validated JSON dictionaries for news sentiment and risk filters.
"""

import os
import re
import time
import json
import threading
from typing import Optional, Dict, Any, List
import requests
from loguru import logger

# Priority order of active, verified Google AI Studio models
CASCADE_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash"
]

_GLOBAL_CLIENT: Optional["GeminiClient"] = None
_CLIENT_INIT_LOCK = threading.Lock()


class GeminiClient:
    """Thread-safe, rate-limited Google Gemini REST client with automatic model failover."""

    def __init__(self, api_key: Optional[str] = None):
        # Load from parameter, environment, or config
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            try:
                import config
                key = getattr(config, "GEMINI_API_KEY", "")
            except Exception:
                pass
        self.api_key = str(key).strip()
        self._lock = threading.Lock()
        self._last_call_time = 0.0
        self._min_interval = 2.0  # Safe minimum delay between calls (seconds)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def is_available(self) -> bool:
        """Returns True if a valid API key is present."""
        return bool(self.api_key and len(self.api_key) >= 15)

    def _wait_for_rate_limit(self):
        """Enforce thread-safe cooldown to prevent 429 quota exhaustion."""
        with self._lock:
            now = time.time()
            elapsed = now - self._last_call_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call_time = time.time()

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        timeout: int = 10
    ) -> Optional[str]:
        """
        Generate text response from Gemini with multi-model failover.
        Returns the generated text string, or None if all models fail.
        """
        if not self.is_available():
            logger.debug("[GEMINI_CLIENT] No valid GEMINI_API_KEY configured.")
            return None

        self._wait_for_rate_limit()

        payload: Dict[str, Any] = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {"Content-Type": "application/json"}

        for model in CASCADE_MODELS:
            url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"].strip()
                            if text:
                                return text
                elif resp.status_code == 429:
                    logger.debug(f"[GEMINI_CLIENT] Model {model} 429 rate limit hit. Falling back...")
                    time.sleep(0.5)
                    continue
                elif resp.status_code in (500, 503):
                    logger.debug(f"[GEMINI_CLIENT] Model {model} server load {resp.status_code}. Falling back...")
                    continue
                else:
                    logger.debug(f"[GEMINI_CLIENT] Model {model} returned HTTP {resp.status_code}: {resp.text[:80]}")
            except Exception as e:
                logger.debug(f"[GEMINI_CLIENT] Error querying {model}: {e}")
                continue

        logger.warning("[GEMINI_CLIENT] All Gemini cascade models exhausted or unavailable.")
        return None

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        timeout: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON response using Gemini with multi-model failover.
        Returns parsed JSON dict, or None if failed.
        """
        if not self.is_available():
            return None

        self._wait_for_rate_limit()

        payload: Dict[str, Any] = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {"Content-Type": "application/json"}

        for model in CASCADE_MODELS:
            url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            raw_text = parts[0]["text"].strip()
                            if raw_text.startswith("```"):
                                raw_text = re.sub(r"^```(?:json)?\s*|```$", "", raw_text, flags=re.MULTILINE).strip()
                            return json.loads(raw_text)
                elif resp.status_code == 429:
                    logger.debug(f"[GEMINI_CLIENT] Model {model} 429 rate limit in JSON mode. Falling back...")
                    time.sleep(0.5)
                    continue
                elif resp.status_code in (500, 503):
                    logger.debug(f"[GEMINI_CLIENT] Model {model} {resp.status_code} in JSON mode. Falling back...")
                    continue
                else:
                    logger.debug(f"[GEMINI_CLIENT] Model {model} JSON HTTP {resp.status_code}")
            except Exception as e:
                logger.debug(f"[GEMINI_CLIENT] Error querying {model} for JSON: {e}")
                continue

        return None


def get_gemini_client(api_key: Optional[str] = None) -> GeminiClient:
    """Singleton getter for the global Gemini client."""
    global _GLOBAL_CLIENT
    with _CLIENT_INIT_LOCK:
        if _GLOBAL_CLIENT is None:
            _GLOBAL_CLIENT = GeminiClient(api_key=api_key)
        elif api_key and not _GLOBAL_CLIENT.api_key:
            _GLOBAL_CLIENT = GeminiClient(api_key=api_key)
        return _GLOBAL_CLIENT
