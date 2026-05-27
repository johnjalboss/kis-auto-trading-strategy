"""
Monte Carlo Trade Simulator
==============================
Simulate trade outcomes for risk assessment.

Features:
1. Trade outcome distribution
2. Max drawdown probability
3. Win streak analysis
4. Risk of ruin calculation
5. Position sizing optimization
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class MonteCarloResult:
    """Monte Carlo simulation result"""
    # Basic stats
    simulations: int
    trades_per_sim: int
    
    # Outcome distribution
    mean_return: float
    median_return: float
    std_return: float
    
    # Percentiles
    p5_return: float   # 5th percentile (worst case)
    p25_return: float
    p75_return: float
    p95_return: float  # 95th percentile (best case)
    
    # Risk metrics
    max_drawdown_avg: float
    max_drawdown_worst: float
    prob_loss: float
    risk_of_ruin: float  # P(drawdown > 50%)
    
    # Win streaks
    avg_win_streak: float
    avg_lose_streak: float
    max_win_streak: int
    max_lose_streak: int
    
    # Recommendations
    optimal_position_size: float
    kelly_fraction: float
    
    confidence_score: int
    details: List[str]


class MonteCarloSimulator:
    """
    Monte Carlo Trade Simulation
    
    Uses historical trade parameters to simulate
    thousands of possible outcomes.
    
    Key Inputs:
    - Win rate
    - Average win size
    - Average loss size
    - Number of trades
    
    Outputs:
    - Expected return distribution
    - Maximum drawdown probabilities
    - Risk of ruin
    - Optimal position sizing
    
    Use Cases:
    - Validate strategy before going live
    - Size positions appropriately
    - Set realistic expectations
    """
    
    def __init__(self, n_simulations: int = 10000):
        self.n_simulations = n_simulations
    
    def simulate(self, 
                 win_rate: float = 0.55,
                 avg_win_pct: float = 0.03,
                 avg_loss_pct: float = 0.02,
                 n_trades: int = 100,
                 position_size: float = 0.10) -> MonteCarloResult:
        """Run Monte Carlo simulation"""
        details = []
        
        # Store results
        final_returns = []
        max_drawdowns = []
        win_streaks = []
        lose_streaks = []
        
        for _ in range(self.n_simulations):
            # Simulate trades
            equity = 1.0
            peak = 1.0
            max_dd = 0
            current_win_streak = 0
            current_lose_streak = 0
            sim_max_win = 0
            sim_max_lose = 0
            
            for _ in range(n_trades):
                # Random outcome
                is_win = np.random.random() < win_rate
                
                if is_win:
                    # Win - add some randomness to win size
                    return_pct = avg_win_pct * np.random.uniform(0.5, 1.5)
                    equity *= (1 + return_pct * position_size)
                    current_win_streak += 1
                    sim_max_win = max(sim_max_win, current_win_streak)
                    current_lose_streak = 0
                else:
                    # Loss
                    return_pct = avg_loss_pct * np.random.uniform(0.5, 1.5)
                    equity *= (1 - return_pct * position_size)
                    current_lose_streak += 1
                    sim_max_lose = max(sim_max_lose, current_lose_streak)
                    current_win_streak = 0
                
                # Update peak and drawdown
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)
            
            final_returns.append(equity - 1)
            max_drawdowns.append(max_dd)
            win_streaks.append(sim_max_win)
            lose_streaks.append(sim_max_lose)
        
        # Calculate statistics
        returns_arr = np.array(final_returns)
        dd_arr = np.array(max_drawdowns)
        
        mean_ret = float(np.mean(returns_arr))
        median_ret = float(np.median(returns_arr))
        std_ret = float(np.std(returns_arr))
        
        p5 = float(np.percentile(returns_arr, 5))
        p25 = float(np.percentile(returns_arr, 25))
        p75 = float(np.percentile(returns_arr, 75))
        p95 = float(np.percentile(returns_arr, 95))
        
        avg_dd = float(np.mean(dd_arr))
        worst_dd = float(np.max(dd_arr))
        prob_loss = float(np.mean(returns_arr < 0))
        risk_of_ruin = float(np.mean(dd_arr > 0.5))
        
        avg_win_streak = float(np.mean(win_streaks))
        avg_lose_streak = float(np.mean(lose_streaks))
        max_win = int(np.max(win_streaks))
        max_lose = int(np.max(lose_streaks))
        
        # Kelly criterion
        b = avg_win_pct / avg_loss_pct
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        kelly = max(0, min(0.25, kelly))  # Cap at 25%
        
        # Optimal position size (half-Kelly)
        optimal_size = kelly / 2
        
        # Confidence score
        if mean_ret > 0.20 and risk_of_ruin < 0.05:
            confidence = 90
            details.append("EXCELLENT_RISK_ADJUSTED")
        elif mean_ret > 0.10 and risk_of_ruin < 0.10:
            confidence = 70
            details.append("GOOD_EXPECTANCY")
        elif mean_ret > 0 and risk_of_ruin < 0.20:
            confidence = 50
            details.append("MARGINAL_EDGE")
        else:
            confidence = 30
            details.append("HIGH_RISK")
        
        details.append(f"EXPECTED:{mean_ret:.1%}")
        details.append(f"WORST_CASE:{p5:.1%}")
        
        return MonteCarloResult(
            simulations=self.n_simulations,
            trades_per_sim=n_trades,
            mean_return=mean_ret,
            median_return=median_ret,
            std_return=std_ret,
            p5_return=p5,
            p25_return=p25,
            p75_return=p75,
            p95_return=p95,
            max_drawdown_avg=avg_dd,
            max_drawdown_worst=worst_dd,
            prob_loss=prob_loss,
            risk_of_ruin=risk_of_ruin,
            avg_win_streak=avg_win_streak,
            avg_lose_streak=avg_lose_streak,
            max_win_streak=max_win,
            max_lose_streak=max_lose,
            optimal_position_size=optimal_size,
            kelly_fraction=kelly,
            confidence_score=confidence,
            details=details
        )


# Global
_simulator = None

def get_monte_carlo() -> MonteCarloSimulator:
    global _simulator
    if _simulator is None:
        _simulator = MonteCarloSimulator()
    return _simulator


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing MonteCarloSimulator...")
    
    simulator = MonteCarloSimulator(n_simulations=5000)
    
    # Test different scenarios
    scenarios = [
        {"name": "Conservative", "win_rate": 0.55, "avg_win": 0.02, "avg_loss": 0.015},
        {"name": "Aggressive", "win_rate": 0.45, "avg_win": 0.05, "avg_loss": 0.02},
        {"name": "Scalping", "win_rate": 0.65, "avg_win": 0.01, "avg_loss": 0.008},
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario['name']}")
        print('='*60)
        
        result = simulator.simulate(
            win_rate=scenario['win_rate'],
            avg_win_pct=scenario['avg_win'],
            avg_loss_pct=scenario['avg_loss'],
            n_trades=100,
            position_size=0.10
        )
        
        print(f"Simulations: {result.simulations:,}")
        print(f"Trades/Sim: {result.trades_per_sim}")
        print()
        print(f"Expected Return: {result.mean_return:.1%}")
        print(f"Median Return: {result.median_return:.1%}")
        print(f"Std Dev: {result.std_return:.1%}")
        print()
        print(f"5th Percentile (Worst): {result.p5_return:.1%}")
        print(f"95th Percentile (Best): {result.p95_return:.1%}")
        print()
        print(f"Avg Max DD: {result.max_drawdown_avg:.1%}")
        print(f"Worst Max DD: {result.max_drawdown_worst:.1%}")
        print(f"Prob of Loss: {result.prob_loss:.1%}")
        print(f"Risk of Ruin: {result.risk_of_ruin:.1%}")
        print()
        print(f"Optimal Position: {result.optimal_position_size:.1%}")
        print(f"Kelly Fraction: {result.kelly_fraction:.1%}")
        print(f"Confidence: {result.confidence_score}%")
        print(f"Details: {result.details}")
