"""
Portfolio Stress Test
========================
Test portfolio under extreme scenarios.
"""

from dataclasses import dataclass
from typing import List, Dict
from loguru import logger


@dataclass
class StressScenario:
    name: str
    description: str
    market_drop_pct: float
    correlation_spike: float
    volatility_mult: float
    
    portfolio_impact_pct: float
    positions_liquidated: int
    recovery_days_est: int


@dataclass
class StressTestResult:
    current_capital: float
    scenarios: List[StressScenario]
    
    worst_case_loss_pct: float
    survival_rate: float  # % of scenarios we survive
    
    recommendations: List[str]


class PortfolioStressTest:
    """
    Portfolio Stress Testing
    
    Scenarios:
    1. 2008 Financial Crisis (-50%)
    2. 2020 COVID Crash (-35%)
    3. Flash Crash (-10% in 1 day)
    4. Rate Shock (-20%)
    5. Black Swan (-40%)
    
    Tests if portfolio can survive extreme events.
    """
    
    SCENARIOS = [
        {
            'name': '2008 Financial Crisis',
            'desc': 'Lehman collapse, credit freeze',
            'drop': 50,
            'corr': 0.95,
            'vol_mult': 4.0,
            'recovery': 250
        },
        {
            'name': '2020 COVID Crash',
            'desc': 'Pandemic panic, fastest drop ever',
            'drop': 35,
            'corr': 0.90,
            'vol_mult': 5.0,
            'recovery': 60
        },
        {
            'name': 'Flash Crash',
            'desc': 'Algorithmic cascade, circuit breakers',
            'drop': 10,
            'corr': 0.99,
            'vol_mult': 10.0,
            'recovery': 1
        },
        {
            'name': 'Rate Shock',
            'desc': 'Aggressive Fed tightening',
            'drop': 20,
            'corr': 0.80,
            'vol_mult': 2.5,
            'recovery': 120
        },
        {
            'name': 'Black Swan',
            'desc': 'Unexpected catastrophic event',
            'drop': 40,
            'corr': 0.95,
            'vol_mult': 6.0,
            'recovery': 180
        },
        {
            'name': '10% Correction',
            'desc': 'Normal market correction',
            'drop': 10,
            'corr': 0.75,
            'vol_mult': 1.5,
            'recovery': 30
        }
    ]
    
    def __init__(self, capital: float, positions: Dict[str, float] = None):
        self.capital = capital
        self.positions = positions or {}
    
    def run_test(self, max_risk_pct: float = 100) -> StressTestResult:
        """Run stress test"""
        
        results = []
        
        for s in self.SCENARIOS:
            # Calculate portfolio impact
            # Simplified: portfolio drops same as market * beta
            beta = 1.0  # Assume market beta
            exposure = sum(self.positions.values()) if self.positions else self.capital * 0.8
            
            # Impact calculation
            impact_pct = s['drop'] * beta * (exposure / self.capital)
            
            # How many positions get stopped out
            stop_threshold = 5  # Assume 5% stop
            positions_stopped = int(impact_pct / stop_threshold)
            
            results.append(StressScenario(
                name=s['name'],
                description=s['desc'],
                market_drop_pct=s['drop'],
                correlation_spike=s['corr'],
                volatility_mult=s['vol_mult'],
                portfolio_impact_pct=min(impact_pct, 100),
                positions_liquidated=positions_stopped,
                recovery_days_est=s['recovery']
            ))
        
        # Analysis
        worst = max(r.portfolio_impact_pct for r in results)
        survive_count = sum(1 for r in results if r.portfolio_impact_pct < max_risk_pct)
        survival_rate = survive_count / len(results) * 100
        
        # Recommendations
        recs = []
        
        if worst > 50:
            recs.append("CRITICAL: Max drawdown >50% - reduce leverage")
        if worst > 30:
            recs.append("Add hedges (GLD, TLT) to reduce tail risk")
        if survival_rate < 100:
            recs.append("Consider reducing position sizes")
        
        if worst < 20:
            recs.append("Portfolio is well-protected against most scenarios")
        
        recs.append(f"Keep {worst * 0.3:.0f}% cash for crisis buying opportunities")
        
        return StressTestResult(
            current_capital=self.capital,
            scenarios=results,
            worst_case_loss_pct=worst,
            survival_rate=survival_rate,
            recommendations=recs
        )


def get_stress_test(capital: float = 100000) -> PortfolioStressTest:
    return PortfolioStressTest(capital)


if __name__ == "__main__":
    print("Testing PortfolioStressTest...")
    
    st = PortfolioStressTest(1500000, {'AAPL': 300000, 'NVDA': 300000, 'TSLA': 200000})
    
    result = st.run_test()
    
    print(f"\n{'='*60}")
    print("PORTFOLIO STRESS TEST")
    print('='*60)
    print(f"Capital: ₩{result.current_capital:,}")
    
    print(f"\nScenarios:")
    for s in result.scenarios:
        print(f"  {s.name}:")
        print(f"    Market: -{s.market_drop_pct}% → Portfolio: -{s.portfolio_impact_pct:.1f}%")
        print(f"    Recovery: ~{s.recovery_days_est} days")
    
    print(f"\nWorst Case Loss: -{result.worst_case_loss_pct:.1f}%")
    print(f"Survival Rate: {result.survival_rate:.0f}%")
    
    print(f"\nRecommendations:")
    for r in result.recommendations:
        print(f"  • {r}")


def run_stress_test(portfolio):
    return PortfolioStressTest(capital=100000).run(portfolio)
