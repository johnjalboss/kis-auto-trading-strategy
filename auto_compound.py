"""
Auto Compound & Profit Reinvestment
=====================================
Automatically reinvest profits for compound growth.
"""

from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta
from loguru import logger
import json
import os


@dataclass
class CompoundState:
    initial_capital: float
    current_capital: float
    total_profit: float
    total_profit_pct: float
    reinvested: float
    withdrawn: float
    
    # Growth metrics
    days_active: int
    monthly_return_pct: float
    annual_projected_pct: float
    
    # Next milestone
    next_milestone: float
    next_milestone_pct: float


class AutoCompound:
    """
    Auto Compound System
    
    Features:
    1. Automatic profit reinvestment
    2. Milestone tracking (50%, 100%, 200%...)
    3. Suggested withdrawal schedule
    4. Growth projection
    
    Strategy:
    - Reinvest 80% of profits
    - Withdraw 20% (take some off the table)
    - Every 100% gain, withdraw principal
    """
    
    def __init__(self, initial_capital: float,
                 reinvest_pct: float = 0.80,
                 state_file: str = "compound_state.json"):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.reinvest_pct = reinvest_pct
        self.state_file = state_file
        
        self.start_date = datetime.now()
        self.milestones_hit = []
        self.withdrawn = 0
        self.reinvested = 0
        
        self._load_state()
    
    def update(self, new_capital: float) -> CompoundState:
        """Update capital and calculate compound metrics"""
        
        prev_capital = self.current_capital
        profit = new_capital - prev_capital
        
        if profit > 0:
            # Reinvest portion
            reinvest = profit * self.reinvest_pct
            withdraw = profit * (1 - self.reinvest_pct)
            
            self.reinvested += reinvest
            self.withdrawn += withdraw
            
            # Effective new capital (after suggested withdrawal)
            self.current_capital = prev_capital + reinvest
        else:
            self.current_capital = new_capital
        
        # Check milestones
        self._check_milestones()
        
        self._save_state()
        return self._get_state()
    
    def add_deposit(self, amount: float):
        """Add new deposit"""
        self.current_capital += amount
        self.initial_capital += amount
        logger.info(f"💰 Deposit: +${amount:,.2f}")
        self._save_state()
    
    def _check_milestones(self):
        """Check for milestone achievements"""
        total_gain = self.current_capital / self.initial_capital - 1
        
        milestones = [0.25, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
        
        for m in milestones:
            if total_gain >= m and m not in self.milestones_hit:
                self.milestones_hit.append(m)
                logger.info(f"🎉 MILESTONE: {m*100:.0f}% gain!")
                
                if m >= 1.0:
                    logger.info(f"💡 Consider withdrawing original ${self.initial_capital:,.2f}")
    
    def _get_state(self) -> CompoundState:
        """Calculate current state"""
        total_profit = self.current_capital - self.initial_capital + self.withdrawn
        total_profit_pct = total_profit / self.initial_capital * 100
        
        days = (datetime.now() - self.start_date).days + 1
        
        # Monthly return
        monthly_return = (self.current_capital / self.initial_capital) ** (30/days) - 1
        annual_projected = (1 + monthly_return) ** 12 - 1
        
        # Next milestone
        current_gain = self.current_capital / self.initial_capital
        milestones = [1.25, 1.50, 1.75, 2.0, 2.5, 3.0, 5.0, 10.0]
        next_m = next((m for m in milestones if m > current_gain), 10.0)
        
        return CompoundState(
            initial_capital=self.initial_capital,
            current_capital=self.current_capital,
            total_profit=total_profit,
            total_profit_pct=total_profit_pct,
            reinvested=self.reinvested,
            withdrawn=self.withdrawn,
            days_active=days,
            monthly_return_pct=monthly_return * 100,
            annual_projected_pct=annual_projected * 100,
            next_milestone=self.initial_capital * next_m,
            next_milestone_pct=next_m * 100
        )
    
    def _save_state(self):
        try:
            state = {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'start_date': self.start_date.isoformat(),
                'milestones_hit': self.milestones_hit,
                'withdrawn': self.withdrawn,
                'reinvested': self.reinvested
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except: pass
    
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.initial_capital = state.get('initial_capital', self.initial_capital)
                self.current_capital = state.get('current_capital', self.initial_capital)
                self.start_date = datetime.fromisoformat(state.get('start_date', datetime.now().isoformat()))
                self.milestones_hit = state.get('milestones_hit', [])
                self.withdrawn = state.get('withdrawn', 0)
                self.reinvested = state.get('reinvested', 0)
        except: pass


def get_compound(initial: float = 1500) -> AutoCompound:
    return AutoCompound(initial)

def update_compound_tier(buying_power: float):
    """Module helper function to update capital and tier progression"""
    logger.info(f"AutoCompound: updating compound tier with buying power ${buying_power:,.2f}")
    # Instantiate or load state
    ac = get_compound()
    state = ac.update(buying_power)
    logger.info(f"AutoCompound: current capital is ${state.current_capital:,.2f}, total profit is {state.total_profit_pct:+.2f}%")


if __name__ == "__main__":
    print("Testing AutoCompound...")
    ac = AutoCompound(1500)
    
    scenarios = [1600, 1800, 2100, 2000, 2500, 3000]
    
    for cap in scenarios:
        state = ac.update(cap)
        print(f"\nCapital: ${cap}")
        print(f"  Current: ${state.current_capital:,.0f}")
        print(f"  Profit: {state.total_profit_pct:+.1f}%")
        print(f"  Monthly: {state.monthly_return_pct:+.1f}%")
        print(f"  Annual Projected: {state.annual_projected_pct:+.1f}%")
