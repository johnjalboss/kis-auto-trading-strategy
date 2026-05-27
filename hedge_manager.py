"""
Hedge Manager
===============
Manage portfolio hedges (VIX, Gold, Bonds).
"""

from dataclasses import dataclass
from typing import List, Dict
import yfinance as yf
from loguru import logger


@dataclass 
class HedgeAllocation:
    instrument: str
    etf: str
    allocation_pct: float
    current_value: float
    target_value: float
    action: str  # "BUY", "SELL", "HOLD"
    rebalance_amount: float


class HedgeManager:
    """
    Portfolio Hedge Manager
    
    Hedge Instruments:
    - VIX: UVXY/VIXY (volatility)
    - Gold: GLD (safe haven)
    - Bonds: TLT (rates)
    - Inverse: SH/SPXU (market hedge)
    - Cash: (opportunity)
    
    Dynamic allocation based on market regime
    """
    
    INSTRUMENTS = {
        'VIX': {'etf': 'UVXY', 'normal': 0.0, 'fear': 0.02, 'crisis': 0.05},
        'GOLD': {'etf': 'GLD', 'normal': 0.03, 'fear': 0.05, 'crisis': 0.08},
        'BONDS': {'etf': 'TLT', 'normal': 0.02, 'fear': 0.05, 'crisis': 0.10},
        'INVERSE': {'etf': 'SH', 'normal': 0.0, 'fear': 0.02, 'crisis': 0.08},
        'CASH': {'etf': None, 'normal': 0.05, 'fear': 0.15, 'crisis': 0.25}
    }
    
    def __init__(self, portfolio_value: float):
        self.portfolio_value = portfolio_value
        self.current_hedges: Dict[str, float] = {}
    
    def get_allocation(self, regime: str) -> List[HedgeAllocation]:
        """Get hedge allocation for regime"""
        
        allocations = []
        regime_key = self._regime_to_key(regime)
        
        for name, config in self.INSTRUMENTS.items():
            target_pct = config[regime_key]
            target_value = self.portfolio_value * target_pct
            current = self.current_hedges.get(name, 0)
            
            diff = target_value - current
            if diff > 100:
                action = "BUY"
            elif diff < -100:
                action = "SELL"
            else:
                action = "HOLD"
            
            allocations.append(HedgeAllocation(
                instrument=name,
                etf=config['etf'],
                allocation_pct=target_pct * 100,
                current_value=current,
                target_value=target_value,
                action=action,
                rebalance_amount=diff
            ))
        
        return allocations
    
    def update_portfolio(self, new_value: float):
        self.portfolio_value = new_value
    
    def update_hedge(self, instrument: str, value: float):
        self.current_hedges[instrument] = value
    
    def get_total_hedge_pct(self) -> float:
        total = sum(self.current_hedges.values())
        return (total / self.portfolio_value * 100) if self.portfolio_value > 0 else 0
    
    def _regime_to_key(self, regime: str) -> str:
        regime = regime.upper()
        if regime in ['BEAR', 'HIGH_VOLATILITY', 'CRASH']:
            return 'crisis'
        elif regime in ['CORRECTION', 'UNCERTAIN', 'FEAR']:
            return 'fear'
        else:
            return 'normal'


def get_hedge_manager(value: float = 100000) -> HedgeManager:
    return HedgeManager(value)


if __name__ == "__main__":
    print("Testing HedgeManager...")
    hm = HedgeManager(1500000)  # ₩150만
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        print(f"\n{'='*50}")
        print(f"Regime: {regime}")
        print('='*50)
        
        allocs = hm.get_allocation(regime)
        for a in allocs:
            if a.allocation_pct > 0:
                print(f"  {a.instrument}: {a.allocation_pct:.1f}% = ₩{a.target_value:,.0f}")
