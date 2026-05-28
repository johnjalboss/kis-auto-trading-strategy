"""
AutoAuth - Automatic Token Management for 24/7 Operation
Refreshes KIS API tokens every 12 hours
"""

import json
import threading
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

import config


class AutoAuth:
    """Automatic token management with 12-hour refresh cycle"""
    
    def __init__(self):
        self.token_path = Path(config.TOKEN_FILE)
        self.base_url = config.BASE_URL
        self.app_key = config.KIS_APP_KEY
        self.app_secret = config.KIS_APP_SECRET
        self._token_data = None
        self._lock = threading.Lock()
        self._refresh_thread = None
        self._running = False
        
    def start(self):
        """Start automatic token refresh thread"""
        self._running = True
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("AutoAuth started (refresh every {}h)", config.TOKEN_REFRESH_HOURS)
        
    def stop(self):
        """Stop automatic token refresh"""
        self._running = False
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("AutoAuth stopped")
        
    def _refresh_loop(self):
        """Background thread for periodic token refresh"""
        while self._running:
            try:
                self._ensure_valid_token()
            except Exception as e:
                logger.error("Token refresh error: {}", e)
            
            # Sleep for refresh interval
            time.sleep(config.TOKEN_REFRESH_HOURS * 3600)
    
    def get_token(self) -> str:
        """Get valid access token (thread-safe)
        
        Validates token before returning, refreshes if needed.
        
        Returns:
            str: Valid access token
        """
        with self._lock:
            return self._ensure_valid_token()
    
    def _ensure_valid_token(self) -> str:
        """Ensure we have a valid token, refresh if needed"""
        # Try to load cached token
        if self._token_data is None:
            self._token_data = self._load_token()
        
        # Check if refresh needed
        if self._token_data:
            expires_at = datetime.fromisoformat(self._token_data.get("expires_at", "2000-01-01"))
            buffer = timedelta(hours=1)  # Refresh 1 hour before expiry
            
            if datetime.now() + buffer < expires_at:
                logger.debug("Token valid until {}", expires_at)
                return self._token_data["access_token"]
            else:
                logger.info("Token expiring soon, refreshing...")
        else:
            logger.info("No cached token, requesting new...")
        
        # Get new token
        self._token_data = self._request_token()
        self._save_token(self._token_data)
        
        return self._token_data["access_token"]
    
    def _request_token(self) -> dict:
        """Request new access token from KIS API"""
        url = f"{self.base_url}/oauth2/tokenP"
        
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "access_token" not in data:
            raise ValueError(f"Invalid token response: {data}")
        
        # KIS tokens are valid for 24 hours
        expires_at = datetime.now() + timedelta(hours=24)
        
        token_data = {
            "access_token": data["access_token"],
            "token_type": data.get("token_type", "Bearer"),
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        logger.success("New token acquired, expires at {}", expires_at)
        return token_data
    
    def _save_token(self, token_data: dict):
        """Save token to file"""
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(token_data, f, indent=2, ensure_ascii=False)
        logger.debug("Token saved to {}", self.token_path)
    
    def _load_token(self) -> dict | None:
        """Load token from file"""
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.warning("Failed to load token: {}", e)
            return None
    
    def get_headers(self, tr_id: str = None) -> dict:
        """Get authenticated headers for API requests
        
        Args:
            tr_id: Transaction ID for the API call
            
        Returns:
            dict: Headers with auth token
        """
        token = self.get_token()
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        if tr_id:
            headers["tr_id"] = tr_id
        return headers
    
    def invalidate(self):
        """Force token refresh on next request"""
        with self._lock:
            self._token_data = None
            if self.token_path.exists():
                self.token_path.unlink()
        logger.info("Token invalidated")


# Global instance
_auth = None

def get_auth() -> AutoAuth:
    """Get global AutoAuth instance"""
    global _auth
    if _auth is None:
        _auth = AutoAuth()
    return _auth


if __name__ == "__main__":
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    print("=" * 50)
    print("Testing AutoAuth")
    print("=" * 50)
    print(f"Environment: {'Paper' if config.IS_PAPER_TRADING else 'LIVE'}")
    print(f"Base URL: {config.BASE_URL}")
    
    auth = AutoAuth()
    
    try:
        token = auth.get_token()
        print(f"✅ Token: {token[:30]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
