"""
Trader Module - Execution & Money Management
=============================================
Handles KIS API integration with exchange mapping,
token refresh, and dynamic position sizing.
"""

import json
import time
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from dataclasses import dataclass
from typing import Optional, Dict, List, Set
from loguru import logger

import config


# ==============================================
# KIS API Permanent Blacklist
# (종목정보없음 오류 발생 시 영구 차단)
# ==============================================

_KIS_BLACKLIST_FILE = Path("kis_symbol_blacklist.json")
_KIS_BLACKLIST: Set[str] = set()


def _load_blacklist():
    """Load KIS API blacklist from disk"""
    global _KIS_BLACKLIST
    if _KIS_BLACKLIST_FILE.exists():
        try:
            data = json.loads(_KIS_BLACKLIST_FILE.read_text(encoding="utf-8"))
            _KIS_BLACKLIST = set(data.get("symbols", []))
            if _KIS_BLACKLIST:
                logger.info("KIS blacklist loaded: {} symbols", len(_KIS_BLACKLIST))
        except Exception as e:
            logger.warning("Failed to load KIS blacklist: {}", e)
            _KIS_BLACKLIST = set()


def _save_blacklist():
    """Save KIS API blacklist to disk"""
    try:
        _KIS_BLACKLIST_FILE.write_text(
            json.dumps({"symbols": sorted(_KIS_BLACKLIST), "updated": datetime.now().isoformat()},
                       indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning("Failed to save KIS blacklist: {}", e)


def add_to_blacklist(symbol: str, reason: str = ""):
    """Add symbol to permanent KIS API blacklist"""
    sym = symbol.upper()
    if sym not in _KIS_BLACKLIST:
        _KIS_BLACKLIST.add(sym)
        _save_blacklist()
        logger.warning("? KIS BLACKLIST: {} added ({}). Will be skipped permanently.", sym, reason)


_load_blacklist()

_price_query_lock = threading.Lock()


# ==============================================
# Data Classes
# ==============================================

@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: float = 0.0
    message: str = ""


@dataclass
class PositionInfo:
    """Position from API"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    exchange: str
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def pnl_pct(self) -> float:
        if self.avg_price == 0:
            return 0.0
        return (self.current_price - self.avg_price) / self.avg_price


# ==============================================
# Exchange Mapper (Critical)
# ==============================================

class ExchangeMapper:
    """
    Maps stock symbols to correct exchange codes for KIS API orders
    
    Critical: API responses may use different codes than required for orders
    - NASDAQ stocks → NASD
    - NYSE stocks → NYSE  
    - AMEX stocks → AMEX
    """
    
    # Known exchange mappings
    API_TO_ORDER = {
        "NAS": "NASD",
        "NYS": "NYSE",
        "AMS": "AMEX",
        "NASD": "NASD",
        "NYSE": "NYSE",
        "AMEX": "AMEX",
        "NASDAQ": "NASD",
    }
    
    # Common symbol to exchange (can be extended)
    SYMBOL_EXCHANGE = {
        # NASDAQ common
        "AAPL": "NASD", "MSFT": "NASD", "GOOGL": "NASD", "AMZN": "NASD",
        "NVDA": "NASD", "META": "NASD", "TSLA": "NASD", "AMD": "NASD",
        "INTC": "NASD", "NFLX": "NASD", "COST": "NASD", "CSCO": "NASD",
        "PYPL": "NASD", "SBUX": "NASD", "TLT": "NASD", "ADBE": "NASD",
        "PANW": "NASD", "CRWD": "NASD", "MU": "NASD", "QCOM": "NASD",
        "TXN": "NASD", "AVGO": "NASD", "PLTR": "NASD", "SOFI": "NASD",
        "RIVN": "NASD", "LCID": "NASD", "COIN": "NASD", "MSTR": "NASD",
        "RKLB": "NASD", "AFRM": "NASD", "PLTD": "NASD",
        # NYSE common
        "JPM": "NYSE", "BAC": "NYSE", "GS": "NYSE", "WMT": "NYSE",
        "DIS": "NYSE", "KO": "NYSE", "PG": "NYSE", "JNJ": "NYSE",
        "XOM": "NYSE", "CVX": "NYSE", "HD": "NYSE", "MCD": "NYSE",
        "NKE": "NYSE", "V": "NYSE", "MA": "NYSE", "UNH": "NYSE",
        "PFE": "NYSE", "LLY": "NYSE", "ABBV": "NYSE", "CAT": "NYSE",
        "BA": "NYSE", "LMT": "NYSE", "CRM": "NYSE", "NOW": "NYSE",
        "PLD": "NYSE", "HST": "NYSE",
        # Sector ETFs
        "SPY": "NYSE", "QQQ": "NASD", "IWM": "NYSE",
        "XLK": "NYSE", "XLP": "NYSE", "XLU": "NYSE", "XLV": "NYSE",
        "XLY": "NYSE", "XLE": "NYSE", "XLF": "NYSE", "GLD": "NYSE",
        # Leveraged / Inverse ETFs
        "TQQQ": "NASD", "SQQQ": "NASD", "SOXL": "NYSE", "SOXS": "NYSE",
        "UPRO": "NYSE", "SPXU": "NYSE", "TNA": "NYSE", "TZA": "NYSE",
        "LABU": "NYSE", "LABD": "NYSE", "FNGU": "NYSE", "FNGD": "NYSE",
        "ARKK": "NYSE", "ARKG": "NYSE", "ARKF": "NYSE",
    }
    
    @classmethod
    def get_exchange(cls, symbol: str, api_code: str = None) -> str:
        """
        Get correct exchange code for order submission
        
        Args:
            symbol: Stock ticker
            api_code: Exchange code from API response (if any)
            
        Returns:
            Correct exchange code for orders (NASD/NYSE/AMEX)
        """
        # First check known symbols
        if symbol.upper() in cls.SYMBOL_EXCHANGE:
            return cls.SYMBOL_EXCHANGE[symbol.upper()]
        
        # Then try API code mapping
        if api_code:
            normalized = cls.API_TO_ORDER.get(api_code.upper())
            if normalized:
                return normalized
        
        # Default to NASD for unknown
        logger.debug("Unknown exchange for {}, defaulting to NASD", symbol)
        return "NASD"
    
    @classmethod
    def get_quote_exchange(cls, symbol: str) -> str:
        """
        Get correct exchange code for price quote endpoints.
        Order endpoints use NASD, but price endpoints use NAS.
        """
        order_exchange = cls.get_exchange(symbol)
        mapping = {
            "NASD": "NAS",
            "NYSE": "NYS",
            "AMEX": "AMS"
        }
        return mapping.get(order_exchange, "NAS")
    
    @classmethod
    def normalize(cls, api_code: str) -> str:
        """Normalize API code to order code"""
        return cls.API_TO_ORDER.get(api_code.upper(), "NASD")


# ==============================================
# Token Manager
# ==============================================

class TokenManager:
    """Manages KIS API access token with auto-refresh"""
    
    TOKEN_FILE = "token.json"
    REFRESH_HOURS = 12
    
    def __init__(self, app_key: str, app_secret: str, base_url: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self._token = None
        self._expires_at = None
        self._lock = threading.Lock()
        self._refresh_thread = None
        self._running = False
        self._stop_event = threading.Event()
    
    def start_auto_refresh(self):
        """Start background token refresh"""
        self._running = True
        self._stop_event.clear()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()
        logger.info("Token auto-refresh started (every {}h)", self.REFRESH_HOURS)
    
    def stop_auto_refresh(self):
        """Stop background refresh"""
        self._running = False
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=10)
    
    def _refresh_loop(self):
        """Background refresh loop"""
        while self._running:
            try:
                self.get_token()
            except Exception as e:
                logger.error("Token refresh failed: {}", e)
            self._stop_event.wait(timeout=self.REFRESH_HOURS * 3600)
    
    def get_token(self) -> str:
        """Get valid access token (thread-safe and process-safe)"""
        with self._lock:
            # 1. Check if current in-memory token is valid
            if self._token and self._expires_at:
                if datetime.now() + timedelta(hours=1) < self._expires_at:
                    return self._token
            
            # 2. Try loading from file
            if self._load_from_file():
                return self._token
            
            # 3. Inter-process lock to prevent concurrent API token requests
            lock_dir = Path("token.lock")
            acquired = False
            for _ in range(15):  # Try for 15 seconds
                try:
                    lock_dir.mkdir(exist_ok=False)
                    acquired = True
                    break
                except FileExistsError:
                    # Lock is held by another process, wait and reload from file
                    time.sleep(1.0)
                    if self._load_from_file():
                        return self._token
            
            try:
                # Double-check file one last time after acquiring lock
                if self._load_from_file():
                    return self._token
                # Request new token
                self._request_new_token()
            finally:
                if acquired:
                    try:
                        lock_dir.rmdir()
                    except Exception as err:
                        logger.warning("⚠️ [trader.py] Fallback triggered: {}", err)
            
            return self._token
    
    def _request_new_token(self):
        """Request new token from API"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        if "access_token" not in data:
            raise ValueError(f"Invalid token response: {data}")
        
        self._token = data["access_token"]
        expiry_str = data.get("access_token_token_expired", "")
        try:
            self._expires_at = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S") if expiry_str else datetime.now() + timedelta(hours=24)
        except ValueError:
            self._expires_at = datetime.now() + timedelta(hours=24)
        self._save_to_file()
        
        logger.success("New token acquired, expires {}", self._expires_at)
    
    def _save_to_file(self):
        """Save token to file"""
        data = {
            "access_token": self._token,
            "expires_at": self._expires_at.isoformat()
        }
        with open(self.TOKEN_FILE, "w") as f:
            json.dump(data, f)
    
    def _load_from_file(self) -> bool:
        """Load token from file"""
        path = Path(self.TOKEN_FILE)
        if not path.exists():
            return False
        try:
            with open(path) as f:
                data = json.load(f)
            self._token = data["access_token"]
            self._expires_at = datetime.fromisoformat(data["expires_at"])
            
            if datetime.now() + timedelta(hours=1) < self._expires_at:
                logger.debug("Loaded token from file")
                return True
            return False
        except Exception:
            return False

    def invalidate(self):
        """Invalidates in-memory and disk token immediately"""
        with self._lock:
            self._token = None
            self._expires_at = None
            try:
                p = Path(self.TOKEN_FILE)
                if p.exists():
                    p.unlink()
                logger.warning("🔑 KIS access token invalidated from memory and disk.")
            except Exception as e:
                logger.debug("Token file unlink error: {}", e)


# ==============================================
# Trader Class
# ==============================================

class Trader:
    """
    Trading execution and money management
    
    Features:
    - Exchange code mapping
    - Dynamic position sizing
    - Token auto-refresh
    - Balance queries
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(self):
        self.app_key = config.KIS_APP_KEY
        self.app_secret = config.KIS_APP_SECRET
        self.account_no = config.KIS_CANO
        self.account_cd = config.KIS_ACNT_PRDT_CD
        self.is_paper = config.IS_PAPER_TRADING
        
        if self.is_paper:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
        
        self._token_mgr = TokenManager(self.app_key, self.app_secret, self.base_url)
        self._exchange_mapper = ExchangeMapper()

    def invalidate_token(self):
        """Invalidate token to force immediate re-authentication"""
        self._token_mgr.invalidate()

    def check_token_error(self, data: dict, status_code: int = 200) -> bool:
        """Checks if response contains token expiry error (EGW00123/EGW00121/401) and invalidates"""
        if not isinstance(data, dict):
            data = {}
        msg_cd = str(data.get("msg_cd", ""))
        msg1 = str(data.get("msg1", ""))
        if status_code in (401, 403) or msg_cd in ("EGW00123", "EGW00121", "EGW00201") or "기간이 만료된 token" in msg1 or "유효하지 않은 token" in msg1:
            logger.warning("🚨 [TOKEN_EXPIRED] In-flight token error detected: {} ({}). Invalidating now!", msg_cd, msg1)
            self.invalidate_token()
            return True
        return False
    
    def start(self):
        """Start trader (token auto-refresh)"""
        self._token_mgr.start_auto_refresh()
        logger.info("Trader started | Paper: {}", self.is_paper)
    
    def stop(self):
        """Stop trader"""
        self._token_mgr.stop_auto_refresh()
        logger.info("Trader stopped")
    
    def _get_headers(self, tr_id: str) -> dict:
        """Get authenticated headers"""
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self._token_mgr.get_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
    
    # ==============================================
    # Account Queries
    # ==============================================
    
    def get_buying_power(self, symbol: str = "AAPL") -> float:
        """Get available USD for trading using dedicated buying power API"""
        tr_id = "VTTS3007R" if self.is_paper else "TTTS3007R"
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
        
        # 매수가능금액조회 requires a symbol and price reference
        ref_price = self.get_price(symbol)
        if ref_price <= 0:
            ref_price = 1.0  # fallback
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": ExchangeMapper.get_exchange(symbol),
            "OVRS_ORD_UNPR": f"{ref_price:.2f}",
            "ITEM_CD": symbol,
        }
        
        try:
            resp = requests.get(url, headers=self._get_headers(tr_id), 
                              params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                # frcr_ord_psbl_amt1 = 통합 주문가능금액 (원화+외화 환산)
                # ovrs_ord_psbl_amt = 외화 주문가능금액
                usd_str = output.get("frcr_ord_psbl_amt1", "") or output.get("ovrs_ord_psbl_amt", "") or "0"
                usd = float(usd_str) if usd_str.strip() else 0.0
                logger.info("Buying Power: ${:,.2f}", usd)
                return usd
            else:
                logger.warning("Buying power query failed: {}", data.get("msg1", ""))
            return 0.0
        except Exception as e:
            logger.error("Buying power query failed: {}", e)
            return 0.0
    
    def get_positions(self) -> List[PositionInfo]:
        """Get all positions across all supported exchanges (NASD, NYSE, AMEX)"""
        tr_id = "VTTS3012R" if self.is_paper else "TTTS3012R"
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
        
        positions_dict = {}
        # Iterate through major exchanges to catch NYSE/AMEX "Ghost" positions
        # KIS Codes: NASD=NASDAQ, NYS=NYSE, AMS=AMEX
        for exchange_code in ["NASD", "NYS", "AMS"]:
            params = {
                "CANO": self.account_no,
                "ACNT_PRDT_CD": self.account_cd,
                "OVRS_EXCG_CD": exchange_code,
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }
            
            try:
                resp = requests.get(url, headers=self._get_headers(tr_id),
                                  params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if self.check_token_error(data, resp.status_code):
                    time.sleep(1)
                    continue

                if data.get("rt_cd") == "0":
                    for item in data.get("output1", []):
                        sym = item.get("ovrs_pdno", "").strip()
                        qty_str = item.get("ovrs_cblc_qty", "") or item.get("ord_psbl_qty", "") or "0"
                        try:
                            qty = int(float(str(qty_str).strip()))
                        except Exception:
                            qty = 0
                        
                        if qty > 0 and sym:
                            positions_dict[sym] = PositionInfo(
                                symbol=sym,
                                quantity=qty,
                                avg_price=float(item.get("pchs_avg_pric", 0) or 0),
                                current_price=float(item.get("now_pric2", 0) or 0),
                                exchange=exchange_code
                            )
                else:
                    logger.debug("Position query returned non-zero code {} on {}", data.get("rt_cd"), exchange_code)
            except Exception as e:
                logger.error("Position query failed for {}: {}", exchange_code, e)
                
        return list(positions_dict.values())
    
    # ==============================================
    # Price Queries
    # ==============================================
    
    def get_price(self, symbol: str, exchange: str = None) -> float:
        """Get current price"""
        # Map order exchange codes (NASD, NYSE, AMEX) to quote codes (NAS, NYS, AMS)
        QUOTE_MAP = {
            "NASD": "NAS",
            "NYSE": "NYS",
            "AMEX": "AMS",
            "NAS": "NAS",
            "NYS": "NYS",
            "AMS": "AMS"
        }
        if exchange:
            exchange = QUOTE_MAP.get(exchange.upper(), exchange)
            
        exchanges_to_try = [exchange] if exchange else [self._exchange_mapper.get_quote_exchange(symbol)]
        
        # Check if currently in Pre-Market or After-Hours session
        try:
            import datetime, pytz
            tz = pytz.timezone('US/Eastern')
            now_est = datetime.datetime.now(tz)
            hm = now_est.hour * 60 + now_est.minute
            weekday = now_est.weekday()
            is_pre = (4 * 60 <= hm < 9 * 60 + 30) and weekday < 5
            is_post = (16 * 60 <= hm < 20 * 60) and weekday < 5
            _is_ext = is_pre or is_post
        except Exception:
            _is_ext = False
            is_pre = False
            is_post = False

        # If in extended hours (Pre/After market), prioritize live 1m tick and pre/postMarketPrice
        if _is_ext:
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                # Method 1: 1m intraday prepost bar (most accurate real-time tick)
                try:
                    df = ticker.history(period="1d", interval="1m", prepost=True)
                    if df is not None and not df.empty:
                        c_val = df['Close'].values[-1]
                        ext_p = float(c_val.item() if hasattr(c_val, 'item') else c_val)
                        if ext_p > 0:
                            return ext_p
                except Exception:
                    pass

                # Method 2: fast info / info preMarketPrice or postMarketPrice
                info = ticker.info or {}
                ext_p = info.get('preMarketPrice') if is_pre else info.get('postMarketPrice')
                if ext_p and float(ext_p) > 0:
                    return float(ext_p)
            except Exception:
                pass

        # If regular market or yfinance fallback, query KIS API price
        tr_id = "HHDFS00000300"
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        
        for excd in exchanges_to_try:
            params = {"AUTH": "", "EXCD": excd, "SYMB": symbol}
            
            # Rate limit protection (Max 20 RPS - Thread-Safe Serialization)
            with _price_query_lock:
                time.sleep(0.1)
                try:
                    resp = requests.get(url, headers=self._get_headers(tr_id),
                                      params=params, timeout=10)
                    data = resp.json()
                    
                    if data.get("rt_cd") == "0":
                        out = data.get("output", {})
                        # 1) Regular market last price
                        last_p = out.get("last", "")
                        # 2) Extended hours / pre-market price (t_xprc)
                        ext_p = out.get("t_xprc", "")
                        
                        resolved_price = 0.0
                        # If extended hours price exists and differs from zero, check time or value
                        if ext_p and float(ext_p or 0) > 0:
                            resolved_price = float(ext_p)
                        elif last_p and float(last_p or 0) > 0:
                            resolved_price = float(last_p)
                        elif out.get("base") and float(out.get("base") or 0) > 0:
                            resolved_price = float(out.get("base"))

                        if resolved_price > 0:
                            if exchange is None and symbol.upper() not in self._exchange_mapper.SYMBOL_EXCHANGE:
                                order_excd = "NYSE" if excd == "NYS" else ("AMEX" if excd == "AMS" else "NASD")
                                self._exchange_mapper.SYMBOL_EXCHANGE[symbol.upper()] = order_excd
                                logger.debug("Dynamically resolved exchange for {} to {}", symbol, order_excd)
                            return resolved_price
                except Exception as e:
                    logger.debug("Price query failed for {} on {}: {}", symbol, excd, e)
                
        # 3) Final Fallback to yfinance fast_info for pre-market / after-hours or indices
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            fast_p = getattr(ticker.fast_info, 'last_price', None)
            if fast_p and float(fast_p) > 0:
                return float(fast_p)
        except Exception:
            pass

        return 0.0

    def get_order_book(self, symbol: str, exchange: str = None) -> dict:
        """
        Get real-time 10-level bid/ask order book for a symbol.
        Uses /uapi/overseas-price/v1/quotations/inquire-asking-price with TR_ID HHDFS76200100.
        """
        QUOTE_MAP = {
            "NASD": "NAS",
            "NYSE": "NYS",
            "AMEX": "AMS",
            "NAS": "NAS",
            "NYS": "NYS",
            "AMS": "AMS"
        }
        if exchange:
            exchange = QUOTE_MAP.get(exchange.upper(), exchange)

        exchanges_to_try = [exchange] if exchange else [self._exchange_mapper.get_quote_exchange(symbol)]
        
        if exchange is None and exchanges_to_try[0] == "NAS" and symbol.upper() not in self._exchange_mapper.SYMBOL_EXCHANGE:
            exchanges_to_try = ["NAS", "NYS", "AMS"]

        tr_id = "HHDFS76200100"
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/inquire-asking-price"

        for excd in exchanges_to_try:
            params = {"AUTH": "", "EXCD": excd, "SYMB": symbol}
            
            # Rate limit protection (Max 20 RPS - Thread-Safe Serialization)
            with _price_query_lock:
                time.sleep(0.1)
                try:
                    resp = requests.get(url, headers=self._get_headers(tr_id),
                                        params=params, timeout=10)
                    data = resp.json()

                    if data.get("rt_cd") == "0":
                        return data
                except Exception as e:
                    logger.error("Order book fetch failed for {} on {}: {}", symbol, excd, e)
        return {}

    def calculate_obi(self, symbol: str, exchange: str = None) -> float:
        """
        Calculate Multi-Level Order Flow Imbalance (MLOFI) for a symbol using a decaying harmonic weight.
        Returns a float between -1.0 (strong sell pressure) and +1.0 (strong buy pressure).
        Formula: Sum( w_i * (vbid_i - vask_i) ) / Sum( w_i * (vbid_i + vask_i) )
        """
        ob = self.get_order_book(symbol, exchange)
        if not ob:
            return 0.0

        output1 = ob.get("output1", {})
        output2 = ob.get("output2", {})

        # 1. Primary: Weighted 10-level ask/bid volumes (Microstructure decay weighting)
        try:
            bid_sum = 0.0
            ask_sum = 0.0
            for i in range(1, 11):
                vbid = float(output2.get(f"vbid{i}", 0))
                vask = float(output2.get(f"vask{i}", 0))
                
                # Decaying weight: Level 1 gets 100%, Level 10 gets 10% (harmonic decay)
                weight = 1.0 / i
                
                bid_sum += vbid * weight
                ask_sum += vask * weight

            if bid_sum + ask_sum > 0:
                mlofi = (bid_sum - ask_sum) / (bid_sum + ask_sum)
                return max(-1.0, min(1.0, mlofi))
        except Exception as err:
            logger.warning("⚠️ [trader.py] Fallback triggered: {}", err)

        # 2. Fallback: Simple total volumes from output1
        try:
            bvol = float(output1.get("bvol", 0))
            avol = float(output1.get("avol", 0))
            if bvol + avol > 0:
                obi = (bvol - avol) / (bvol + avol)
                return max(-1.0, min(1.0, obi))
        except Exception as err:
            logger.warning("⚠️ [trader.py] Fallback triggered: {}", err)

        return 0.0

    def get_spread(self, symbol: str, exchange: str = None) -> float:
        """
        Calculate real-time bid-ask spread of the order book.
        Formula: (Ask_1 - Bid_1) / MidPrice
        """
        ob = self.get_order_book(symbol, exchange)
        if not ob:
            return 0.001  # Default fallback of 10 bps

        output2 = ob.get("output2", {})
        try:
            pbid1 = float(output2.get("pbid1", 0))
            pask1 = float(output2.get("pask1", 0))
            if pbid1 > 0 and pask1 > 0:
                mid = (pbid1 + pask1) / 2.0
                return (pask1 - pbid1) / mid
        except Exception as err:
            logger.warning("⚠️ [trader.py] Fallback triggered: {}", err)
        return 0.001  # Default fallback

    # ==============================================
    # Order Execution
    # ==============================================
    
    def buy(self, symbol: str, quantity: int, limit_price: float = None, ensure_fill: bool = False) -> OrderResult:
        """Buy stock with limit order, optionally chasing price if unfilled"""
        # Check permanent blacklist first (do it at the very top to save API calls)
        if symbol.upper() in _KIS_BLACKLIST:
            logger.debug("BLACKLIST: {} skipped (KIS API permanently rejected)", symbol)
            return OrderResult(False, "", symbol, "BUY", quantity, limit_price or 0.0, "KIS_BLACKLISTED")

        if limit_price is None:
            price = self.get_price(symbol)
            # [SOTA QUANT SPREAD GATE & MID-SPREAD PEGGING]
            # 10호가 스프레드를 실시간 측정하여 슬리피지를 원천 차단
            spread = self.get_spread(symbol)
            if spread > 0.0035:
                # 스프레드가 35 bps 초과로 넓을 경우: Ask가 아닌 호가 내부 40% 지점(Mid-Spread)에 페깅하여 60% 슬리피지 절감
                ob = self.get_order_book(symbol)
                output2 = ob.get("output2", {}) if isinstance(ob, dict) else {}
                pbid1 = float(output2.get("pbid1", 0) or 0)
                pask1 = float(output2.get("pask1", 0) or 0)
                if pbid1 > 0 and pask1 > 0 and pask1 > pbid1:
                    limit_price = round(pbid1 + (pask1 - pbid1) * 0.40, 2)
                    logger.info("🛡️ [SPREAD_GATE_PEGGED] {} Wide Spread {:.2%} (>0.35%) | Bid: ${:.2f}, Ask: ${:.2f} -> Pegged Limit: ${:.2f} (Saved {:.2%} slippage)",
                                symbol, spread, pbid1, pask1, limit_price, (pask1 - limit_price) / price)
                else:
                    limit_price = round(price * 1.0015, 2)
            else:
                # 스프레드가 35 bps 이하로 촘촘할 경우: 즉시 체결을 위해 15 bps 가산 지정가
                limit_price = round(price * (1.0 + max(0.0005, spread * 0.5)), 2)
                logger.info("⚡ [TIGHT_SPREAD_EXECUTION] BUY {} | Price: ${:.2f}, Spread: {:.2%}, Limit: ${:.2f}",
                            symbol, price, spread, limit_price)
            
        exchange = self._exchange_mapper.get_exchange(symbol)
        
        tr_id = "VTTT1002U" if self.is_paper else "TTTT1002U"
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": f"{limit_price:.2f}",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        logger.info("BUY {} x {} @ ${:.2f} ({})", symbol, quantity, limit_price, exchange)
        
        # All exchanges to try in order
        EXCHANGE_PROBE_ORDER = [exchange, "NYSE", "NASD", "AMEX"]
        # Deduplicate while preserving order
        seen = set()
        exchanges_to_try = [e for e in EXCHANGE_PROBE_ORDER if not (e in seen or seen.add(e))]
        
        no_info_error = "해당종목정보가 없습니다"
        all_no_info = True  # Flag to track if all errors were KIS "no info" errors
        
        for try_exchange in exchanges_to_try:
            body["OVRS_EXCG_CD"] = try_exchange
            if try_exchange != exchange:
                logger.info("BUY {} retrying on exchange {} (prev: {})", symbol, try_exchange, exchange)
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = requests.post(url, headers=self._get_headers(tr_id),
                                       json=body, timeout=10)
                    data = resp.json()
                    
                    if data.get("rt_cd") == "0":
                        all_no_info = False
                        order_id = data.get("output", {}).get("ODNO", "")
                        logger.success("BUY order placed: {} (ID: {}, exchange: {})", symbol, order_id, try_exchange)
                        # Cache successful exchange
                        self._exchange_mapper.SYMBOL_EXCHANGE[symbol.upper()] = try_exchange
                        result = OrderResult(True, order_id, symbol, "BUY", quantity, limit_price)
                        
                        if ensure_fill:
                            # Wait 15 seconds for fill
                            time.sleep(15)
                            orders = self.get_unfilled_orders()
                            unfilled = next((o for o in orders if o["order_id"] == order_id), None)
                            
                            if unfilled:
                                logger.warning("BUY Order {} ({}) UNFILLED after 15s. Chasing market!", order_id, symbol)
                                # Cancel the old order
                                if self.cancel_order(order_id, symbol, unfilled["quantity"], try_exchange, "BUY"):
                                    time.sleep(2)
                                    
                                    # Resubmit at max of +1% or current price +0.5% (aggressive chase)
                                    current_price = self.get_price(symbol)
                                    chase_price = round(max(limit_price * 1.01, current_price * 1.005), 2)
                                    logger.warning("Resubmitting BUY for {} at CHASE PRICE: ${:.2f}", symbol, chase_price)
                                    return self.buy(symbol, unfilled["quantity"], limit_price=chase_price, ensure_fill=False)
                                else:
                                    logger.error("Cancel failed for BUY order {} ({}). Keeping original order active, skipping chase.", order_id, symbol)
                                    return result
                        
                        return result
                    else:
                        if self.check_token_error(data, resp.status_code):
                            time.sleep(1)
                            continue
                        msg = data.get("msg1", "Error")
                        logger.error("BUY failed on {}: {}", try_exchange, msg)
                        if no_info_error in msg:
                            break  # No point retrying same exchange — try next
                        
                        # Any other error means it's not a "no info" issue
                        all_no_info = False
                        if attempt < self.MAX_RETRIES - 1:
                            time.sleep(self.RETRY_DELAY)
                except Exception as e:
                    # Connection/network errors are not "no info" errors
                    all_no_info = False
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                        continue
                    logger.error("BUY request exception for {}: {}", symbol, e)
        
        # Only blacklist if we specifically got KIS "no info" error on all exchanges
        if all_no_info:
            add_to_blacklist(symbol, "해당종목정보가 없습니다 (all exchanges)")
            return OrderResult(False, "", symbol, "BUY", quantity, limit_price, "KIS_SYMBOL_NOT_FOUND")
        else:
            return OrderResult(False, "", symbol, "BUY", quantity, limit_price, "ORDER_FAILED")
    
    def sell(self, symbol: str, quantity: int, limit_price: float = None, ensure_fill: bool = False) -> OrderResult:
        """Sell stock with limit order, optionally chasing price if unfilled"""
        # Warn if selling a blacklisted symbol, but don't hard-block sells
        if symbol.upper() in _KIS_BLACKLIST:
            logger.warning("⚠️ SELL on blacklisted {}: attempting anyway to close position.", symbol)

        if limit_price is None:
            price = self.get_price(symbol)
            # [Quant-Execution] Spread-Aware Dynamic Pricing (호가 스프레드 연동형 동적 지정가 산출)
            spread = self.get_spread(symbol)
            markdown = max(0.001, min(0.015, spread * 1.5))
            limit_price = round(price * (1.0 - markdown), 2)
            logger.info("SELL {} | Price: ${:.2f}, Spread: {:.2%}, Markdown: {:.2%}, Limit: ${:.2f}",
                        symbol, price, spread, markdown, limit_price)
            
        exchange = self._exchange_mapper.get_exchange(symbol)
        
        # Multi-exchange fallback for SELL (prioritize known exchange, then try all exchanges)
        exchanges_to_try = [exchange]
        for alt in ["NYSE", "NASD", "AMEX"]:
            if alt not in exchanges_to_try:
                exchanges_to_try.append(alt)

        tr_id = "VTTT1001U" if self.is_paper else "TTTT1006U"
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": f"{limit_price:.2f}",
            "SLL_TYPE": "00",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        logger.info("SELL {} x {} @ ${:.2f} (trying: {})", symbol, quantity, limit_price, exchanges_to_try)
        
        no_info_error = "해당종목정보가 없습니다"
        last_error_msg = "ORDER_FAILED"

        for try_exchange in exchanges_to_try:
            body["OVRS_EXCG_CD"] = try_exchange
            if try_exchange != exchange:
                logger.info("SELL {} retrying on exchange {} (prev: {})", symbol, try_exchange, exchange)

            for attempt in range(self.MAX_RETRIES):
                try:
                    resp = requests.post(url, headers=self._get_headers(tr_id),
                                       json=body, timeout=10)
                    data = resp.json()
                    
                    if data.get("rt_cd") == "0":
                        order_id = data.get("output", {}).get("ODNO", "")
                        logger.success("SELL order placed: {} (ID: {}, exchange: {})", symbol, order_id, try_exchange)
                        # Cache successful exchange
                        self._exchange_mapper.SYMBOL_EXCHANGE[symbol.upper()] = try_exchange
                        result = OrderResult(True, order_id, symbol, "SELL", quantity, limit_price)
                        
                        if ensure_fill:
                            # Wait 15 seconds for fill
                            time.sleep(15)
                            orders = self.get_unfilled_orders()
                            unfilled = next((o for o in orders if o["order_id"] == order_id), None)
                            
                            if unfilled:
                                logger.warning("Order {} ({}) UNFILLED after 15s. Chasing market!", order_id, symbol)
                                # Cancel the old order
                                if self.cancel_order(order_id, symbol, unfilled["quantity"], try_exchange, "SELL"):
                                    time.sleep(2)  # Wait for cancellation to process
                                    
                                    # Resubmit at min of -1.0% or current price -0.5% (aggressive chase)
                                    current_price = self.get_price(symbol)
                                    chase_price = round(min(limit_price * 0.99, current_price * 0.995), 2)
                                    logger.warning("Resubmitting SELL for {} at CHASE PRICE: ${:.2f}", symbol, chase_price)
                                    return self.sell(symbol, unfilled["quantity"], limit_price=chase_price, ensure_fill=False)
                                else:
                                    logger.error("Cancel failed for order {} ({}). Keeping original order active, skipping chase.", order_id, symbol)
                                    return result
                        
                        return result
                    else:
                        if self.check_token_error(data, resp.status_code):
                            time.sleep(1)
                            continue
                        last_error_msg = data.get("msg1", "Error")
                        logger.error("SELL failed on {}: {}", try_exchange, last_error_msg)
                        if no_info_error in last_error_msg:
                            break  # Try next exchange in exchanges_to_try
                        if attempt < self.MAX_RETRIES - 1:
                            time.sleep(self.RETRY_DELAY)
                except Exception as e:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(self.RETRY_DELAY)
                        continue
                    logger.error("SELL request exception for {} on {}: {}", symbol, try_exchange, e)

        return OrderResult(False, "", symbol, "SELL", quantity, limit_price, last_error_msg)
    
    def calculate_order_qty(self, symbol: str, usd_amount: float) -> int:
        """Calculate order quantity for given USD amount"""
        price = self.get_price(symbol)
        if price <= 0:
            return 0
        return int(usd_amount / price)
    
    # ==============================================
    # Order Verification
    # ==============================================
    
    def get_unfilled_orders(self) -> list:
        """미체결 주문 내역 조회"""
        tr_id = "VTTS3018R" if self.is_paper else "TTTS3018R"
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-nccs"
        
        # KIS requires querying per exchange to get comprehensive unfilled list
        exchanges = ["NASD", "NYSE", "AMEX"]
        orders = []
        
        for exch in exchanges:
            params = {
                "CANO": self.account_no,
                "ACNT_PRDT_CD": self.account_cd,
                "OVRS_EXCG_CD": exch,
                "SORT_SQN": "DS",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }
            
            try:
                # 50ms protection sleep
                time.sleep(0.05)
                resp = requests.get(url, headers=self._get_headers(tr_id),
                                  params=params, timeout=10)
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    for item in data.get("output", []):
                        remaining = int(item.get("nccs_qty", 0))
                        if remaining > 0:
                            orders.append({
                                "order_id": item.get("odno", ""),
                                "symbol": item.get("pdno", ""),
                                "side": "BUY" if item.get("sll_buy_dvsn_cd") == "02" else "SELL",
                                "quantity": remaining,
                                "price": float(item.get("ft_ord_unpr3", 0)),
                                "exchange": item.get("ovrs_excg_cd", "")
                            })
                else:
                    logger.debug("Unfilled query warning for {}: {}", exch, data.get("msg1", ""))
            except Exception as e:
                logger.error("Unfilled orders query failed for {}: {}", exch, e)
                
        return orders
    
    def cancel_order(self, order_id: str, symbol: str, quantity: int, 
                     exchange: str, side: str) -> bool:
        """주문 취소"""
        if side == "BUY":
            tr_id = "VTTT1004U" if self.is_paper else "TTTT1004U"
        else:
            tr_id = "VTTT1003U" if self.is_paper else "TTTT1003U"
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order-rvsecncl"
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORGN_ODNO": order_id,
            "RVSE_CNCL_DVSN_CD": "02",  # 02 = 취소
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        try:
            resp = requests.post(url, headers=self._get_headers(tr_id),
                               json=body, timeout=10)
            data = resp.json()
            
            if data.get("rt_cd") == "0":
                logger.info("Order cancelled: {} ({})", order_id, symbol)
                return True
            else:
                logger.error("Cancel failed: {}", data.get("msg1", ""))
                return False
        except Exception as e:
            logger.error("Cancel order error: {}", e)
            return False
    
    def cancel_all_unfilled(self) -> int:
        """모든 미체결 주문 취소"""
        orders = self.get_unfilled_orders()
        cancelled = 0
        
        for order in orders:
            time.sleep(0.5)  # API 호출 제한
            if self.cancel_order(
                order["order_id"], order["symbol"],
                order["quantity"], order["exchange"], order["side"]
            ):
                cancelled += 1
        
        if cancelled > 0:
            logger.warning("Cancelled {} unfilled orders", cancelled)
        return cancelled
    
    def wait_for_fill(self, order_id: str, symbol: str, 
                       max_wait: int = 30) -> bool:
        """주문 체결 대기 (최대 max_wait초)"""
        num_checks = max(1, max_wait // 5)
        for i in range(num_checks):
            time.sleep(5)
            orders = self.get_unfilled_orders()
            still_pending = any(o["order_id"] == order_id for o in orders)
            if not still_pending:
                logger.info("Order {} filled for {}", order_id, symbol)
                return True
        
        logger.warning("Order {} not filled within {}s for {}", 
                       order_id, max_wait, symbol)
        return False

    def get_order_fill_price(self, order_id: str, symbol: str, default_price: float) -> float:
        """
        Queries KIS Overseas Order Execution History (inquire-ccnl) to retrieve the EXACT 
        market execution/fill price matched on the exchange, rather than the submitted limit order price.
        """
        if not order_id:
            return default_price
            
        try:
            exchange = self.get_exchange(symbol)
            headers = self._get_headers("TTTS3035R")
            from datetime import datetime, date
            today_str = date.today().strftime("%Y%m%d")
            params = {
                "CANO": config.KIS_CANO,
                "ACNT_PRDT_CD": config.KIS_ACNT_PRDT_CD,
                "PDNO": "%",
                "ORD_STRT_DT": today_str,
                "ORD_END_DT": today_str,
                "SLL_BUY_DVSN": "00",
                "CCLD_DVSN": "00",
                "OVRS_EXCG_CD": exchange,
                "SORT_SQN": "DS",
                "ORD_DT": "",
                "ORD_GNO_BRNO": "",
                "ODNO": order_id,
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }
            url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
            r = requests.get(url, headers=headers, params=params, timeout=8)
            if r.ok:
                data = r.json()
                for item in data.get("output", []):
                    item_odno = item.get("odno", "")
                    if item_odno == order_id or not order_id:
                        ccld_p = float(item.get("ft_ccld_pric3", 0.0) or 0.0)
                        ccld_qty = int(item.get("ft_ccld_qty", 0) or 0)
                        if ccld_p > 0 and ccld_qty > 0:
                            logger.info("🎯 [REAL_FILL_PRICE] Order {} ({}) actual broker fill price: ${:.2f} (vs submitted ${:.2f})",
                                        order_id, symbol, ccld_p, default_price)
                            return ccld_p
        except Exception as e:
            logger.debug("Failed to query inquire-ccnl for order {}: {}", order_id, e)
            
        # Fallback: check live quote if drift is significant
        try:
            curr_p = self.get_price(symbol)
            if curr_p > 0 and abs(curr_p - default_price) / default_price > 0.005:
                logger.info("🎯 [REAL_FILL_PRICE_FALLBACK] Using market quote ${:.2f} for {} fill (vs limit ${:.2f})",
                            curr_p, symbol, default_price)
                return curr_p
        except Exception:
            pass
            
        return default_price
    
    def close_all_positions(self, dry_run: bool = False) -> List[OrderResult]:
        """Close all open positions"""
        logger.warning("CLOSING ALL POSITIONS")
        
        positions = self.get_positions()
        results = []
        
        for pos in positions:
            logger.info("Closing {}: {} shares", pos.symbol, pos.quantity)
            
            if dry_run:
                results.append(OrderResult(True, "DRY", pos.symbol, "SELL", pos.quantity))
                continue
            
            result = self.sell(pos.symbol, pos.quantity)
            results.append(result)
        
        return results


# Global instance
_trader = None

def get_trader() -> Trader:
    global _trader
    if _trader is None:
        _trader = Trader()
    return _trader


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing Trader...")
    print(f"Paper Trading: {config.IS_PAPER_TRADING}")
    
    # Test exchange mapper
    print("\nExchange Mapper Tests:")
    print(f"  AAPL -> {ExchangeMapper.get_exchange('AAPL')}")
    print(f"  JPM  -> {ExchangeMapper.get_exchange('JPM')}")
    print(f"  PLTR -> {ExchangeMapper.get_exchange('PLTR')}")
