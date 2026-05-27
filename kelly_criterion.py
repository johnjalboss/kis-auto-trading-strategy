"""
Kelly Criterion Position Sizing
=================================
Mathematically optimal position sizing.
"""

from dataclasses import dataclass
from loguru import logger


@dataclass
class KellyResult:
    kelly_fraction: float      # Raw Kelly (often too aggressive)
    half_kelly: float          # Safer, half Kelly
    quarter_kelly: float       # Conservative
    recommended_pct: float     # Our recommendation
    max_position_value: float
    rationale: str


class KellyCriterion:
    """
    Kelly Criterion Calculator
    
    Formula: f* = (p * b - q) / b
    where:
    - p = win probability
    - q = loss probability (1 - p)
    - b = win/loss ratio (avg win / avg loss)
    
    We use HALF KELLY for safety (less volatile)
    """
    
    def __init__(self, 
                 default_win_rate: float = 0.55,
                 default_win_loss_ratio: float = 1.5,
                 max_kelly_fraction: float = 0.25):
        self.default_win_rate = default_win_rate
        self.default_win_loss_ratio = default_win_loss_ratio
        self.max_kelly = max_kelly_fraction
    
    def calculate(self,
                  capital: float,
                  win_rate: float = None,
                  avg_win: float = None,
                  avg_loss: float = None,
                  confidence: int = 50) -> KellyResult:
        """Calculate optimal position size"""
        
        p = win_rate or self.default_win_rate
        q = 1 - p
        
        if avg_win and avg_loss and avg_loss > 0:
            b = avg_win / avg_loss
        else:
            b = self.default_win_loss_ratio
        
        # Kelly formula
        if b > 0:
            kelly = (p * b - q) / b
        else:
            kelly = 0
        
        # Sanity check
        kelly = max(0, min(kelly, self.max_kelly))
        
        half = kelly / 2
        quarter = kelly / 4
        
        # Adjust by confidence
        confidence_mult = 0.5 + (confidence / 100) * 0.5  # 0.5 to 1.0
        
        # Recommended: Half Kelly adjusted by confidence
        recommended = half * confidence_mult
        recommended = min(recommended, 0.15)  # Cap at 15%
        
        max_value = capital * recommended
        
        # Rationale
        if kelly >= 0.20:
            rationale = f"Strong edge (Kelly={kelly:.1%}), using half for safety"
        elif kelly >= 0.10:
            rationale = f"Good edge (Kelly={kelly:.1%}), moderate sizing"
        elif kelly > 0:
            rationale = f"Small edge (Kelly={kelly:.1%}), conservative sizing"
        else:
            rationale = "No edge detected, skip trade"
        
        return KellyResult(
            kelly_fraction=kelly,
            half_kelly=half,
            quarter_kelly=quarter,
            recommended_pct=recommended,
            max_position_value=max_value,
            rationale=rationale
        )
    
    def from_historical(self, 
                        capital: float,
                        trades: list) -> KellyResult:
        """Calculate from historical trades"""
        if not trades:
            return self.calculate(capital)
        
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t < 0]
        
        if not wins or not losses:
            return self.calculate(capital)
        
        win_rate = len(wins) / len(trades)
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        
        return self.calculate(capital, win_rate, avg_win, avg_loss)


def get_kelly() -> KellyCriterion:
    return KellyCriterion()


def get_kelly_fraction(symbol: str = None) -> float:
    """Get recommended Kelly fraction for a symbol based on real trading history.
    
    Called by orchestrator.py Phase 5 to size positions.
    Returns a fraction (0.0 ~ 0.15) representing recommended position size.
    """
    kc = get_kelly()
    
    # Attempt to fetch real win rate from database
    try:
        from database import get_database
        db = get_database()
        # Get all completed trades (SELL side trades with valid pnl_pct)
        with db._get_conn() as conn:
            trades = conn.execute("SELECT pnl_pct FROM trades WHERE side='SELL'").fetchall()
        if trades and len(trades) >= 10:
            profits = [t['pnl_pct'] for t in trades]
            wins = [p for p in profits if p > 0]
            losses = [p for p in profits if p < 0]
            
            if wins and losses:
                win_rate = len(wins) / len(profits)
                avg_win = sum(wins) / len(wins)
                avg_loss = abs(sum(losses) / len(losses))
                
                result = kc.calculate(capital=10000, win_rate=win_rate, avg_win=avg_win, avg_loss=avg_loss)
                return result.recommended_pct
    except Exception as e:
        logger.debug(f"Could not load historical Kelly stats: {e}")
        
    # Fallback to defaults
    result = kc.calculate(capital=10000)
    return result.recommended_pct


if __name__ == "__main__":
    print("Testing KellyCriterion...")
    kc = KellyCriterion()
    
    scenarios = [
        (0.60, 2.0, "High edge"),
        (0.55, 1.5, "Moderate edge"),
        (0.50, 1.0, "No edge"),
        (0.45, 1.5, "Slight negative"),
    ]
    
    for wr, wl, name in scenarios:
        result = kc.calculate(10000, wr, 100, 100/wl)
        print(f"\n{name} (WR={wr:.0%}, W/L={wl})")
        print(f"  Kelly: {result.kelly_fraction:.1%}")
        print(f"  Half Kelly: {result.half_kelly:.1%}")
        print(f"  Recommended: {result.recommended_pct:.1%}")
        print(f"  Max: ${result.max_position_value:,.0f}")
        print(f"  {result.rationale}")
