"""
KIS API Integration
=====================
한국투자증권 해외주식 실제 매매 연동
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger

try:
    import mojito
    HAS_MOJITO = True
except ImportError:
    HAS_MOJITO = False
    logger.warning("mojito not installed. Run: pip install mojito")


@dataclass
class OrderResult:
    success: bool
    order_id: str
    symbol: str
    action: str
    quantity: int
    price: float
    message: str


@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    pnl_pct: float


class KISIntegration:
    """
    한국투자증권 API 연동
    
    Setup:
    1. pip install mojito
    2. Set environment variables:
       - KIS_APP_KEY
       - KIS_APP_SECRET
       - KIS_ACCOUNT_NO (format: "12345678-01")
       - KIS_MOCK (true for paper trading)
    """
    
    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY", "")
        self.app_secret = os.getenv("KIS_APP_SECRET", "")
        self.account = os.getenv("KIS_ACCOUNT_NO", "")
        self.mock = os.getenv("KIS_MOCK", "true").lower() == "true"
        
        self.broker = None
        self._init_broker()
    
    def _init_broker(self):
        if not HAS_MOJITO:
            logger.error("mojito not installed")
            return
        
        if not all([self.app_key, self.app_secret, self.account]):
            logger.warning("KIS credentials not configured")
            return
        
        try:
            self.broker = mojito.KoreaInvestment(
                api_key=self.app_key,
                api_secret=self.app_secret,
                acc_no=self.account,
                mock=self.mock,
                exchange="NASDAQ"
            )
            logger.info(f"KIS connected (Mock: {self.mock})")
        except Exception as e:
            logger.error(f"KIS connection failed: {e}")
    
    def buy(self, symbol: str, quantity: int, 
            order_type: str = "market") -> OrderResult:
        """매수 주문"""
        if not self.broker:
            return OrderResult(False, "", symbol, "BUY", quantity, 0, "Not connected")
        
        try:
            if order_type == "market":
                result = self.broker.create_market_buy_order(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                result = self.broker.create_limit_buy_order(
                    symbol=symbol,
                    quantity=quantity,
                    price=0  # Need to specify
                )
            
            success = result.get("rt_cd") == "0"
            order_id = result.get("output", {}).get("ODNO", "")
            
            logger.info(f"BUY {symbol} x{quantity}: {success}")
            
            return OrderResult(
                success=success,
                order_id=order_id,
                symbol=symbol,
                action="BUY",
                quantity=quantity,
                price=0,
                message=result.get("msg1", "")
            )
        except Exception as e:
            logger.error(f"Buy order failed: {e}")
            return OrderResult(False, "", symbol, "BUY", quantity, 0, str(e))
    
    def sell(self, symbol: str, quantity: int,
             order_type: str = "market") -> OrderResult:
        """매도 주문"""
        if not self.broker:
            return OrderResult(False, "", symbol, "SELL", quantity, 0, "Not connected")
        
        try:
            if order_type == "market":
                result = self.broker.create_market_sell_order(
                    symbol=symbol,
                    quantity=quantity
                )
            else:
                result = self.broker.create_limit_sell_order(
                    symbol=symbol,
                    quantity=quantity,
                    price=0
                )
            
            success = result.get("rt_cd") == "0"
            order_id = result.get("output", {}).get("ODNO", "")
            
            logger.info(f"SELL {symbol} x{quantity}: {success}")
            
            return OrderResult(
                success=success,
                order_id=order_id,
                symbol=symbol,
                action="SELL",
                quantity=quantity,
                price=0,
                message=result.get("msg1", "")
            )
        except Exception as e:
            logger.error(f"Sell order failed: {e}")
            return OrderResult(False, "", symbol, "SELL", quantity, 0, str(e))
    
    def get_balance(self) -> Dict:
        """잔고 조회"""
        if not self.broker:
            return {"error": "Not connected"}
        
        try:
            return self.broker.fetch_balance()
        except Exception as e:
            logger.error(f"Balance fetch failed: {e}")
            return {"error": str(e)}
    
    def get_positions(self) -> List[Position]:
        """보유 종목 조회"""
        if not self.broker:
            return []
        
        try:
            balance = self.broker.fetch_balance()
            positions = []
            
            for item in balance.get("output1", []):
                sym = item.get("pdno", "")
                qty = int(item.get("hldg_qty", 0))
                avg = float(item.get("pchs_avg_pric", 0))
                cur = float(item.get("ovrs_now_pric1", 0))
                
                if qty > 0:
                    pnl = (cur - avg) * qty
                    pnl_pct = (cur / avg - 1) * 100 if avg > 0 else 0
                    positions.append(Position(sym, qty, avg, cur, pnl, pnl_pct))
            
            return positions
        except Exception as e:
            logger.error(f"Position fetch failed: {e}")
            return []
    
    def get_price(self, symbol: str) -> float:
        """현재가 조회"""
        if not self.broker:
            return 0
        
        try:
            result = self.broker.fetch_price(symbol)
            return float(result.get("output", {}).get("last", 0))
        except:
            return 0


_kis = None

def get_kis() -> KISIntegration:
    global _kis
    if _kis is None:
        _kis = KISIntegration()
    return _kis


if __name__ == "__main__":
    print("Testing KISIntegration...")
    kis = KISIntegration()
    
    print(f"Mock mode: {kis.mock}")
    print(f"Connected: {kis.broker is not None}")
    
    if kis.broker:
        print(f"Balance: {kis.get_balance()}")
        print(f"Positions: {kis.get_positions()}")
