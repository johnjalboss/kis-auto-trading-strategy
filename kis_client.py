"""
KISClient - Korea Investment & Securities API Client
=====================================================
Handles authentication, token management, and trading operations.
Integrated with Macro-Defense Shield for position sizing.
"""

import json
import time
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from loguru import logger

import config


# ==============================================
# Data Classes
# ==============================================

@dataclass
class TokenInfo:
    """Access Token Information"""
    access_token: str
    token_type: str
    expires_at: datetime
    created_at: datetime


@dataclass
class BuyingPower:
    """Available buying power"""
    usd_available: float
    usd_total: float
    positions_value: float
    timestamp: datetime


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


# ==============================================
# KISClient Class
# ==============================================

class KISClient:
    """
    Korea Investment & Securities API Client
    
    Features:
    - Automatic token management with refresh
    - Thread-safe operations
    - Retry logic for API failures
    - Exchange code normalization
    - Buying power queries
    - Order execution
    """
    
    # Exchange code mapping (API response -> Order codes)
    EXCHANGE_MAP = {
        "NAS": "NASD",
        "NYS": "NYSE", 
        "AMS": "AMEX",
        "NASD": "NASD",
        "NYSE": "NYSE",
        "AMEX": "AMEX",
        "NASDAQ": "NASD",
    }
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, 
                 app_key: str = None,
                 app_secret: str = None,
                 account_no: str = None,
                 account_cd: str = None,
                 is_paper: bool = True):
        """
        Initialize KIS API Client
        
        Args:
            app_key: KIS App Key (from .env if None)
            app_secret: KIS App Secret (from .env if None)
            account_no: Account number (from .env if None)
            account_cd: Account product code (from .env if None)
            is_paper: True for paper trading, False for live
        """
        self.app_key = app_key or config.KIS_APP_KEY
        self.app_secret = app_secret or config.KIS_APP_SECRET
        self.account_no = account_no or config.KIS_CANO
        self.account_cd = account_cd or config.KIS_ACNT_PRDT_CD
        self.is_paper = is_paper if is_paper is not None else config.IS_PAPER_TRADING
        
        # Set base URL based on trading mode
        if self.is_paper:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"
        
        # Token management
        self._token: Optional[TokenInfo] = None
        self._token_lock = threading.Lock()
        self._token_path = Path("token.json")
        
        # Auto-refresh thread
        self._refresh_thread: Optional[threading.Thread] = None
        self._running = False
        
        logger.info("KISClient initialized | Paper: {} | URL: {}", 
                   self.is_paper, self.base_url)
    
    # ==============================================
    # Token Management
    # ==============================================
    
    def start_auto_refresh(self, interval_hours: int = 12):
        """Start automatic token refresh in background"""
        self._running = True
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop, 
            args=(interval_hours,),
            daemon=True
        )
        self._refresh_thread.start()
        logger.info("Auto-refresh started (every {}h)", interval_hours)
    
    def stop_auto_refresh(self):
        """Stop automatic token refresh"""
        self._running = False
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("Auto-refresh stopped")
    
    def _refresh_loop(self, interval_hours: int):
        """Background token refresh loop"""
        while self._running:
            try:
                self.get_access_token()
            except Exception as e:
                logger.error("Token refresh failed: {}", e)
            time.sleep(interval_hours * 3600)
    
    def get_access_token(self) -> str:
        """
        Get valid access token (thread-safe)
        
        Checks cached token, loads from file, or requests new token.
        
        Returns:
            str: Valid access token
        """
        with self._token_lock:
            # Check cached token
            if self._token and self._is_token_valid():
                return self._token.access_token
            
            # Try loading from file
            if self._load_token_file() and self._is_token_valid():
                logger.debug("Loaded token from file")
                return self._token.access_token
            
            # Request new token
            logger.info("Requesting new access token...")
            self._request_new_token()
            return self._token.access_token
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid (1 hour buffer)"""
        if not self._token:
            return False
        return datetime.now() + timedelta(hours=1) < self._token.expires_at
    
    def _request_new_token(self):
        """Request new token from KIS API"""
        url = f"{self.base_url}/oauth2/tokenP"
        
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                
                if "access_token" not in data:
                    raise ValueError(f"Invalid response: {data}")
                
                expires_at = datetime.now() + timedelta(hours=24)
                
                self._token = TokenInfo(
                    access_token=data["access_token"],
                    token_type=data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    created_at=datetime.now()
                )
                
                self._save_token_file()
                logger.success("New token acquired, expires at {}", expires_at)
                return
                
            except Exception as e:
                logger.warning("Token request attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise RuntimeError(f"Failed to get token after {self.MAX_RETRIES} attempts")
    
    def _save_token_file(self):
        """Save token to file"""
        if not self._token:
            return
        data = {
            "access_token": self._token.access_token,
            "token_type": self._token.token_type,
            "expires_at": self._token.expires_at.isoformat(),
            "created_at": self._token.created_at.isoformat()
        }
        with open(self._token_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def _load_token_file(self) -> bool:
        """Load token from file"""
        if not self._token_path.exists():
            return False
        try:
            with open(self._token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._token = TokenInfo(
                access_token=data["access_token"],
                token_type=data.get("token_type", "Bearer"),
                expires_at=datetime.fromisoformat(data["expires_at"]),
                created_at=datetime.fromisoformat(data["created_at"])
            )
            return True
        except Exception as e:
            logger.warning("Failed to load token file: {}", e)
            return False
    
    def _get_headers(self, tr_id: str) -> Dict[str, str]:
        """Get authenticated headers for API request"""
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self.get_access_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
    
    # ==============================================
    # Account Queries
    # ==============================================
    
    def check_buying_power(self) -> BuyingPower:
        """
        Check available buying power (USD)
        
        Uses /uapi/overseas-stock/v1/trading/inquire-balance endpoint.
        
        Returns:
            BuyingPower with available USD
        """
        tr_id = "VTTS3012R" if self.is_paper else "TTTS3012R"
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": "NASD",
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") != "0":
                    logger.error("Balance query failed: {}", data.get("msg1"))
                    raise ValueError(data.get("msg1", "Unknown error"))
                
                output2 = data.get("output2", {})
                
                buying_power = BuyingPower(
                    usd_available=float(output2.get("frcr_ord_psbl_amt_1", 0)),
                    usd_total=float(output2.get("tot_evlu_pfls_amt", 0)),
                    positions_value=float(output2.get("ovrs_stck_evlu_amt", 0)),
                    timestamp=datetime.now()
                )
                
                logger.info("Buying Power: ${:,.2f} available", buying_power.usd_available)
                return buying_power
                
            except Exception as e:
                logger.warning("Buying power query attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    return BuyingPower(0, 0, 0, datetime.now())
    
    # ==============================================
    # Order Execution
    # ==============================================
    
    def normalize_exchange(self, code: str) -> str:
        """Normalize exchange code for orders"""
        return self.EXCHANGE_MAP.get(code.upper(), "NASD") if code else "NASD"
    
    def get_current_price(self, symbol: str, exchange: str = "NASD") -> float:
        """Get current price for a symbol"""
        tr_id = "HHDFS00000300"
        
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        headers = self._get_headers(tr_id)
        
        params = {
            "AUTH": "",
            "EXCD": self.normalize_exchange(exchange),
            "SYMB": symbol
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") == "0":
                return float(data.get("output", {}).get("last", 0))
            return 0.0
        except Exception as e:
            logger.error("Price query error for {}: {}", symbol, e)
            return 0.0
    
    def buy_limit_order(self, symbol: str, quantity: int, price: float,
                        exchange: str = "NASD") -> OrderResult:
        """Place limit buy order"""
        tr_id = "VTTT1002U" if self.is_paper else "TTTT1002U"
        exchange = self.normalize_exchange(exchange)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        headers = self._get_headers(tr_id)
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": f"{price:.2f}",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        logger.info("BUY {} x {} @ ${:.2f}", symbol, quantity, price)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    order_id = data.get("output", {}).get("ODNO", "")
                    logger.success("Order placed: {} (ID: {})", symbol, order_id)
                    return OrderResult(True, order_id, symbol, "BUY", quantity, price, "Success")
                else:
                    msg = data.get("msg1", "Error")
                    logger.error("Order failed: {}", msg)
                    return OrderResult(False, "", symbol, "BUY", quantity, price, msg)
                    
            except Exception as e:
                logger.warning("Order attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        return OrderResult(False, "", symbol, "BUY", quantity, price, "Max retries exceeded")
    
    def sell_limit_order(self, symbol: str, quantity: int, price: float,
                         exchange: str = "NASD") -> OrderResult:
        """Place limit sell order"""
        tr_id = "VTTT1001U" if self.is_paper else "TTTT1006U"
        exchange = self.normalize_exchange(exchange)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        headers = self._get_headers(tr_id)
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": f"{price:.2f}",
            "SLL_TYPE": "00",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        logger.info("SELL {} x {} @ ${:.2f}", symbol, quantity, price)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    order_id = data.get("output", {}).get("ODNO", "")
                    logger.success("Sell order placed: {} (ID: {})", symbol, order_id)
                    return OrderResult(True, order_id, symbol, "SELL", quantity, price, "Success")
                else:
                    msg = data.get("msg1", "Error")
                    logger.error("Sell failed: {}", msg)
                    return OrderResult(False, "", symbol, "SELL", quantity, price, msg)
                    
            except Exception as e:
                logger.warning("Sell attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        return OrderResult(False, "", symbol, "SELL", quantity, price, "Max retries exceeded")
    
    def buy_with_amount(self, symbol: str, usd_amount: float,
                        exchange: str = "NASD") -> OrderResult:
        """
        Buy stock with specified USD amount
        
        Args:
            symbol: Stock ticker
            usd_amount: USD amount to invest
            exchange: Exchange code
            
        Returns:
            OrderResult
        """
        price = self.get_current_price(symbol, exchange)
        if price <= 0:
            return OrderResult(False, "", symbol, "BUY", 0, 0, "Could not get price")
        
        quantity = int(usd_amount / price)
        if quantity <= 0:
            return OrderResult(False, "", symbol, "BUY", 0, price,
                             f"${usd_amount:.2f} not enough for 1 share @ ${price:.2f}")
        
        limit_price = round(price * 1.002, 2)  # Slightly above market
        return self.buy_limit_order(symbol, quantity, limit_price, exchange)
    
    # ==============================================
    # Order Management (Cancel / Modify)
    # ==============================================
    
    def cancel_order(self, order_id: str, symbol: str, quantity: int,
                     exchange: str = "NASD") -> OrderResult:
        """
        Cancel a pending order
        
        Args:
            order_id: Original order number (ODNO from order response)
            symbol: Stock ticker
            quantity: Order quantity to cancel
            exchange: Exchange code
            
        Returns:
            OrderResult
        """
        tr_id = "VTTT1004U" if self.is_paper else "TTTT1004U"
        exchange = self.normalize_exchange(exchange)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order-rvsecncl"
        headers = self._get_headers(tr_id)
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORGN_ODNO": order_id,
            "RVSE_CNCL_DVSN_CD": "02",  # 02 = Cancel
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",  # 0 for cancel
            "ORD_SVR_DVSN_CD": "0"
        }
        
        logger.info("CANCEL order {} for {}", order_id, symbol)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    new_id = data.get("output", {}).get("ODNO", "")
                    logger.success("Cancel confirmed: {} (new ID: {})", symbol, new_id)
                    return OrderResult(True, new_id, symbol, "CANCEL", quantity, 0, "Cancelled")
                else:
                    msg = data.get("msg1", "Error")
                    logger.error("Cancel failed: {}", msg)
                    return OrderResult(False, "", symbol, "CANCEL", quantity, 0, msg)
                    
            except Exception as e:
                logger.warning("Cancel attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        return OrderResult(False, "", symbol, "CANCEL", quantity, 0, "Max retries exceeded")
    
    def modify_order(self, order_id: str, symbol: str, quantity: int,
                     new_price: float, exchange: str = "NASD") -> OrderResult:
        """
        Modify a pending order (change price/quantity)
        
        Args:
            order_id: Original order number
            symbol: Stock ticker
            quantity: New order quantity
            new_price: New limit price
            exchange: Exchange code
            
        Returns:
            OrderResult
        """
        tr_id = "VTTT1004U" if self.is_paper else "TTTT1004U"
        exchange = self.normalize_exchange(exchange)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order-rvsecncl"
        headers = self._get_headers(tr_id)
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORGN_ODNO": order_id,
            "RVSE_CNCL_DVSN_CD": "01",  # 01 = Modify
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": f"{new_price:.2f}",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        logger.info("MODIFY order {} -> {} x {} @ ${:.2f}", order_id, symbol, quantity, new_price)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    new_id = data.get("output", {}).get("ODNO", "")
                    logger.success("Modify confirmed: {} (new ID: {})", symbol, new_id)
                    return OrderResult(True, new_id, symbol, "MODIFY", quantity, new_price, "Modified")
                else:
                    msg = data.get("msg1", "Error")
                    logger.error("Modify failed: {}", msg)
                    return OrderResult(False, "", symbol, "MODIFY", quantity, new_price, msg)
                    
            except Exception as e:
                logger.warning("Modify attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        return OrderResult(False, "", symbol, "MODIFY", quantity, new_price, "Max retries exceeded")
    
    # ==============================================
    # Position & Account Queries
    # ==============================================
    
    def get_positions(self, exchange: str = "NASD") -> List[Dict]:
        """
        Get current stock positions (detailed holdings)
        
        Uses 해외주식 잔고 API (TTTS3012R/VTTS3012R)
        
        Returns:
            List of position dicts with keys:
            - symbol, name, quantity, avg_price, current_price, 
            - profit_loss, profit_rate, exchange
        """
        tr_id = "VTTS3012R" if self.is_paper else "TTTS3012R"
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": self.normalize_exchange(exchange),
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        positions = []
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Positions query failed: {}", data.get("msg1"))
                return positions
            
            positions_dict = {}
            for item in data.get("output1", []):
                qty = int(float(item.get("ovrs_cblc_qty", 0)))
                if qty <= 0:
                    continue
                
                symbol = item.get("ovrs_pdno", "")
                if symbol in positions_dict:
                    positions_dict[symbol]["quantity"] += qty
                    positions_dict[symbol]["sellable_qty"] += int(float(item.get("ord_psbl_qty", 0)))
                    positions_dict[symbol]["eval_amount"] += float(item.get("ovrs_stck_evlu_amt", 0))
                    positions_dict[symbol]["profit_loss"] += float(item.get("frcr_evlu_pfls_amt", 0))
                    positions_dict[symbol]["purchase_amount"] += float(item.get("frcr_pchs_amt1", 0))
                else:
                    positions_dict[symbol] = {
                        "symbol": symbol,
                        "name": item.get("ovrs_item_name", ""),
                        "quantity": qty,
                        "sellable_qty": int(float(item.get("ord_psbl_qty", 0))),
                        "avg_price": float(item.get("pchs_avg_pric", 0)),
                        "current_price": float(item.get("now_pric2", 0)),
                        "purchase_amount": float(item.get("frcr_pchs_amt1", 0)),
                        "eval_amount": float(item.get("ovrs_stck_evlu_amt", 0)),
                        "profit_loss": float(item.get("frcr_evlu_pfls_amt", 0)),
                        "profit_rate": float(item.get("evlu_pfls_rt", 0)),
                        "exchange": item.get("ovrs_excg_cd", ""),
                        "currency": item.get("tr_crcy_cd", "USD")
                    }
                    
            positions = list(positions_dict.values())
            
            logger.info("Found {} positions", len(positions))
            
        except Exception as e:
            logger.error("Positions query error: {}", e)
        
        return positions
    
    def get_order_history(self, start_date: str = None, end_date: str = None,
                          exchange: str = "NASD") -> List[Dict]:
        """
        Get order execution history
        
        Uses 해외주식 주문체결내역 API (TTTS3035R/VTTS3035R)
        
        Args:
            start_date: YYYYMMDD (default: today)
            end_date: YYYYMMDD (default: today)
            exchange: Exchange code
            
        Returns:
            List of order history dicts
        """
        tr_id = "VTTS3035R" if self.is_paper else "TTTS3035R"
        
        if not start_date:
            start_date = datetime.now().strftime("%Y%m%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "PDNO": "%",
            "ORD_STRT_DT": start_date,
            "ORD_END_DT": end_date,
            "SLL_BUY_DVSN": "00",
            "CCLD_NCCS_DVSN": "00",
            "OVRS_EXCG_CD": self.normalize_exchange(exchange),
            "SORT_SQN": "DS",
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_NK200": "",
            "CTX_AREA_FK200": ""
        }
        
        orders = []
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Order history query failed: {}", data.get("msg1"))
                return orders
            
            for item in data.get("output", []):
                orders.append({
                    "order_date": item.get("ord_dt", ""),
                    "order_id": item.get("odno", ""),
                    "symbol": item.get("pdno", ""),
                    "side": "BUY" if item.get("sll_buy_dvsn_cd") == "02" else "SELL",
                    "side_name": item.get("sll_buy_dvsn_cd_name", ""),
                    "status": item.get("rvse_cncl_dvsn", ""),
                    "order_time": item.get("ord_tmd", ""),
                    "exchange": item.get("ovrs_excg_cd", ""),
                })
            
            logger.info("Found {} orders in history", len(orders))
            
        except Exception as e:
            logger.error("Order history query error: {}", e)
        
        return orders
    
    def get_buyable_amount(self, symbol: str, price: float,
                           exchange: str = "NASD") -> Dict:
        """
        Get buyable amount for a specific stock at a given price
        
        Uses 해외주식 매수가능금액조회 API (TTTS3007R/VTTS3007R)
        
        Args:
            symbol: Stock ticker
            price: Target buy price
            exchange: Exchange code
            
        Returns:
            Dict with max_qty, available_usd, exchange_rate
        """
        tr_id = "VTTS3007R" if self.is_paper else "TTTS3007R"
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": self.normalize_exchange(exchange),
            "OVRS_ORD_UNPR": f"{price:.2f}",
            "ITEM_CD": symbol
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Buyable amount query failed: {}", data.get("msg1"))
                return {"max_qty": 0, "available_usd": 0, "exchange_rate": 0}
            
            output = data.get("output", {})
            result = {
                "max_qty": int(float(output.get("max_ord_psbl_qty", 0))),
                "available_usd": float(output.get("ovrs_ord_psbl_amt", 0)),
                "available_usd_total": float(output.get("frcr_ord_psbl_amt1", 0)),
                "exchange_rate": float(output.get("exrt", 0)),
                "currency": output.get("tr_crcy_cd", "USD")
            }
            
            logger.info("Buyable: {} shares of {} (${:,.2f} available)", 
                        result["max_qty"], symbol, result["available_usd"])
            return result
            
        except Exception as e:
            logger.error("Buyable amount query error for {}: {}", symbol, e)
            return {"max_qty": 0, "available_usd": 0, "exchange_rate": 0}
    
    # ==============================================
    # Convenience Order Methods
    # ==============================================
    
    def market_buy(self, symbol: str, quantity: int,
                   exchange: str = "NASD") -> OrderResult:
        """
        Place market buy order
        
        Note: For US stocks, uses LOO (limit-on-open) approach with 0 price
        Per API docs: market order sets OVRS_ORD_UNPR to "0"
        """
        tr_id = "VTTT1002U" if self.is_paper else "TTTT1002U"
        exchange = self.normalize_exchange(exchange)
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"
        headers = self._get_headers(tr_id)
        
        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        logger.info("MARKET BUY {} x {}", symbol, quantity)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("rt_cd") == "0":
                    order_id = data.get("output", {}).get("ODNO", "")
                    logger.success("Market buy placed: {} (ID: {})", symbol, order_id)
                    return OrderResult(True, order_id, symbol, "BUY", quantity, 0, "Market order")
                else:
                    msg = data.get("msg1", "Error")
                    logger.error("Market buy failed: {}", msg)
                    return OrderResult(False, "", symbol, "BUY", quantity, 0, msg)
                    
            except Exception as e:
                logger.warning("Market buy attempt {} failed: {}", attempt + 1, e)
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)
        
        return OrderResult(False, "", symbol, "BUY", quantity, 0, "Max retries exceeded")
    
    def sell_with_amount(self, symbol: str, usd_amount: float,
                         exchange: str = "NASD") -> OrderResult:
        """
        Sell stock worth a specified USD amount
        
        Args:
            symbol: Stock ticker
            usd_amount: USD amount to sell
            exchange: Exchange code
            
        Returns:
            OrderResult
        """
        price = self.get_current_price(symbol, exchange)
        if price <= 0:
            return OrderResult(False, "", symbol, "SELL", 0, 0, "Could not get price")
        
        quantity = int(usd_amount / price)
        if quantity <= 0:
            return OrderResult(False, "", symbol, "SELL", 0, price,
                             f"${usd_amount:.2f} not enough for 1 share @ ${price:.2f}")
        
        limit_price = round(price * 0.998, 2)  # Slightly below market for quick fill
        return self.sell_limit_order(symbol, quantity, limit_price, exchange)
    
    def sell_all(self, symbol: str, exchange: str = "NASD") -> OrderResult:
        """
        Sell all shares of a symbol
        
        Args:
            symbol: Stock ticker
            exchange: Exchange code
            
        Returns:
            OrderResult
        """
        # Get current position
        positions = self.get_positions(exchange)
        target = None
        for pos in positions:
            if pos["symbol"].upper() == symbol.upper():
                target = pos
                break
        
        if not target or target["sellable_qty"] <= 0:
            return OrderResult(False, "", symbol, "SELL", 0, 0, 
                             f"No sellable position for {symbol}")
        
        price = self.get_current_price(symbol, exchange)
        if price <= 0:
            price = target["current_price"]
        
        limit_price = round(price * 0.998, 2)
        return self.sell_limit_order(symbol, target["sellable_qty"], limit_price, exchange)
    
    # ==============================================
    # Shutdown
    # ==============================================
    
    def graceful_shutdown(self):
        """Graceful shutdown - stop threads and cleanup"""
        logger.info("Initiating graceful shutdown...")
        self.stop_auto_refresh()
        logger.info("KISClient shutdown complete")


# ==============================================
# Integration with MacroRiskManager
# ==============================================

def calculate_order_quantity(client: KISClient, 
                            macro_score: float,
                            symbol: str,
                            exchange: str = "NASD") -> int:
    """
    Calculate order quantity based on buying power and macro score
    
    Args:
        client: KISClient instance
        macro_score: Macro score (0-100)
        symbol: Stock ticker
        exchange: Exchange code
        
    Returns:
        int: Number of shares to buy
    """
    # Get buying power
    bp = client.check_buying_power()
    
    # Apply macro score multiplier
    if macro_score >= 80:
        multiplier = 1.0  # Full size
    elif macro_score >= 50:
        multiplier = 0.5  # Half size
    else:
        multiplier = 0.0  # No buy
    
    available = bp.usd_available * multiplier
    
    # Get current price
    price = client.get_current_price(symbol, exchange)
    if price <= 0:
        return 0
    
    quantity = int(available / price)
    
    logger.info("Order calc: ${:,.2f} * {:.0%} = ${:,.2f} / ${:.2f} = {} shares",
               bp.usd_available, multiplier, available, price, quantity)
    
    return quantity


# ==============================================
# Test
# ==============================================

if __name__ == "__main__":
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    print("=" * 50)
    print("KISClient Test")
    print("=" * 50)
    
    client = KISClient()
    
    print(f"\nPaper Trading: {client.is_paper}")
    print(f"Base URL: {client.base_url}")
    
    # Test token (will fail without valid credentials)
    try:
        token = client.get_access_token()
        print(f"Token: {token[:30]}...")
    except Exception as e:
        print(f"Token error (expected without valid .env): {e}")
