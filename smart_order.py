"""
Smart Order Execution
======================
Minimize slippage and optimize order execution.

Features:
1. TWAP (Time-Weighted Average Price)
2. VWAP Targeting
3. Iceberg Orders (split large orders)
4. Adaptive Limit Orders
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from enum import Enum
import time
from loguru import logger


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"
    VWAP = "VWAP"
    ICEBERG = "ICEBERG"
    ADAPTIVE = "ADAPTIVE"


class OrderStatus(Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class SmartOrder:
    """Smart order structure"""
    order_id: str
    symbol: str
    side: str  # "BUY" or "SELL"
    total_quantity: int
    filled_quantity: int
    order_type: OrderType
    limit_price: Optional[float]
    status: OrderStatus
    
    # Execution details
    child_orders: List[dict]
    avg_fill_price: float
    slippage_pct: float
    
    # Timing
    created_at: datetime
    updated_at: datetime


@dataclass
class ExecutionPlan:
    """Execution plan for smart order"""
    order_type: OrderType
    num_slices: int
    slice_size: int
    interval_seconds: int
    limit_offset_pct: float
    max_participation: float  # Max % of ADV
    urgency: str  # "LOW", "MEDIUM", "HIGH"


class SmartOrderExecutor:
    """
    Smart Order Execution Engine
    
    Strategies:
    1. TWAP - Split order over time evenly
    2. VWAP - Weight by expected volume
    3. Iceberg - Hide large orders
    4. Adaptive - Dynamic limit pricing
    
    Slippage Reduction:
    - Use limit orders when possible
    - Split large orders
    - Time execution optimally
    """
    
    # ADV (Average Daily Volume) participation limits
    MAX_ADV_PARTICIPATION = 0.10  # Max 10% of daily volume
    
    # Order sizing thresholds
    SMALL_ORDER_THRESHOLD = 1000  # $1000
    LARGE_ORDER_THRESHOLD = 10000  # $10000
    
    def __init__(self, trader=None):
        """
        Args:
            trader: Trader instance for order execution
        """
        self.trader = trader
        self._orders: Dict[str, SmartOrder] = {}
        self._order_counter = 0
    
    def create_execution_plan(self, symbol: str, side: str,
                             quantity: int, current_price: float,
                             urgency: str = "MEDIUM") -> ExecutionPlan:
        """
        Create optimal execution plan based on order size
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            current_price: Current market price
            urgency: LOW, MEDIUM, HIGH
        """
        order_value = quantity * current_price
        
        # Small orders - Just use limit
        if order_value < self.SMALL_ORDER_THRESHOLD:
            return ExecutionPlan(
                order_type=OrderType.ADAPTIVE,
                num_slices=1,
                slice_size=quantity,
                interval_seconds=0,
                limit_offset_pct=0.001 if side == "BUY" else -0.001,
                max_participation=1.0,
                urgency=urgency
            )
        
        # Medium orders - Use TWAP
        elif order_value < self.LARGE_ORDER_THRESHOLD:
            num_slices = 3
            return ExecutionPlan(
                order_type=OrderType.TWAP,
                num_slices=num_slices,
                slice_size=quantity // num_slices,
                interval_seconds=60,  # 1 minute apart
                limit_offset_pct=0.002 if side == "BUY" else -0.002,
                max_participation=0.05,
                urgency=urgency
            )
        
        # Large orders - Use Iceberg
        else:
            num_slices = min(10, max(5, quantity // 100))
            interval = 30 if urgency == "HIGH" else 120 if urgency == "LOW" else 60
            
            return ExecutionPlan(
                order_type=OrderType.ICEBERG,
                num_slices=num_slices,
                slice_size=quantity // num_slices,
                interval_seconds=interval,
                limit_offset_pct=0.003 if side == "BUY" else -0.003,
                max_participation=0.03,
                urgency=urgency
            )
    
    def execute(self, symbol: str, side: str, quantity: int,
               current_price: float, plan: Optional[ExecutionPlan] = None) -> SmartOrder:
        """
        Execute order using smart execution strategy
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            current_price: Current market price
            plan: Execution plan (optional, will create if not provided)
        """
        if plan is None:
            plan = self.create_execution_plan(symbol, side, quantity, current_price)
        
        # Generate order ID
        self._order_counter += 1
        order_id = f"SMT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_counter}"
        
        smart_order = SmartOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            total_quantity=quantity,
            filled_quantity=0,
            order_type=plan.order_type,
            limit_price=None,
            status=OrderStatus.PENDING,
            child_orders=[],
            avg_fill_price=0,
            slippage_pct=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._orders[order_id] = smart_order
        
        import threading
        
        # Execute based on order type
        if plan.order_type == OrderType.ADAPTIVE:
            self._execute_adaptive(smart_order, current_price, plan)
        elif plan.order_type == OrderType.TWAP:
            threading.Thread(target=self._execute_twap, args=(smart_order, current_price, plan), daemon=True).start()
        elif plan.order_type == OrderType.ICEBERG:
            threading.Thread(target=self._execute_iceberg, args=(smart_order, current_price, plan), daemon=True).start()
        else:
            self._execute_market(smart_order, current_price)
        
        return smart_order
    
    def _execute_adaptive(self, order: SmartOrder, price: float, plan: ExecutionPlan):
        """Execute with adaptive limit order"""
        if order.side == "BUY":
            limit = price * (1 + plan.limit_offset_pct)
        else:
            limit = price * (1 + plan.limit_offset_pct)
        
        order.limit_price = limit
        
        # Simulate or execute
        if self.trader:
            try:
                if order.side == "BUY":
                    result = self.trader.buy(order.symbol, order.total_quantity, limit)
                else:
                    # Critical: Force fill on all sell orders to prevent phantom positions
                    result = self.trader.sell(order.symbol, order.total_quantity, limit, ensure_fill=True)
                    
                if result and getattr(result, 'success', False):
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.total_quantity
                    order.avg_fill_price = getattr(result, 'fill_price', price)
                else:
                    order.status = OrderStatus.REJECTED
                    order.reason = "API order creation failed"
            except Exception as e:
                logger.error("Adaptive order failed: {}", e)
                order.status = OrderStatus.REJECTED
                order.reason = str(e)
        else:
            # Simulation
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.total_quantity
            order.avg_fill_price = limit
        
        # Calculate slippage
        if order.avg_fill_price > 0:
            if order.side == "BUY":
                order.slippage_pct = (order.avg_fill_price - price) / price
            else:
                order.slippage_pct = (price - order.avg_fill_price) / price
        
        order.updated_at = datetime.now()
        order.child_orders.append({
            'type': 'LIMIT',
            'quantity': order.total_quantity,
            'price': limit,
            'filled': order.filled_quantity,
            'time': datetime.now().isoformat()
        })
        
        logger.info("Adaptive order executed: {} {} {} @ {:.2f} (slippage: {:.2%})",
                   order.side, order.total_quantity, order.symbol,
                   order.avg_fill_price, order.slippage_pct)
    
    def _execute_twap(self, order: SmartOrder, price: float, plan: ExecutionPlan):
        """Execute using Time-Weighted Average Price"""
        total_filled = 0
        total_cost = 0
        
        for i in range(plan.num_slices):
            slice_qty = min(plan.slice_size, order.total_quantity - total_filled)
            
            if slice_qty <= 0:
                break
            
            # Simulate slight price movement
            price_adj = price * (1 + np.random.uniform(-0.001, 0.001))
            
            if order.side == "BUY":
                limit = price_adj * (1 + plan.limit_offset_pct)
            else:
                limit = price_adj * (1 + plan.limit_offset_pct)
            
            # Execute slice
            if self.trader:
                try:
                    if order.side == "BUY":
                        result = self.trader.buy(order.symbol, slice_qty, limit)
                    else:
                        # Critical: Force fill on sell slices
                        result = self.trader.sell(order.symbol, slice_qty, limit, ensure_fill=True)
                    
                    fill_price = result.get('fill_price', limit)
                except:
                    fill_price = limit
            else:
                fill_price = limit
            
            total_filled += slice_qty
            total_cost += fill_price * slice_qty
            
            order.child_orders.append({
                'type': 'TWAP_SLICE',
                'slice': i + 1,
                'quantity': slice_qty,
                'price': fill_price,
                'time': datetime.now().isoformat()
            })
            
            order.status = OrderStatus.PARTIAL if total_filled < order.total_quantity else OrderStatus.FILLED
            order.filled_quantity = total_filled
            order.updated_at = datetime.now()
            
            # Wait between slices (in real execution)
            time.sleep(plan.interval_seconds)
        
        # Calculate average
        order.avg_fill_price = total_cost / total_filled if total_filled > 0 else price
        
        if order.side == "BUY":
            order.slippage_pct = (order.avg_fill_price - price) / price
        else:
            order.slippage_pct = (price - order.avg_fill_price) / price
        
        logger.info("TWAP order executed: {} {} {} @ {:.2f} (slippage: {:.2%})",
                   order.side, total_filled, order.symbol,
                   order.avg_fill_price, order.slippage_pct)
        
        # Send notification after first slice or completion
        if total_filled > 0:
            try:
                from notification import get_notifier
                get_notifier().alert_trade(order.side, order.symbol, order.avg_fill_price, "TWAP Execution Completed")
            except Exception:
                pass

    
    def _execute_iceberg(self, order: SmartOrder, price: float, plan: ExecutionPlan):
        """Execute using Iceberg strategy"""
        # Similar to TWAP but with smaller visible slices
        self._execute_twap(order, price, plan)
        logger.info("Iceberg order completed (hidden: {} slices)", plan.num_slices)
    
    def _execute_market(self, order: SmartOrder, price: float):
        """Execute as market order (fallback)"""
        order.avg_fill_price = price * 1.001  # Assume 0.1% slippage
        order.filled_quantity = order.total_quantity
        order.status = OrderStatus.FILLED
        order.slippage_pct = 0.001
        order.updated_at = datetime.now()
        
        logger.info("Market order executed: {} {} {} @ {:.2f}",
                   order.side, order.total_quantity, order.symbol, order.avg_fill_price)
    
    def get_order(self, order_id: str) -> Optional[SmartOrder]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        order = self._orders.get(order_id)
        if order and order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.now()
            return True
        return False


import numpy as np

# Global instance
_executor = None

def get_smart_executor(trader=None) -> SmartOrderExecutor:
    global _executor
    if _executor is None:
        _executor = SmartOrderExecutor(trader)
    return _executor


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing SmartOrderExecutor...")
    
    executor = SmartOrderExecutor()
    
    # Test different order sizes
    test_cases = [
        ("AAPL", "BUY", 5, 150.0, "Small order"),
        ("TSLA", "BUY", 50, 200.0, "Medium order"),
        ("NVDA", "BUY", 200, 500.0, "Large order"),
    ]
    
    for symbol, side, qty, price, desc in test_cases:
        print(f"\n{'='*50}")
        print(f"{desc}: {qty} shares @ ${price}")
        print('='*50)
        
        plan = executor.create_execution_plan(symbol, side, qty, price)
        print(f"Strategy: {plan.order_type.value}")
        print(f"Slices: {plan.num_slices}")
        print(f"Interval: {plan.interval_seconds}s")
        
        order = executor.execute(symbol, side, qty, price, plan)
        print(f"Status: {order.status.value}")
        print(f"Avg Price: ${order.avg_fill_price:.2f}")
        print(f"Slippage: {order.slippage_pct:.3%}")
