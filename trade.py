"""
Trade Manager for KIS API
Handles order execution, position management, and account queries
"""

import requests
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from loguru import logger

import config
from auth import get_auth
from utils import normalize_exchange, get_exchange_for_symbol, format_price, format_percent


@dataclass
class Position:
    """Represents a stock position"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    exchange: str
    entry_date: Optional[datetime] = None
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price
    
    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis
    
    @property
    def pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.current_price - self.avg_price) / self.avg_price


@dataclass  
class OrderResult:
    """Result of an order execution"""
    success: bool
    order_id: Optional[str] = None
    symbol: str = ""
    side: str = ""  # BUY or SELL
    quantity: int = 0
    price: float = 0.0
    message: str = ""
    raw_response: dict = field(default_factory=dict)


class TradeManager:
    """Manages trading operations via KIS API"""
    
    def __init__(self):
        self.auth = get_auth()
        self.base_url = config.BASE_URL
        self.account_no = config.KIS_CANO
        self.account_cd = config.KIS_ACNT_PRDT_CD
        
    def _get_headers(self, tr_id: str) -> dict:
        """Get headers for API request with transaction ID
        
        Args:
            tr_id: Transaction ID for the API call
            
        Returns:
            dict: Headers with auth and transaction ID
        """
        headers = self.auth.get_auth_headers()
        headers["tr_id"] = tr_id
        return headers
    
    # ==============================================
    # Account Queries
    # ==============================================
    
    def get_available_cash(self) -> float:
        """Get available USD cash for trading
        
        Returns:
            float: Available cash in USD
        """
        # Transaction ID for overseas available cash inquiry
        if config.IS_PAPER_TRADING:
            tr_id = "VTTS3007R"  # Paper trading
        else:
            tr_id = "TTTS3007R"  # Live trading
        
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_cd,
            "WCRC_FRCR_DVSN_CD": "02",  # USD
            "NATN_CD": "840",  # USA
            "TR_MKET_CD": "00",
            "INQR_DVSN_CD": "00"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Failed to get available cash: {}", data.get("msg1"))
                return 0.0
            
            output = data.get("output2", [{}])
            if output:
                # psbl_frcr_ord_amt = available foreign currency order amount
                cash = float(output[0].get("frcr_dncl_amt_2", 0))
                logger.info("Available USD: {}", format_price(cash))
                return cash
            
            return 0.0
            
        except Exception as e:
            logger.error("Error getting available cash: {}", e)
            return 0.0
    
    def get_total_equity(self) -> float:
        """Get total account equity in USD
        
        Returns:
            float: Total equity (cash + positions)
        """
        cash = self.get_available_cash()
        positions = self.get_positions()
        
        positions_value = sum(p.market_value for p in positions)
        total = cash + positions_value
        
        logger.info("Total equity: {} (Cash: {}, Positions: {})",
                   format_price(total), format_price(cash), format_price(positions_value))
        return total
    
    def get_positions(self) -> List[Position]:
        """Get all current positions
        
        Returns:
            List of Position objects
        """
        # Transaction ID for overseas holdings inquiry
        if config.IS_PAPER_TRADING:
            tr_id = "VTTS3012R"
        else:
            tr_id = "TTTS3012R"
        
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
        
        positions = []
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Failed to get positions: {}", data.get("msg1"))
                return positions
            
            for item in data.get("output1", []):
                qty = int(item.get("ovrs_cblc_qty", 0))
                if qty > 0:
                    pos = Position(
                        symbol=item.get("ovrs_pdno", ""),
                        quantity=qty,
                        avg_price=float(item.get("pchs_avg_pric", 0)),
                        current_price=float(item.get("ovrs_stck_evlu_amt", 0)) / qty if qty else 0,
                        exchange=normalize_exchange(item.get("ovrs_excg_cd", "NAS"))
                    )
                    positions.append(pos)
                    logger.debug("Position: {} x {} @ {}",
                               pos.symbol, pos.quantity, format_price(pos.avg_price))
            
            return positions
            
        except Exception as e:
            logger.error("Error getting positions: {}", e)
            return positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Position or None if not held
        """
        positions = self.get_positions()
        for pos in positions:
            if pos.symbol == symbol:
                return pos
        return None
    
    # ==============================================
    # Order Execution
    # ==============================================
    
    def place_limit_buy(self, symbol: str, quantity: int, price: float, 
                        exchange: str = None) -> OrderResult:
        """Place a limit buy order
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares
            price: Limit price in USD
            exchange: Exchange code (auto-detected if not provided)
            
        Returns:
            OrderResult with execution details
        """
        if exchange is None:
            exchange = get_exchange_for_symbol(symbol)
        exchange = normalize_exchange(exchange)
        
        # Transaction ID for overseas stock buy
        if config.IS_PAPER_TRADING:
            tr_id = "VTTT1002U"
        else:
            tr_id = "TTTT1002U"
        
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
            "ORD_DVSN": "00"  # Limit order
        }
        
        logger.info("Placing BUY order: {} x {} @ {} on {}",
                   symbol, quantity, format_price(price), exchange)
        
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") == "0":
                order_id = data.get("output", {}).get("ODNO", "")
                logger.success("BUY order placed: {} (ID: {})", symbol, order_id)
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=price,
                    message="Order placed successfully",
                    raw_response=data
                )
            else:
                msg = data.get("msg1", "Unknown error")
                logger.error("BUY order failed: {}", msg)
                return OrderResult(
                    success=False,
                    symbol=symbol,
                    side="BUY",
                    message=msg,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error("BUY order error: {}", e)
            return OrderResult(success=False, symbol=symbol, side="BUY", message=str(e))
    
    def place_limit_sell(self, symbol: str, quantity: int, price: float,
                         exchange: str = None) -> OrderResult:
        """Place a limit sell order
        
        Args:
            symbol: Stock ticker
            quantity: Number of shares
            price: Limit price in USD
            exchange: Exchange code (auto-detected if not provided)
            
        Returns:
            OrderResult with execution details
        """
        if exchange is None:
            exchange = get_exchange_for_symbol(symbol)
        exchange = normalize_exchange(exchange)
        
        # Transaction ID for overseas stock sell
        if config.IS_PAPER_TRADING:
            tr_id = "VTTT1001U"
        else:
            tr_id = "TTTT1006U"
        
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
            "ORD_DVSN": "00"  # Limit order
        }
        
        logger.info("Placing SELL order: {} x {} @ {} on {}",
                   symbol, quantity, format_price(price), exchange)
        
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") == "0":
                order_id = data.get("output", {}).get("ODNO", "")
                logger.success("SELL order placed: {} (ID: {})", symbol, order_id)
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    price=price,
                    message="Order placed successfully",
                    raw_response=data
                )
            else:
                msg = data.get("msg1", "Unknown error")
                logger.error("SELL order failed: {}", msg)
                return OrderResult(
                    success=False,
                    symbol=symbol,
                    side="SELL",
                    message=msg,
                    raw_response=data
                )
                
        except Exception as e:
            logger.error("SELL order error: {}", e)
            return OrderResult(success=False, symbol=symbol, side="SELL", message=str(e))
    
    # ==============================================
    # Position Sizing
    # ==============================================
    
    def calculate_order_quantity(self, symbol: str, price: float) -> int:
        """Calculate order quantity respecting position size limits
        
        Args:
            symbol: Stock ticker
            price: Current/target price
            
        Returns:
            int: Number of shares to order (0 if limit exceeded)
        """
        total_equity = self.get_total_equity()
        if total_equity <= 0:
            logger.warning("Cannot calculate order qty: no equity")
            return 0
        
        # Max position value = 20% of total equity
        max_position_value = total_equity * config.MAX_POSITION_PCT
        
        # Check existing position
        existing = self.get_position(symbol)
        existing_value = existing.market_value if existing else 0
        
        # Available allocation
        available_value = max_position_value - existing_value
        
        if available_value <= 0:
            logger.warning("{} position at max limit ({})", 
                          symbol, format_percent(config.MAX_POSITION_PCT))
            return 0
        
        # Also check available cash
        cash = self.get_available_cash()
        order_value = min(available_value, cash)
        
        if order_value < price:
            logger.warning("Insufficient funds for {} (need {}, have {})",
                          symbol, format_price(price), format_price(cash))
            return 0
        
        quantity = int(order_value / price)
        
        logger.info("Order sizing for {}: {} shares @ {} = {} (max allocation: {})",
                   symbol, quantity, format_price(price), 
                   format_price(quantity * price), format_price(max_position_value))
        
        return quantity
    
    # ==============================================
    # Price Data
    # ==============================================
    
    def get_current_price(self, symbol: str, exchange: str = None) -> float:
        """Get current price for a symbol
        
        Args:
            symbol: Stock ticker
            exchange: Exchange code
            
        Returns:
            float: Current price in USD
        """
        if exchange is None:
            exchange = get_exchange_for_symbol(symbol)
        exchange = normalize_exchange(exchange)
        
        # Transaction ID for overseas price inquiry
        tr_id = "HHDFS00000300"
        
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") == "0":
                output = data.get("output", {})
                price = float(output.get("last", 0))
                logger.debug("{} current price: {}", symbol, format_price(price))
                return price
            else:
                logger.error("Failed to get price for {}: {}", symbol, data.get("msg1"))
                return 0.0
                
        except Exception as e:
            logger.error("Error getting price for {}: {}", symbol, e)
            return 0.0
    
    def get_price_history(self, symbol: str, days: int = 50, exchange: str = None) -> Optional[dict]:
        """Get historical daily price data
        
        Args:
            symbol: Stock ticker
            days: Number of days of history
            exchange: Exchange code
            
        Returns:
            DataFrame with OHLCV data or None
        """
        if exchange is None:
            exchange = get_exchange_for_symbol(symbol)
        exchange = normalize_exchange(exchange)
        
        # Transaction ID for overseas daily price
        tr_id = "HHDFS76240000"
        
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/dailyprice"
        
        headers = self._get_headers(tr_id)
        
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "GUBN": "0",  # Daily
            "BYMD": "",   # End date (empty = today)
            "MODP": "1"   # Adjusted price
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("rt_cd") != "0":
                logger.error("Failed to get history for {}: {}", symbol, data.get("msg1"))
                return None
            
            import pandas as pd
            
            records = []
            for item in data.get("output2", [])[:days]:
                records.append({
                    "date": item.get("xymd"),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("clos", 0)),
                    "volume": int(item.get("tvol", 0))
                })
            
            if not records:
                return None
            
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            
            logger.debug("Got {} days of history for {}", len(df), symbol)
            return df
            
        except Exception as e:
            logger.error("Error getting history for {}: {}", symbol, e)
            return None


if __name__ == "__main__":
    # Test trade manager
    print("=" * 60)
    print("Testing Trade Manager")
    print("=" * 60)
    
    print(f"\nEnvironment: {'Paper Trading' if config.IS_PAPER_TRADING else 'LIVE TRADING'}")
    print(f"Base URL: {config.BASE_URL}")
    
    trader = TradeManager()
    
    # These will only work with valid API credentials
    print("\nTesting price query...")
    for symbol in ["AAPL", "TSLA"]:
        price = trader.get_current_price(symbol)
        print(f"  {symbol}: {format_price(price)}")
    
    print("\n✅ Trade Manager initialized")
