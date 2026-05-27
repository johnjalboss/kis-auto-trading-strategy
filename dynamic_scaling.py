"""
Dynamic Position Scaling
==========================
Scale position sizes as capital grows.
"""

from dataclasses import dataclass
from typing import Dict
from loguru import logger
import config


@dataclass
class ScalingConfig:
    capital: float
    max_position_pct: float
    max_positions: int
    per_trade_risk_pct: float
    strategy: str


class DynamicScaler:
    """
    Dynamic Position Scaling
    
    Scale based on capital tiers:
    - <$3K: Focused (1-2 positions, 25%)
    - $3K-$10K: Growing (2-3 positions, 20%)
    - $10K-$30K: Diversified (3-5 positions, 15%)
    - $30K-$100K: Professional (5-8 positions, 10%)
    - >$100K: Institutional (8-12 positions, 8%)
    """
    
    TIERS = [
        (3000, ScalingConfig(3000, 0.30, 2, 0.02, "FOCUSED")),
        (10000, ScalingConfig(10000, 0.20, 3, 0.015, "GROWING")),
        (30000, ScalingConfig(30000, 0.15, 5, 0.01, "DIVERSIFIED")),
        (100000, ScalingConfig(100000, 0.10, 8, 0.008, "PROFESSIONAL")),
        (float('inf'), ScalingConfig(float('inf'), 0.08, 12, 0.005, "INSTITUTIONAL"))
    ]
    
    def __init__(self, initial_capital: float = 1500):
        self.capital = initial_capital
    
    def update_capital(self, new_capital: float):
        self.capital = new_capital
    
    def get_config(self) -> ScalingConfig:
        """Get scaling config for current capital"""
        for threshold, config in self.TIERS:
            if self.capital < threshold:
                return ScalingConfig(
                    capital=self.capital,
                    max_position_pct=config.max_position_pct,
                    max_positions=config.max_positions,
                    per_trade_risk_pct=config.per_trade_risk_pct,
                    strategy=config.strategy
                )
        return self.TIERS[-1][1]
    
    def calculate_position_size(self, 
                                price: float,
                                stop_loss: float,
                                conviction: int = 50) -> Dict:
        """Calculate position size based on capital and risk"""
        
        config = self.get_config()
        
        # Risk per trade
        risk_amount = self.capital * config.per_trade_risk_pct
        
        # Price-based risk
        per_share_risk = abs(price - stop_loss)
        
        if per_share_risk > 0:
            shares_by_risk = int(risk_amount / per_share_risk)
        else:
            shares_by_risk = 1
        
        # Max position limit
        max_position_value = self.capital * config.max_position_pct
        max_shares = int(max_position_value / price) if price > 0 else 1
        
        # Conviction scaling (0.5x to 1.5x)
        conviction_mult = 0.5 + (conviction / 100)
        
        # Final shares
        base_shares = min(shares_by_risk, max_shares)
        final_shares = max(1, int(base_shares * conviction_mult))
        
        position_value = final_shares * price
        position_pct = position_value / self.capital * 100
        
        return {
            'shares': final_shares,
            'value': position_value,
            'pct_of_capital': position_pct,
            'risk_amount': final_shares * per_share_risk,
            'risk_pct': (final_shares * per_share_risk) / self.capital * 100,
            'strategy': config.strategy,
            'max_positions': config.max_positions
        }
    
    def get_growth_plan(self) -> Dict:
        """Show growth plan milestones"""
        return {
            '$1.5K → $3K': 'Focus mode: 1-2 high conviction trades',
            '$3K → $10K': 'Add 1 more position, diversify sectors',
            '$10K → $30K': 'Professional diversification, reduce per-trade risk',
            '$30K → $100K': 'Institutional approach, multi-strategy',
            '$100K+': 'Full portfolio management'
        }


def get_scaler(capital: float = 1500) -> DynamicScaler:
    return DynamicScaler(capital)


if __name__ == "__main__":
    print("Testing DynamicScaler...")
    
    capitals = [1500, 5000, 15000, 50000, 150000]
    
    for cap in capitals:
        scaler = DynamicScaler(cap)
        config = scaler.get_config()
        
        print(f"\n{'='*50}")
        print(f"Capital: ${cap:,}")
        print('='*50)
        print(f"Strategy: {config.strategy}")
        print(f"Max Position: {config.max_position_pct:.0%}")
        print(f"Max Positions: {config.max_positions}")
        print(f"Risk/Trade: {config.per_trade_risk_pct:.1%}")
        
        pos = scaler.calculate_position_size(150.0, 145.0, 70)
        print(f"\nExample (AAPL $150, stop $145, 70% conviction):")
        print(f"  Shares: {pos['shares']}")
        print(f"  Value: ${pos['value']:,.0f} ({pos['pct_of_capital']:.1f}%)")
        print(f"  Risk: ${pos['risk_amount']:,.0f} ({pos['risk_pct']:.1f}%)")
