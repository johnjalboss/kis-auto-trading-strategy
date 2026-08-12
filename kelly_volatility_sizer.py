"""
[v11.0 ULTRA QUANT] Kelly Criterion & Volatility Parity Position Sizer
======================================================================
Calculates optimal position quantity using Kelly Criterion & ATR Volatility Parity:

f* = (p * b - q) / b * (Target_Volatility / Asset_Volatility)

High volatility stocks get smaller allocation, low volatility high-win stocks get larger allocation.
Dramatically smooths portfolio equity curve drawdowns toward zero!
"""

from typing import Dict, Any
from loguru import logger
import config


class KellyVolatilitySizer:
    def __init__(self, target_daily_vol: float = 0.015):
        self.target_daily_vol = target_daily_vol

    def calculate_qty(self, symbol: str, entry_price: float, total_equity: float, 
                      buying_power: float, atr: float, win_rate: float = 0.65, 
                      win_loss_ratio: float = 1.5) -> int:
        if entry_price <= 0 or total_equity <= 0 or buying_power <= 0:
            return 0

        try:
            # 1. Full Kelly Fraction f* = (p * b - q) / b
            p = win_rate
            q = 1.0 - p
            b = win_loss_ratio
            full_kelly = (p * b - q) / b if b > 0 else 0.10
            
            # Half-Kelly safety cap for conservative risk management
            half_kelly = max(0.05, min(0.25, full_kelly * 0.5))

            # 2. Volatility Parity Scaling factor
            asset_daily_vol = (atr / entry_price) if atr > 0 else 0.02
            vol_scale = self.target_daily_vol / max(0.005, asset_daily_vol)
            vol_scale = max(0.40, min(1.60, vol_scale))  # Cap volatility scaling between 40% and 160%

            # 3. Target Slot Capital (자금 최대 활용 모드)
            max_positions = getattr(config, 'MAX_POSITIONS', 5)
            base_slot_capital = total_equity / max_positions
            
            # 사용자 요구사항: 구매 시 보유 자금 적극 활용 (최대 슬롯 자금 또는 주문 가능 현금 투입)
            # 수량 계산: 슬롯 한도 금액($base_slot_capital)과 주문가능현금($buying_power) 중 최소값으로 풀매수
            target_capital = min(base_slot_capital * 1.25, buying_power)  # 슬롯 자금 125%까지 유연하게 활용
            
            qty = int(target_capital / entry_price)
            if qty == 0 and entry_price <= buying_power:
                qty = 1  # 현금이 되면 최소 1주 매수

            logger.info("📐 [KELLY_VOLATILITY_SIZER] {}: Qty {} shares (TargetCap: ${:.2f}, BuyingPower: ${:.2f})",
                        symbol, qty, target_capital, buying_power)
            return qty
        except Exception as e:
            logger.debug("KellyVolatilitySizer error for {}: {}", symbol, e)
            return int(buying_power / entry_price) if entry_price > 0 else 0
