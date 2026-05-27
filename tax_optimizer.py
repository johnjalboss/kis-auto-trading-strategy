"""
Tax Optimizer (Tax-Loss Harvesting)
=====================================
Optimize taxes through strategic selling.
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class TaxLot:
    symbol: str
    shares: int
    cost_basis: float
    purchase_date: datetime
    current_value: float
    unrealized_pnl: float
    is_short_term: bool
    days_held: int


@dataclass
class HarvestOpportunity:
    symbol: str
    loss_amount: float
    tax_savings_est: float
    action: str
    wash_sale_end: datetime
    replacement_symbol: str


class TaxOptimizer:
    """
    Tax-Loss Harvesting
    
    Strategy:
    1. Harvest losses to offset gains
    2. Avoid wash sales (30-day rule)
    3. Consider short-term vs long-term rates
    
    Korean Tax Context:
    - 250만원 공제 후 22% (지방세 포함)
    - 2023년부터 금융투자소득세
    """
    
    # Korean tax rates (2023+)
    TAX_EXEMPTION = 2_500_000  # ₩250만
    TAX_RATE = 0.22  # 22% including local tax
    
    WASH_SALE_DAYS = 30
    LONG_TERM_DAYS = 365
    
    def __init__(self):
        self.realized_gains: float = 0
        self.realized_losses: float = 0
        self.harvested: Dict[str, datetime] = {}  # symbol -> harvest date
    
    def add_realized(self, pnl: float):
        """Record realized gain/loss"""
        if pnl > 0:
            self.realized_gains += pnl
        else:
            self.realized_losses += abs(pnl)
    
    def find_harvest_opportunities(self, positions: List[TaxLot]) -> List[HarvestOpportunity]:
        """Find tax-loss harvesting opportunities"""
        opportunities = []
        
        for pos in positions:
            if pos.unrealized_pnl >= 0:
                continue
            
            # Check wash sale
            if pos.symbol in self.harvested:
                wash_end = self.harvested[pos.symbol] + timedelta(days=self.WASH_SALE_DAYS)
                if datetime.now() < wash_end:
                    continue
            
            loss = abs(pos.unrealized_pnl)
            tax_savings = loss * self.TAX_RATE
            
            # Find replacement (similar but different)
            replacement = self._find_replacement(pos.symbol)
            
            opportunities.append(HarvestOpportunity(
                symbol=pos.symbol,
                loss_amount=loss,
                tax_savings_est=tax_savings,
                action=f"Sell {pos.shares} shares",
                wash_sale_end=datetime.now() + timedelta(days=self.WASH_SALE_DAYS),
                replacement_symbol=replacement
            ))
        
        # Sort by loss amount
        opportunities.sort(key=lambda x: x.loss_amount, reverse=True)
        return opportunities
    
    def should_harvest(self, position: TaxLot, force: bool = False) -> tuple:
        """
        Check if should harvest this loss
        
        NOTE: Tax optimization is OPTIONAL. Don't force trades just for taxes.
        Only suggest when it makes trading sense AND saves taxes.
        """
        
        if position.unrealized_pnl >= 0:
            return False, "Position is profitable"
        
        loss = abs(position.unrealized_pnl)
        
        # Don't harvest small losses (not worth the effort)
        if loss < 50000:  # ₩5만 미만
            return False, "Loss too small to harvest"
        
        # Check if we have gains to offset
        net_gains = self.realized_gains - self.realized_losses
        
        if net_gains > self.TAX_EXEMPTION:
            # We have taxable gains
            benefit = min(loss, net_gains - self.TAX_EXEMPTION) * self.TAX_RATE
            # Only recommend if benefit is significant
            if benefit > 10000 or force:  # ₩1만 이상
                return True, f"Optional: Harvest saves ₩{benefit:,.0f} in taxes"
            return False, "Tax benefit minimal"
        
        # Don't force harvest just for carry-forward
        if force:
            return True, "Optional: Carry forward loss"
        return False, "No immediate tax benefit"
    
    def record_harvest(self, symbol: str, loss: float):
        """Record a tax-loss harvest"""
        self.harvested[symbol] = datetime.now()
        self.realized_losses += loss
        logger.info(f"Tax-loss harvest: {symbol} -₩{loss:,.0f}")
    
    def get_tax_summary(self) -> dict:
        """Get tax summary"""
        net = self.realized_gains - self.realized_losses
        taxable = max(0, net - self.TAX_EXEMPTION)
        tax_owed = taxable * self.TAX_RATE
        
        return {
            'realized_gains': self.realized_gains,
            'realized_losses': self.realized_losses,
            'net_gains': net,
            'tax_exemption': self.TAX_EXEMPTION,
            'taxable_amount': taxable,
            'estimated_tax': tax_owed
        }
    
    def _find_replacement(self, symbol: str) -> str:
        """Find replacement to maintain exposure"""
        replacements = {
            'AAPL': 'XLK',
            'MSFT': 'XLK',
            'GOOGL': 'XLC',
            'AMZN': 'XLY',
            'NVDA': 'SMH',
            'TSLA': 'XLY',
            'META': 'XLC'
        }
        return replacements.get(symbol, 'SPY')


def get_tax_optimizer() -> TaxOptimizer:
    return TaxOptimizer()


def optimize_tax_lot(symbol: str, action: str, qty: int) -> tuple:
    """Orchestrator compatibility: check if tax-loss harvesting applies.
    
    Called by orchestrator.py Phase 5 to potentially adjust trade for tax benefits.
    Returns (qty, action) — may be unchanged if no tax optimization needed.
    """
    if action != "SELL":
        return qty, action
    # Tax optimizer doesn't modify qty/action directly for now, just pass-through.
    # Future: could reduce qty to defer gains or suggest harvesting.
    return qty, action


if __name__ == "__main__":
    print("Testing TaxOptimizer...")
    to = TaxOptimizer()
    
    # Simulate gains
    to.add_realized(500000)  # ₩50만 이익
    
    # Create test positions
    positions = [
        TaxLot("AAPL", 10, 180, datetime.now() - timedelta(days=60), 1700, -100000, True, 60),
        TaxLot("NVDA", 5, 500, datetime.now() - timedelta(days=120), 2200, -50000, True, 120),
        TaxLot("TSLA", 8, 250, datetime.now() - timedelta(days=30), 2200, 20000, True, 30),
    ]
    
    opps = to.find_harvest_opportunities(positions)
    
    print(f"\nRealized Gains: ₩{to.realized_gains:,}")
    print(f"\nHarvest Opportunities:")
    for o in opps:
        print(f"  {o.symbol}: Loss ₩{o.loss_amount:,} → Tax Savings ₩{o.tax_savings_est:,.0f}")
        print(f"    Replace with: {o.replacement_symbol}")
    
    summary = to.get_tax_summary()
    print(f"\nTax Summary: {summary}")
