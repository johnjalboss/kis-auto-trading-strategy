"""
Anti-Fragility Module
=======================
Profit from chaos and extreme events.
"""

from dataclasses import dataclass
from typing import List
import yfinance as yf
from loguru import logger


@dataclass
class AntiFragilePosition:
    instrument: str
    position_type: str  # "HEDGE", "TAIL_RISK", "VOLATILITY"
    allocation_pct: float
    trigger_condition: str
    expected_payoff: str


class AntiFrагility:
    """
    Anti-Fragility Strategy
    
    Get STRONGER from volatility/chaos:
    
    1. Tail Risk Hedges: Small puts for crash protection
    2. VIX Calls: Profit from fear spikes  
    3. Cash Buffer: Deploy when others panic
    4. Inverse ETFs: Short exposure in crisis
    
    Allocation: 5-10% of portfolio to anti-fragile positions
    """
    
    HEDGE_INSTRUMENTS = {
        'VIX_CALL': 'UVXY',    # VIX long
        'MARKET_PUT': 'SPXU',   # 3x inverse S&P
        'GOLD': 'GLD',          # Flight to safety
        'BONDS': 'TLT',         # Treasury bonds
        'CASH': 'CASH'          # Dry powder
    }
    
    def __init__(self, portfolio_value: float, hedge_pct: float = 0.05):
        self.portfolio_value = portfolio_value
        self.hedge_pct = hedge_pct
        self.hedge_budget = portfolio_value * hedge_pct
    
    def get_hedge_positions(self, vix_level: float, market_trend: str) -> List[AntiFragilePosition]:
        """Recommend hedge positions based on conditions"""
        positions = []
        
        # Always keep some cash for opportunities
        positions.append(AntiFragilePosition(
            instrument="CASH",
            position_type="OPPORTUNITY",
            allocation_pct=2.0,
            trigger_condition="Market crash > 10%",
            expected_payoff="Deploy at panic lows"
        ))
        
        if vix_level < 15:
            # Low fear = cheap hedges
            positions.append(AntiFragilePosition(
                instrument="UVXY",
                position_type="TAIL_RISK",
                allocation_pct=1.0,
                trigger_condition="VIX < 15",
                expected_payoff="VIX spike to 30+ = 3-5x"
            ))
        
        if market_trend == "BULL" and vix_level < 20:
            # Buy protection when cheap
            positions.append(AntiFragilePosition(
                instrument="GLD",
                position_type="HEDGE",
                allocation_pct=2.0,
                trigger_condition="Bull market, low VIX",
                expected_payoff="Crisis protection"
            ))
        
        if market_trend == "BEAR":
            # More defensive
            positions.append(AntiFragilePosition(
                instrument="TLT",
                position_type="HEDGE",
                allocation_pct=3.0,
                trigger_condition="Bear market",
                expected_payoff="Flight to safety"
            ))
        
        return positions
    
    def get_crisis_actions(self, drawdown_pct: float) -> List[str]:
        """Actions during crisis"""
        actions = []
        
        if drawdown_pct >= 5:
            actions.append("REDUCE: Cut losers, keep winners")
        
        if drawdown_pct >= 10:
            actions.append("HEDGE: Add inverse positions")
            actions.append("CASH: Raise to 30%")
        
        if drawdown_pct >= 20:
            actions.append("OPPORTUNITY: Start selective buying")
            actions.append("QUALITY: Focus on best names only")
        
        if drawdown_pct >= 30:
            actions.append("AGGRESSIVE: Deploy cash into oversold quality")
        
        return actions
    
    def get_opportunity_score(self, vix: float, drawdown: float) -> int:
        """Score buying opportunity (0-100)"""
        score = 0
        
        # Higher VIX = more fear = better opportunity
        if vix > 30:
            score += 30
        elif vix > 25:
            score += 20
        elif vix > 20:
            score += 10
        
        # Bigger drawdown = better prices
        if drawdown > 20:
            score += 40
        elif drawdown > 15:
            score += 30
        elif drawdown > 10:
            score += 20
        elif drawdown > 5:
            score += 10
        
        return min(100, score)
    
    def get_antifragility_score(self) -> float:
        """
        Compute antifragility score (-100 to 100).
        Lower score (< -50) indicates fragile state requiring size reduction.
        """
        try:
            import yfinance as yf
            vix_df = yf.Ticker("^VIX").history(period="5d")
            vix = vix_df["Close"].iloc[-1] if not vix_df.empty else 15.0
            
            spy_df = yf.Ticker("SPY").history(period="10d")
            if not spy_df.empty:
                spy_max = spy_df["High"].max()
                spy_curr = spy_df["Close"].iloc[-1]
                drawdown = (spy_max - spy_curr) / spy_max * 100
            else:
                drawdown = 0.0
                
            score = 0.0
            if vix > 35:
                score -= 60.0
            elif vix > 25:
                score -= 30.0
                
            if drawdown > 8.0:
                score -= 55.0
            elif drawdown > 5.0:
                score -= 25.0
                
            return score
        except Exception as e:
            logger.warning("Error in get_antifragility_score: {}", e)
            return 0.0


def get_antifragility(portfolio: float = 100000) -> AntiFrагility:
    return AntiFrагility(portfolio)


if __name__ == "__main__":
    print("Testing AntiFrагility...")
    af = AntiFrагility(1500000)  # ₩150만 = $1500 approx
    
    scenarios = [
        (12, "BULL", 0),
        (18, "SIDEWAYS", 5),
        (25, "BEAR", 10),
        (35, "BEAR", 25),
    ]
    
    for vix, trend, dd in scenarios:
        print(f"\n{'='*50}")
        print(f"VIX: {vix}, Trend: {trend}, DD: {dd}%")
        print('='*50)
        
        hedges = af.get_hedge_positions(vix, trend)
        for h in hedges:
            print(f"  {h.instrument}: {h.allocation_pct}% - {h.expected_payoff}")
        
        if dd > 0:
            actions = af.get_crisis_actions(dd)
            print(f"  Actions: {actions}")
        
        opp = af.get_opportunity_score(vix, dd)
        print(f"  Opportunity Score: {opp}/100")
