"""
Cost Model (Commission & Slippage)
====================================
Model real trading costs.
KIS Commission: 0.25%
"""

from dataclasses import dataclass
from loguru import logger


@dataclass
class TradeCost:
    commission: float       # $ amount
    commission_pct: float   # %
    slippage: float        # $ amount
    slippage_pct: float    # %
    total_cost: float
    total_cost_pct: float
    breakeven_move_pct: float  # Need this much move to break even


class CostModel:
    """
    Trading Cost Model
    
    KIS (한국투자증권):
    - Commission: 0.25% per trade
    - Round trip: 0.50%
    
    Slippage estimates:
    - Large cap: 0.05%
    - Mid cap: 0.10%
    - Small cap: 0.20%
    """
    
    # KIS commission
    COMMISSION_PCT = 0.0025  # 0.25%
    
    # Slippage by market cap
    SLIPPAGE = {
        'large': 0.0005,   # 0.05%
        'mid': 0.0010,     # 0.10%
        'small': 0.0020,   # 0.20%
        'micro': 0.0050    # 0.50%
    }
    
    def __init__(self, commission_pct: float = 0.0025):
        self.commission_pct = commission_pct
    
    def calculate_entry_cost(self, 
                             value: float,
                             cap_size: str = 'large') -> TradeCost:
        """Calculate cost for entry"""
        
        commission = value * self.commission_pct
        slippage_pct = self.SLIPPAGE.get(cap_size, 0.001)
        slippage = value * slippage_pct
        
        total = commission + slippage
        total_pct = (total / value) * 100 if value > 0 else 0
        
        return TradeCost(
            commission=commission,
            commission_pct=self.commission_pct * 100,
            slippage=slippage,
            slippage_pct=slippage_pct * 100,
            total_cost=total,
            total_cost_pct=total_pct,
            breakeven_move_pct=total_pct
        )
    
    def calculate_round_trip(self, 
                             value: float,
                             cap_size: str = 'large') -> TradeCost:
        """Calculate round-trip cost (buy + sell)"""
        
        commission = value * self.commission_pct * 2  # Both ways
        slippage_pct = self.SLIPPAGE.get(cap_size, 0.001)
        slippage = value * slippage_pct * 2  # Both ways
        
        total = commission + slippage
        total_pct = (total / value) * 100 if value > 0 else 0
        
        return TradeCost(
            commission=commission,
            commission_pct=self.commission_pct * 100 * 2,
            slippage=slippage,
            slippage_pct=slippage_pct * 100 * 2,
            total_cost=total,
            total_cost_pct=total_pct,
            breakeven_move_pct=total_pct
        )
    
    def estimate_cost(self, symbol: str, qty: int, price: float) -> float:
        """Estimate trading cost (commission + slippage)"""
        value = qty * price
        # Default to mid cap slippage if cap size is unknown
        cost_info = self.calculate_entry_cost(value, 'mid')
        return cost_info.total_cost
    
    def adjust_target(self, 
                      raw_target_pct: float,
                      cap_size: str = 'large') -> float:
        """Adjust profit target to account for costs"""
        
        rt_cost = self.calculate_round_trip(10000, cap_size)
        adjusted = raw_target_pct + rt_cost.total_cost_pct
        
        return adjusted
    
    def is_trade_worth_it(self,
                          expected_return_pct: float,
                          cap_size: str = 'large') -> tuple:
        """Check if expected return justifies costs"""
        
        rt_cost = self.calculate_round_trip(10000, cap_size)
        
        net_expected = expected_return_pct - rt_cost.total_cost_pct
        worth_it = net_expected > 0.5  # At least 0.5% after costs
        
        return worth_it, net_expected, rt_cost.total_cost_pct
    
    def get_cap_size(self, market_cap: float) -> str:
        """Determine cap size category"""
        if market_cap >= 10e9:  # $10B+
            return 'large'
        elif market_cap >= 2e9:  # $2B+
            return 'mid'
        elif market_cap >= 300e6:  # $300M+
            return 'small'
        else:
            return 'micro'


def get_cost_model(commission_pct: float = 0.0025) -> CostModel:
    return CostModel(commission_pct)


if __name__ == "__main__":
    print("Testing CostModel (KIS 0.25%)...")
    cm = CostModel()
    
    for value in [100000, 500000, 1500000]:  # KRW
        print(f"\n거래금액: ₩{value:,}")
        
        for cap in ['large', 'mid', 'small']:
            rt = cm.calculate_round_trip(value, cap)
            print(f"  {cap:6s}: 수수료 ₩{rt.commission:,.0f} + 슬리피지 ₩{rt.slippage:,.0f}")
            print(f"          총 ₩{rt.total_cost:,.0f} ({rt.total_cost_pct:.2f}%)")
            print(f"          손익분기: +{rt.breakeven_move_pct:.2f}%")
