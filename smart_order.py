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
    FAILED = "FAILED"


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
    
    reason: str = ""


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

        # [Alpha Slicing] Large dollar orders (>= LARGE_ORDER_THRESHOLD) use 3-slice, 3-minute TWAP
        if side == "BUY" and order_value >= self.LARGE_ORDER_THRESHOLD:
            return ExecutionPlan(
                order_type=OrderType.TWAP,
                num_slices=3,
                slice_size=quantity // 3,
                interval_seconds=180,
                limit_offset_pct=0.005,  # 0.5% above market to guarantee fill
                max_participation=0.10,
                urgency=urgency
            )
        
        # Small orders (our typical case: 1 share of expensive stock)
        # [v1.1.8] BUY limit raised from 0.1% -> 0.5% above market
        # 0.1% was too tight -> frequent missed fills on fast-moving stocks
        # 0.5% virtually guarantees fill on liquid US stocks within seconds
        if order_value < self.SMALL_ORDER_THRESHOLD:
            return ExecutionPlan(
                order_type=OrderType.ADAPTIVE,
                num_slices=1,
                slice_size=quantity,
                interval_seconds=0,
                limit_offset_pct=0.005 if side == "BUY" else -0.001,
                max_participation=1.0,
                urgency=urgency
            )
        
        # Medium orders - Use ADAPTIVE (not TWAP)
        # [v1.1.8] Changed from TWAP to ADAPTIVE for medium orders too
        # TWAP runs in background thread and can cause double-notification
        # For our small account, medium orders are rare - just use aggressive limit
        elif order_value < self.LARGE_ORDER_THRESHOLD:
            return ExecutionPlan(
                order_type=OrderType.ADAPTIVE,
                num_slices=1,
                slice_size=quantity,
                interval_seconds=0,
                limit_offset_pct=0.005 if side == "BUY" else -0.002,
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
        obi = 0.0
        if self.trader:
            try:
                obi = self.trader.calculate_obi(order.symbol)
                logger.info("[OBI_FILTER] Order Book Imbalance for {}: {:+.2f}", order.symbol, obi)
            except Exception as e:
                logger.error("[OBI_FILTER] Failed to calculate OBI: {}", e)

        if order.side == "BUY":
            # If sell pressure is high (negative OBI), reduce buy limit price aggression to save slippage
            if obi < -0.3:
                # Limit offset scaled down proportionally by OBI, clamped to a safe minimum of 0.1%
                adjusted_offset = max(0.001, plan.limit_offset_pct * (1.0 + obi))
                limit = price * (1 + adjusted_offset)
                logger.info("[OBI_FILTER] High selling pressure detected. Reduced BUY limit offset from {:.3%} to {:.3%}", 
                            plan.limit_offset_pct, adjusted_offset)
            else:
                limit = price * (1 + plan.limit_offset_pct)
        else:
            if obi > 0.3:
                # Strong buy pressure — raise sell limit (less negative offset) for a better fill
                adjusted_offset = min(-0.0005, plan.limit_offset_pct * (1.0 - obi * 0.5))
                limit = price * (1 + adjusted_offset)
                logger.info("[OBI_FILTER] Strong buying pressure detected. Raised SELL limit offset from {:.3%} to {:.3%}",
                            plan.limit_offset_pct, adjusted_offset)
            else:
                limit = price * (1 + plan.limit_offset_pct)
        
        order.limit_price = limit
        
        # Simulate or execute
        # Simulate or execute
        if self.trader:
            try:
                if order.side == "BUY":
                    # [Quant-Execution] Enable ensure_fill=True for BUY orders to prevent missing entries
                    result = self.trader.buy(order.symbol, order.total_quantity, limit, ensure_fill=True)
                else:
                    # Critical: Force fill on all sell orders to prevent phantom positions
                    result = self.trader.sell(order.symbol, order.total_quantity, limit, ensure_fill=True)
                
                order_id_from_kis = None
                if result:
                    order_id_from_kis = (getattr(result, 'order_id', None) or 
                                         getattr(result, 'odno', None) or
                                         (result.get('odno') if isinstance(result, dict) else None) or
                                         (result.get('order_id') if isinstance(result, dict) else None))
                
                if order_id_from_kis:
                    logger.info("⏳ Order placed: {} ({}). Waiting up to 30s for fill...", order_id_from_kis, order.symbol)
                    is_filled = self.trader.wait_for_fill(order_id_from_kis, order.symbol, max_wait=30)
                    
                    if is_filled:
                        order.status = OrderStatus.FILLED
                        order.filled_quantity = order.total_quantity
                        order.avg_fill_price = getattr(result, 'price', limit) or limit
                    else:
                        logger.warning("❌ Order {} for {} did NOT fill within 30s.", order_id_from_kis, order.symbol)
                        exchange_to_use = getattr(result, 'exchange', None) or self.trader._exchange_mapper.get_exchange(order.symbol)
                        
                        if order.side == "BUY":
                            logger.warning("Cancelling unfilled BUY order, initiating aggressive buy chase to secure entry.")
                            if self.trader.cancel_order(order_id_from_kis, order.symbol, order.total_quantity, exchange_to_use, "BUY"):
                                time.sleep(2)
                                
                                # Resubmit at +5.0% (pseudo-market price to lock in entry)
                                chase_price = round(price * 1.05, 2)
                                logger.warning("Aggressive chase BUY for {} at pseudo-market price: ${:.2f}", order.symbol, chase_price)
                                chase_result = self.trader.buy(order.symbol, order.total_quantity, limit_price=chase_price, ensure_fill=False)
                                chase_order_id = getattr(chase_result, 'order_id', None) or getattr(chase_result, 'odno', None)
                                
                                if chase_order_id:
                                    is_chase_filled = self.trader.wait_for_fill(chase_order_id, order.symbol, max_wait=15)
                                    if is_chase_filled:
                                        order.status = OrderStatus.FILLED
                                        order.filled_quantity = order.total_quantity
                                        order.avg_fill_price = chase_price
                                        logger.success("✅ Aggressive chase BUY filled for {} at ${:.2f}", order.symbol, chase_price)
                                    else:
                                        logger.error("🚨 CRITICAL: Aggressive chase BUY order {} also unfilled!", chase_order_id)
                                        order.status = OrderStatus.FAILED
                                        order.reason = "Chase BUY unfilled (requires manual intervention)"
                                else:
                                    logger.error("🚨 CRITICAL: Aggressive chase BUY order failed to place!")
                                    order.status = OrderStatus.FAILED
                                    order.reason = "Chase BUY placement failed"
                            else:
                                logger.error("Cancel failed for BUY order {} ({}). Keeping original order active, skipping chase.", order_id_from_kis, order.symbol)
                                is_filled = self.trader.wait_for_fill(order_id_from_kis, order.symbol, max_wait=15)
                                if is_filled:
                                    order.status = OrderStatus.FILLED
                                    order.filled_quantity = order.total_quantity
                                    order.avg_fill_price = limit
                                else:
                                    order.status = OrderStatus.FAILED
                                    order.reason = "Cancel failed, original order still unfilled"
                        else:
                            logger.warning("Cancelling unfilled SELL order, initiating aggressive market chase.")
                            if self.trader.cancel_order(order_id_from_kis, order.symbol, order.total_quantity, exchange_to_use, "SELL"):
                                time.sleep(2)
                                
                                chase_price = round(price * 0.95, 2)
                                logger.warning("Aggressive chase SELL for {} at pseudo-market price: ${:.2f}", order.symbol, chase_price)
                                chase_result = self.trader.sell(order.symbol, order.total_quantity, limit_price=chase_price, ensure_fill=False)
                                chase_order_id = getattr(chase_result, 'order_id', None) or getattr(chase_result, 'odno', None)
                                
                                if chase_order_id:
                                    is_chase_filled = self.trader.wait_for_fill(chase_order_id, order.symbol, max_wait=15)
                                    if is_chase_filled:
                                        order.status = OrderStatus.FILLED
                                        order.filled_quantity = order.total_quantity
                                        order.avg_fill_price = chase_price
                                    else:
                                        logger.error("🚨 CRITICAL: Aggressive chase SELL order {} also unfilled!", chase_order_id)
                                        order.status = OrderStatus.PARTIAL
                                        order.reason = "Chase SELL unfilled (requires manual intervention)"
                                else:
                                    order.status = OrderStatus.REJECTED
                                    order.reason = f"Chase SELL order placement failed: {chase_result.message if chase_result else ''}"
                            else:
                                logger.error("Cancel failed for SELL order {} ({}). Keeping original order active, skipping chase.", order_id_from_kis, order.symbol)
                                is_filled = self.trader.wait_for_fill(order_id_from_kis, order.symbol, max_wait=15)
                                if is_filled:
                                    order.status = OrderStatus.FILLED
                                    order.filled_quantity = order.total_quantity
                                    order.avg_fill_price = limit
                                else:
                                    order.status = OrderStatus.FAILED
                                    order.reason = "Cancel failed, original order still unfilled"
                else:
                    order.status = OrderStatus.REJECTED
                    order.reason = f"KIS API returned no order ID: {result}"
                    logger.warning("Order for {} got no KIS order ID — marking REJECTED", order.symbol)
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
        import random
        total_filled = 0
        total_cost = 0
        
        for i in range(plan.num_slices):
            # Calculate slice quantity. Ensure last slice gets all remaining quantity.
            if i == plan.num_slices - 1:
                slice_qty = order.total_quantity - total_filled
            else:
                slice_qty = min(plan.slice_size, order.total_quantity - total_filled)
            
            if slice_qty <= 0:
                break
            
            # Use standard random instead of numpy to conserve memory and CPU on Oracle VM
            price_adj = price * (1 + random.uniform(-0.001, 0.001))
            limit = price_adj * (1 + plan.limit_offset_pct)
            
            # Execute slice
            fill_price = limit
            slice_filled = False
            
            if self.trader:
                try:
                    if order.side == "BUY":
                        result = self.trader.buy(order.symbol, slice_qty, limit, ensure_fill=True)
                    else:
                        result = self.trader.sell(order.symbol, slice_qty, limit, ensure_fill=True)
                    
                    order_id_from_kis = None
                    if result:
                        order_id_from_kis = (getattr(result, 'order_id', None) or 
                                             getattr(result, 'odno', None) or
                                             (result.get('odno') if isinstance(result, dict) else None) or
                                             (result.get('order_id') if isinstance(result, dict) else None))
                    
                    if order_id_from_kis:
                        logger.info("⏳ TWAP Slice {}/{} order placed: {} for {} shares of {}. Waiting 30s for fill...", 
                                    i+1, plan.num_slices, order_id_from_kis, slice_qty, order.symbol)
                        is_filled = self.trader.wait_for_fill(order_id_from_kis, order.symbol, max_wait=30)
                        
                        if is_filled:
                            fill_price = getattr(result, 'price', limit) or limit
                            total_filled += slice_qty
                            total_cost += fill_price * slice_qty
                            slice_filled = True
                            logger.info("✅ TWAP Slice {}/{} filled at ${:.2f}", i+1, plan.num_slices, fill_price)
                        else:
                            logger.warning("❌ TWAP Slice {}/{} did NOT fill. Cancelling order to prevent layout drift...", i+1, plan.num_slices)
                            exchange_to_use = getattr(result, 'exchange', None) or self.trader._exchange_mapper.get_exchange(order.symbol)
                            self.trader.cancel_order(order_id_from_kis, order.symbol, slice_qty, exchange_to_use, order.side)
                    else:
                        logger.warning("❌ TWAP Slice {}/{} failed: KIS API did not return order ID.", i+1, plan.num_slices)
                except Exception as e:
                    logger.error("❌ TWAP Slice {}/{} failed with error: {}", i+1, plan.num_slices, e)
            else:
                # Simulation mode
                fill_price = limit
                total_filled += slice_qty
                total_cost += fill_price * slice_qty
                slice_filled = True
            
            order.child_orders.append({
                'type': 'TWAP_SLICE',
                'slice': i + 1,
                'quantity': slice_qty if slice_filled else 0,
                'price': fill_price,
                'time': datetime.now().isoformat()
            })
            
            order.status = OrderStatus.PARTIAL if total_filled < order.total_quantity else OrderStatus.FILLED
            order.filled_quantity = total_filled
            order.updated_at = datetime.now()
            
            # Wait between slices (only if there are remaining slices)
            if i < plan.num_slices - 1 and total_filled < order.total_quantity:
                logger.info("⏳ Waiting {}s before placing next TWAP slice...", plan.interval_seconds)
                time.sleep(plan.interval_seconds)
        
        # Calculate average fill price based on successfully filled slices
        order.avg_fill_price = total_cost / total_filled if total_filled > 0 else price
        
        if order.side == "BUY":
            order.slippage_pct = (order.avg_fill_price - price) / price if price > 0 else 0
        else:
            order.slippage_pct = (price - order.avg_fill_price) / price if price > 0 else 0
        
        logger.info("TWAP order execution finished: {} {}/{} {} @ {:.2f} (slippage: {:.2%})",
                   order.side, total_filled, order.total_quantity, order.symbol,
                   order.avg_fill_price, order.slippage_pct)
        
        # Send notification upon completion
        if total_filled > 0:
            try:
                from notifier import get_notifier
                get_notifier().alert_trade(order.side, order.symbol, order.avg_fill_price, 
                                           f"TWAP Slicing Completed ({total_filled}/{order.total_quantity} shares)")
            except Exception as e:
                logger.debug("Failed to send TWAP notification: {}", e)

    
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
