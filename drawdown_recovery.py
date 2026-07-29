"""
Drawdown Recovery Mode
========================
Special strategy when in drawdown.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum
from loguru import logger
import config


class RecoveryPhase(Enum):
    NORMAL = "NORMAL"           # <5% DD
    CAUTION = "CAUTION"         # 5-10% DD
    DEFENSIVE = "DEFENSIVE"     # 10-15% DD
    RECOVERY = "RECOVERY"       # 15-20% DD
    CRITICAL = "CRITICAL"       # >20% DD


@dataclass
class RecoveryConfig:
    phase: RecoveryPhase
    
    # Position sizing
    position_mult: float
    max_positions: int
    
    # Entry criteria
    min_score_boost: int
    require_confluence: bool
    new_entries_allowed: bool
    
    # Exit criteria
    profit_target_mult: float
    stop_loss_mult: float
    
    # Risk
    daily_loss_limit_pct: float
    
    # Special rules
    special_rules: List[str]


class DrawdownRecovery:
    """
    Drawdown Recovery Manager
    
    Phases:
    1. NORMAL (<5%): Full strategy
    2. CAUTION (5-10%): Reduce size
    3. DEFENSIVE (10-15%): Quality only
    4. RECOVERY (15-20%): Aggressive recovery
    5. CRITICAL (>20%): Stop and reassess
    
    Recovery Strategy:
    - Smaller positions, higher quality
    - Wider stops (don't get stopped out again)
    - Pyramid into winners
    """
    
    CONFIGS = {
        RecoveryPhase.NORMAL: RecoveryConfig(
            phase=RecoveryPhase.NORMAL,
            position_mult=1.0,
            max_positions=5,
            min_score_boost=0,
            require_confluence=False,
            new_entries_allowed=True,
            profit_target_mult=2.0,
            stop_loss_mult=1.0,
            daily_loss_limit_pct=3.0,
            special_rules=["Normal trading"]
        ),
        RecoveryPhase.CAUTION: RecoveryConfig(
            phase=RecoveryPhase.CAUTION,
            position_mult=0.75,
            max_positions=4,
            min_score_boost=5,
            require_confluence=False,
            new_entries_allowed=True,
            profit_target_mult=2.0,
            stop_loss_mult=1.2,
            daily_loss_limit_pct=2.5,
            special_rules=["Reduce position sizes", "Widen stops slightly"]
        ),
        RecoveryPhase.DEFENSIVE: RecoveryConfig(
            phase=RecoveryPhase.DEFENSIVE,
            position_mult=0.5,
            max_positions=3,
            min_score_boost=10,
            require_confluence=True,
            new_entries_allowed=True,
            profit_target_mult=2.5,
            stop_loss_mult=1.5,
            daily_loss_limit_pct=2.0,
            special_rules=[
                "Quality trades only",
                "Require multi-TF confluence",
                "No FOMO entries"
            ]
        ),
        RecoveryPhase.RECOVERY: RecoveryConfig(
            phase=RecoveryPhase.RECOVERY,
            position_mult=0.6,
            max_positions=3,
            min_score_boost=15,
            require_confluence=True,
            new_entries_allowed=True,
            profit_target_mult=3.0,
            stop_loss_mult=1.5,
            daily_loss_limit_pct=2.0,
            special_rules=[
                "Only A+ setups",
                "Let winners run",
                "Pyramid into winners",
                "Cut losers fast"
            ]
        ),
        RecoveryPhase.CRITICAL: RecoveryConfig(
            phase=RecoveryPhase.CRITICAL,
            position_mult=0.25,
            max_positions=1,
            min_score_boost=20,
            require_confluence=True,
            new_entries_allowed=False,
            profit_target_mult=3.0,
            stop_loss_mult=2.0,
            daily_loss_limit_pct=1.0,
            special_rules=[
                "STOP: Reassess strategy",
                "Close all but best position",
                "Paper trade until confidence returns",
                "Review what went wrong"
            ]
        )
    }
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.peak_capital = initial_capital
        self.current_capital = initial_capital
    
    def update(self, new_capital: float) -> RecoveryConfig:
        """Update capital and get recovery config"""
        
        self.current_capital = new_capital
        self.peak_capital = max(self.peak_capital, new_capital)
        
        dd = self.get_drawdown()
        phase = self.get_phase(dd)
        
        logger.info(f"Drawdown: {dd:.1f}% → Phase: {phase.value}")
        
        return self.CONFIGS[phase]
    
    def get_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        if self.peak_capital <= 0:
            return 0
        return (1 - self.current_capital / self.peak_capital) * 100
    
    def get_phase(self, dd: float = None) -> RecoveryPhase:
        """Get recovery phase"""
        if dd is None:
            dd = self.get_drawdown()
        
        if dd < 5:
            return RecoveryPhase.NORMAL
        elif dd < 10:
            return RecoveryPhase.CAUTION
        elif dd < 15:
            return RecoveryPhase.DEFENSIVE
        elif dd < 20:
            return RecoveryPhase.RECOVERY
        else:
            return RecoveryPhase.CRITICAL
    
    def get_adjusted_score_threshold(self, base: int) -> int:
        """Adjust score threshold based on phase"""
        config = self.CONFIGS[self.get_phase()]
        return base + config.min_score_boost
    
    def get_position_size(self, normal_size: float) -> float:
        """Adjust position size based on phase"""
        config = self.CONFIGS[self.get_phase()]
        return normal_size * config.position_mult


def get_drawdown_recovery(capital: float = 100000) -> DrawdownRecovery:
    return DrawdownRecovery(capital)


if __name__ == "__main__":
    print("Testing DrawdownRecovery...")
    
    dr = DrawdownRecovery(1500000)
    
    scenarios = [1500000, 1450000, 1350000, 1275000, 1150000]
    
    for cap in scenarios:
        config = dr.update(cap)
        dd = dr.get_drawdown()
        
        print(f"\n{'='*50}")
        print(f"Capital: ₩{cap:,} (DD: {dd:.1f}%)")
        print(f"Phase: {config.phase.value}")
        print(f"Position Mult: {config.position_mult}x")
        print(f"Max Positions: {config.max_positions}")
        print(f"Score Boost: +{config.min_score_boost}")
        print(f"Rules: {config.special_rules}")
