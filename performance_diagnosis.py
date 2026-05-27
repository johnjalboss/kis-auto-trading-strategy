"""
Performance Diagnosis System
===============================
Analyze why returns are low and recommend fixes.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
import os


@dataclass
class DiagnosisReport:
    period: str
    total_return_pct: float
    benchmark_return_pct: float
    alpha: float  # Return vs benchmark
    
    # Problems identified
    problems: List[str]
    severity: str  # "CRITICAL", "WARNING", "INFO"
    
    # Root causes
    root_causes: List[str]
    
    # Specific recommendations
    recommendations: List[str]
    
    # Parameter adjustments
    suggested_changes: Dict[str, str]


@dataclass
class TradeAnalysis:
    total_trades: int
    winners: int
    losers: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Problems
    biggest_losers: List[Dict]
    problem_patterns: List[str]


class PerformanceDiagnosis:
    """
    Performance Diagnosis Engine
    
    Analyzes:
    1. Win rate issues
    2. Risk/reward imbalance
    3. Market timing problems
    4. Strategy mismatch
    5. Cost drag
    6. Position sizing errors
    """
    
    def __init__(self, data_file: str = "trade_history.json"):
        self.data_file = data_file
        self.trades: List[Dict] = []
        self._load()
    
    def record_trade(self, trade: Dict):
        """Record a completed trade"""
        self.trades.append({
            **trade,
            'timestamp': datetime.now().isoformat()
        })
        self._save()
    
    def diagnose(self, days: int = 30) -> DiagnosisReport:
        """Run full diagnosis"""
        
        # Filter recent trades
        cutoff = datetime.now() - timedelta(days=days)
        recent = [t for t in self.trades 
                  if datetime.fromisoformat(t['timestamp']) > cutoff]
        
        if not recent:
            return self._no_data_report()
        
        # Calculate metrics
        returns = [t.get('pnl_pct', 0) for t in recent]
        total_return = sum(returns)
        
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        
        win_rate = len(wins) / len(returns) * 100 if returns else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 1
        pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else 0
        
        # Benchmark (assume SPY ~0.5%/week)
        benchmark = days / 7 * 0.5
        alpha = total_return - benchmark
        
        problems = []
        root_causes = []
        recommendations = []
        changes = {}
        
        # === DIAGNOSIS ===
        
        # 1. Win Rate Analysis
        if win_rate < 40:
            problems.append(f"LOW_WIN_RATE: {win_rate:.0f}%")
            root_causes.append("Entry signals too weak or timing off")
            recommendations.append("Increase min_composite_score threshold")
            changes['min_composite_score'] = "50 → 60"
        
        # 2. Profit Factor Analysis
        if pf < 1.0:
            problems.append(f"NEGATIVE_EXPECTANCY: PF={pf:.2f}")
            root_causes.append("Losses bigger than wins")
            recommendations.append("Widen profit targets, tighten stops")
            changes['profit_target_multiplier'] = "2.0 → 3.0"
        elif pf < 1.5:
            problems.append(f"LOW_PROFIT_FACTOR: PF={pf:.2f}")
            recommendations.append("Hold winners longer")
        
        # 3. Average Win vs Loss
        if avg_loss > avg_win * 1.5:
            problems.append(f"RISK_REWARD_IMBALANCE: Win={avg_win:.1f}% Loss={avg_loss:.1f}%")
            root_causes.append("Cutting winners too early, holding losers too long")
            recommendations.append("Use trailing stops to let winners run")
            changes['use_trailing_stop'] = "True with 5% activation"
        
        # 4. Trade Frequency
        trades_per_day = len(recent) / days
        if trades_per_day > 3:
            problems.append(f"OVERTRADING: {trades_per_day:.1f}/day")
            root_causes.append("Too many low-quality trades")
            recommendations.append("Reduce max_trades_per_day")
            changes['max_trades_per_day'] = f"{int(trades_per_day)} → 3"
        
        # 5. Losing Streak Analysis
        max_streak = self._get_losing_streak(returns)
        if max_streak >= 5:
            problems.append(f"LONG_LOSING_STREAK: {max_streak} in a row")
            root_causes.append("Strategy may not match current market")
            recommendations.append("Check market regime and pause if bear")
        
        # 6. Cost Impact
        if recent:
            avg_trade_size = sum([t.get('value', 0) for t in recent]) / len(recent)
            cost_per_trade = avg_trade_size * 0.005  # 0.5% round trip
            total_costs = cost_per_trade * len(recent)
            cost_drag = total_costs / avg_trade_size * 100 if avg_trade_size > 0 else 0
            
            if cost_drag > 2:
                problems.append(f"HIGH_COST_DRAG: {cost_drag:.1f}%")
                recommendations.append("Increase min hold time to reduce turnover")
        
        # Severity
        if len(problems) >= 4 or total_return < -10:
            severity = "CRITICAL"
        elif len(problems) >= 2 or total_return < -5:
            severity = "WARNING"
        else:
            severity = "INFO"
        
        # Default recommendations if no specific issues
        if not recommendations:
            recommendations.append("Performance within acceptable range")
            recommendations.append("Continue monitoring")
        
        return DiagnosisReport(
            period=f"Last {days} days",
            total_return_pct=total_return,
            benchmark_return_pct=benchmark,
            alpha=alpha,
            problems=problems,
            severity=severity,
            root_causes=root_causes,
            recommendations=recommendations,
            suggested_changes=changes
        )
    
    def get_problem_trades(self) -> List[Dict]:
        """Get worst trades for analysis"""
        sorted_trades = sorted(self.trades, key=lambda x: x.get('pnl_pct', 0))
        return sorted_trades[:5]  # Worst 5
    
    def analyze_by_strategy(self) -> Dict[str, Dict]:
        """Analyze performance by strategy"""
        strategies = {}
        
        for t in self.trades:
            strat = t.get('strategy', 'UNKNOWN')
            if strat not in strategies:
                strategies[strat] = {'trades': [], 'total': 0}
            strategies[strat]['trades'].append(t.get('pnl_pct', 0))
        
        for strat, data in strategies.items():
            trades = data['trades']
            data['count'] = len(trades)
            data['total'] = sum(trades)
            data['avg'] = sum(trades) / len(trades) if trades else 0
            data['win_rate'] = len([t for t in trades if t > 0]) / len(trades) * 100 if trades else 0
        
        return strategies
    
    def analyze_by_regime(self) -> Dict[str, Dict]:
        """Analyze performance by market regime"""
        regimes = {}
        
        for t in self.trades:
            regime = t.get('regime', 'UNKNOWN')
            if regime not in regimes:
                regimes[regime] = {'trades': [], 'total': 0}
            regimes[regime]['trades'].append(t.get('pnl_pct', 0))
        
        for regime, data in regimes.items():
            trades = data['trades']
            data['count'] = len(trades)
            data['total'] = sum(trades)
            data['avg'] = sum(trades) / len(trades) if trades else 0
        
        return regimes
    
    def get_improvement_priority(self) -> List[str]:
        """Get prioritized list of improvements"""
        report = self.diagnose()
        
        priority = []
        for problem in report.problems:
            if 'WIN_RATE' in problem:
                priority.append("1. Improve entry signals (raise thresholds)")
            if 'PROFIT_FACTOR' in problem:
                priority.append("2. Fix risk/reward (wider targets)")
            if 'OVERTRADING' in problem:
                priority.append("3. Reduce trade frequency")
            if 'STREAK' in problem:
                priority.append("4. Add regime filter")
        
        return priority[:3]  # Top 3
    
    def _get_losing_streak(self, returns: list) -> int:
        max_streak = 0
        current = 0
        for r in returns:
            if r <= 0:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak
    
    def _no_data_report(self) -> DiagnosisReport:
        return DiagnosisReport(
            period="N/A",
            total_return_pct=0,
            benchmark_return_pct=0,
            alpha=0,
            problems=["NO_DATA"],
            severity="INFO",
            root_causes=["No trades recorded yet"],
            recommendations=["Start trading to collect data"],
            suggested_changes={}
        )
    
    def _save(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
        except: pass
    
    def _load(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.trades = json.load(f)
        except: pass


def get_diagnosis() -> PerformanceDiagnosis:
    return PerformanceDiagnosis()


if __name__ == "__main__":
    print("Testing PerformanceDiagnosis...")
    pd = PerformanceDiagnosis("test_diag.json")
    
    # Simulate poor performance
    test_trades = [
        {'pnl_pct': 2.0, 'strategy': 'MOMENTUM', 'regime': 'BULL', 'value': 50000},
        {'pnl_pct': -3.5, 'strategy': 'MOMENTUM', 'regime': 'BULL', 'value': 50000},
        {'pnl_pct': -2.0, 'strategy': 'REVERSAL', 'regime': 'SIDEWAYS', 'value': 50000},
        {'pnl_pct': 1.5, 'strategy': 'MOMENTUM', 'regime': 'BULL', 'value': 50000},
        {'pnl_pct': -4.0, 'strategy': 'REVERSAL', 'regime': 'BEAR', 'value': 50000},
        {'pnl_pct': -1.5, 'strategy': 'MOMENTUM', 'regime': 'BEAR', 'value': 50000},
        {'pnl_pct': 3.0, 'strategy': 'MOMENTUM', 'regime': 'BULL', 'value': 50000},
        {'pnl_pct': -2.5, 'strategy': 'REVERSAL', 'regime': 'SIDEWAYS', 'value': 50000},
    ]
    
    for t in test_trades:
        pd.record_trade(t)
    
    report = pd.diagnose(30)
    
    print(f"\n{'='*60}")
    print(f"PERFORMANCE DIAGNOSIS ({report.severity})")
    print('='*60)
    print(f"Return: {report.total_return_pct:+.1f}% vs Benchmark {report.benchmark_return_pct:+.1f}%")
    print(f"Alpha: {report.alpha:+.1f}%")
    
    print(f"\n📛 Problems:")
    for p in report.problems:
        print(f"  • {p}")
    
    print(f"\n🔍 Root Causes:")
    for r in report.root_causes:
        print(f"  • {r}")
    
    print(f"\n💡 Recommendations:")
    for r in report.recommendations:
        print(f"  • {r}")
    
    if report.suggested_changes:
        print(f"\n🔧 Parameter Changes:")
        for k, v in report.suggested_changes.items():
            print(f"  • {k}: {v}")
    
    print(f"\n📊 By Strategy:")
    strats = pd.analyze_by_strategy()
    for s, d in strats.items():
        print(f"  {s}: {d['count']} trades, {d['total']:+.1f}%, WR={d['win_rate']:.0f}%")
    
    print(f"\n📊 By Regime:")
    regimes = pd.analyze_by_regime()
    for r, d in regimes.items():
        print(f"  {r}: {d['count']} trades, {d['total']:+.1f}%")
