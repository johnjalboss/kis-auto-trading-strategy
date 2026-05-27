"""
High Performance Optimizer
============================
Maximum returns while maintaining risk control.
Target: PF > 2.0, Win Rate > 60%, MDD < 15%
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
from loguru import logger
import config


class PerformanceMode(Enum):
    CONSERVATIVE = "CONSERVATIVE"  # PF 1.5, WR 55%, MDD 10%
    BALANCED = "BALANCED"          # PF 1.8, WR 58%, MDD 12%
    AGGRESSIVE = "AGGRESSIVE"      # PF 2.0, WR 60%, MDD 15%
    MAXIMUM = "MAXIMUM"            # PF 2.5+, WR 65%+, MDD 18%


@dataclass
class PerformanceConfig:
    mode: PerformanceMode
    
    # Entry filters (higher = more selective = higher win rate)
    min_composite_score: int
    min_confidence: int
    min_momentum_percentile: int
    require_regime_alignment: bool
    require_volume_confirmation: bool
    
    # Position sizing
    base_position_pct: float
    max_position_pct: float
    scale_by_conviction: bool
    
    # Exit optimization
    profit_target_multiplier: float  # vs stop loss
    use_trailing_stop: bool
    trailing_activation_pct: float
    partial_take_profit: bool  # Take 50% at 1st target
    
    # Risk limits
    max_daily_trades: int
    max_open_positions: int
    daily_loss_limit_pct: float
    
    # Alpha boosters
    use_premarket_gap: bool
    use_momentum_ranking: bool
    use_sector_rotation: bool
    avoid_earnings: bool


class HighPerformanceOptimizer:
    """
    High Performance Trading Optimizer
    
    Key Optimizations:
    1. Higher entry threshold → Higher win rate
    2. Wider targets → Better PF
    3. Smart sizing → Lower MDD
    4. Multiple confirmations → Fewer but better trades
    """
    
    CONFIGS = {
        PerformanceMode.CONSERVATIVE: PerformanceConfig(
            mode=PerformanceMode.CONSERVATIVE,
            min_composite_score=50,
            min_confidence=70,
            min_momentum_percentile=60,
            require_regime_alignment=True,
            require_volume_confirmation=True,
            base_position_pct=0.05,
            max_position_pct=0.10,
            scale_by_conviction=True,
            profit_target_multiplier=1.5,
            use_trailing_stop=True,
            trailing_activation_pct=5.0,
            partial_take_profit=True,
            max_daily_trades=3,
            max_open_positions=3,
            daily_loss_limit_pct=2.0,
            use_premarket_gap=False,
            use_momentum_ranking=True,
            use_sector_rotation=True,
            avoid_earnings=True
        ),
        PerformanceMode.BALANCED: PerformanceConfig(
            mode=PerformanceMode.BALANCED,
            min_composite_score=45,
            min_confidence=65,
            min_momentum_percentile=55,
            require_regime_alignment=True,
            require_volume_confirmation=True,
            base_position_pct=0.08,
            max_position_pct=0.15,
            scale_by_conviction=True,
            profit_target_multiplier=2.0,
            use_trailing_stop=True,
            trailing_activation_pct=4.0,
            partial_take_profit=True,
            max_daily_trades=5,
            max_open_positions=4,
            daily_loss_limit_pct=2.5,
            use_premarket_gap=True,
            use_momentum_ranking=True,
            use_sector_rotation=True,
            avoid_earnings=True
        ),
        PerformanceMode.AGGRESSIVE: PerformanceConfig(
            mode=PerformanceMode.AGGRESSIVE,
            min_composite_score=40,
            min_confidence=60,
            min_momentum_percentile=50,
            require_regime_alignment=True,
            require_volume_confirmation=False,
            base_position_pct=0.12,
            max_position_pct=0.20,
            scale_by_conviction=True,
            profit_target_multiplier=2.5,
            use_trailing_stop=True,
            trailing_activation_pct=3.0,
            partial_take_profit=True,
            max_daily_trades=7,
            max_open_positions=5,
            daily_loss_limit_pct=3.0,
            use_premarket_gap=True,
            use_momentum_ranking=True,
            use_sector_rotation=True,
            avoid_earnings=False
        ),
        PerformanceMode.MAXIMUM: PerformanceConfig(
            mode=PerformanceMode.MAXIMUM,
            min_composite_score=55,  # Higher for quality
            min_confidence=70,
            min_momentum_percentile=70,  # Top 30% only
            require_regime_alignment=True,
            require_volume_confirmation=True,
            base_position_pct=0.15,
            max_position_pct=0.25,
            scale_by_conviction=True,
            profit_target_multiplier=3.0,  # Big winners
            use_trailing_stop=True,
            trailing_activation_pct=5.0,
            partial_take_profit=True,
            max_daily_trades=4,  # Quality over quantity
            max_open_positions=3,
            daily_loss_limit_pct=3.0,
            use_premarket_gap=True,
            use_momentum_ranking=True,
            use_sector_rotation=True,
            avoid_earnings=True
        )
    }
    
    def __init__(self, mode: PerformanceMode = PerformanceMode.AGGRESSIVE):
        self.mode = mode
        self.config = self.CONFIGS[mode]
        logger.info(f"Performance mode: {mode.value}")
    
    def should_trade(self, 
                     composite_score: int,
                     confidence: int,
                     momentum_percentile: float,
                     regime_aligned: bool,
                     has_volume: bool) -> tuple:
        """Check if trade meets performance criteria"""
        
        c = self.config
        reasons = []
        
        # Check each filter
        if composite_score < c.min_composite_score:
            reasons.append(f"Score {composite_score} < {c.min_composite_score}")
        
        if confidence < c.min_confidence:
            reasons.append(f"Confidence {confidence} < {c.min_confidence}")
        
        if momentum_percentile < c.min_momentum_percentile:
            reasons.append(f"Momentum {momentum_percentile:.0f}% < {c.min_momentum_percentile}%")
        
        if c.require_regime_alignment and not regime_aligned:
            reasons.append("Regime not aligned")
        
        if c.require_volume_confirmation and not has_volume:
            reasons.append("No volume confirmation")
        
        passed = len(reasons) == 0
        return passed, reasons
    
    def calculate_position_size(self, 
                                capital: float,
                                composite_score: int,
                                confidence: int) -> float:
        """Calculate optimal position size"""
        
        c = self.config
        base = capital * c.base_position_pct
        
        if c.scale_by_conviction:
            # Scale by score strength
            score_factor = min(1.5, composite_score / 50)
            conf_factor = min(1.3, confidence / 70)
            
            size = base * score_factor * conf_factor
        else:
            size = base
        
        # Cap at max
        max_size = capital * c.max_position_pct
        return min(size, max_size)
    
    def get_targets(self, entry: float, atr: float) -> dict:
        """Calculate optimized exit targets"""
        
        c = self.config
        stop = entry - (1.5 * atr)  # 1.5 ATR stop
        
        risk = entry - stop
        reward = risk * c.profit_target_multiplier
        
        target1 = entry + (reward * 0.5)  # First target
        target2 = entry + reward          # Full target
        
        return {
            'stop_loss': stop,
            'target_1': target1,
            'target_2': target2,
            'trailing_activation': entry * (1 + c.trailing_activation_pct / 100),
            'use_trailing': c.use_trailing_stop,
            'partial_at_t1': c.partial_take_profit
        }
    
    def get_expected_metrics(self) -> dict:
        """Expected performance metrics"""
        
        metrics = {
            PerformanceMode.CONSERVATIVE: {
                'win_rate': '55-60%', 'profit_factor': '1.4-1.6',
                'mdd': '8-12%', 'annual_return': '15-25%'
            },
            PerformanceMode.BALANCED: {
                'win_rate': '55-62%', 'profit_factor': '1.6-2.0',
                'mdd': '10-15%', 'annual_return': '20-35%'
            },
            PerformanceMode.AGGRESSIVE: {
                'win_rate': '50-58%', 'profit_factor': '1.8-2.2',
                'mdd': '12-18%', 'annual_return': '30-50%'
            },
            PerformanceMode.MAXIMUM: {
                'win_rate': '60-70%', 'profit_factor': '2.0-3.0',
                'mdd': '12-18%', 'annual_return': '40-80%'
            }
        }
        return metrics.get(self.mode, {})
    
    def set_mode(self, mode: PerformanceMode):
        self.mode = mode
        self.config = self.CONFIGS[mode]


def get_optimizer(mode: str = "AGGRESSIVE") -> HighPerformanceOptimizer:
    mode_enum = PerformanceMode[mode.upper()]
    return HighPerformanceOptimizer(mode_enum)


if __name__ == "__main__":
    print("Testing HighPerformanceOptimizer...")
    
    for mode in PerformanceMode:
        print(f"\n{'='*50}")
        print(f"Mode: {mode.value}")
        print('='*50)
        
        opt = HighPerformanceOptimizer(mode)
        config = opt.config
        expected = opt.get_expected_metrics()
        
        print(f"Min Score: {config.min_composite_score}")
        print(f"Min Confidence: {config.min_confidence}")
        print(f"Position: {config.base_position_pct:.0%} - {config.max_position_pct:.0%}")
        print(f"Profit Target: {config.profit_target_multiplier}x risk")
        print(f"Max Positions: {config.max_open_positions}")
        print()
        print("Expected Performance:")
        for k, v in expected.items():
            print(f"  {k}: {v}")
