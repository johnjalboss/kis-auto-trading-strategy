"""
Execution Quality Tracker
===========================
Track and optimize trade execution quality.
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from loguru import logger
import json
import os


@dataclass
class ExecutionRecord:
    symbol: str
    timestamp: datetime
    intended_price: float
    actual_price: float
    slippage_pct: float
    order_type: str
    market_condition: str
    
    @property
    def quality_grade(self) -> str:
        if self.slippage_pct < 0.05:
            return "A"  # Excellent
        elif self.slippage_pct < 0.15:
            return "B"  # Good
        elif self.slippage_pct < 0.30:
            return "C"  # Acceptable
        else:
            return "D"  # Poor


@dataclass
class ExecutionStats:
    total_trades: int
    avg_slippage_pct: float
    best_execution: float
    worst_execution: float
    
    # By time
    best_time_window: str
    worst_time_window: str
    
    # Grade distribution
    grade_a_pct: float
    grade_b_pct: float
    grade_c_pct: float
    grade_d_pct: float
    
    recommendations: List[str]


class ExecutionTracker:
    """
    Execution Quality Tracker
    
    Tracks:
    1. Slippage per trade
    2. Best execution times
    3. Order type performance
    
    Learns optimal:
    - Time of day to trade
    - Order types (limit vs market)
    - Position sizing impact
    """
    
    def __init__(self, data_file: str = "execution_data.json"):
        self.data_file = data_file
        self.records: List[Dict] = []
        self._load()
    
    def record(self, 
               symbol: str,
               intended: float,
               actual: float,
               order_type: str = "MARKET",
               condition: str = "NORMAL"):
        """Record an execution"""
        
        slippage = abs(actual - intended) / intended * 100 if intended > 0 else 0
        
        record = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'intended': intended,
            'actual': actual,
            'slippage_pct': slippage,
            'order_type': order_type,
            'condition': condition,
            'hour': datetime.now().hour
        }
        
        self.records.append(record)
        self._save()
        
        # Log quality
        grade = self._get_grade(slippage)
        logger.info(f"Execution {symbol}: {grade} (slip: {slippage:.2f}%)")
    
    def get_stats(self) -> ExecutionStats:
        """Get execution statistics"""
        if not self.records:
            return self._empty_stats()
        
        slippages = [r['slippage_pct'] for r in self.records]
        
        # By hour
        hourly = {}
        for r in self.records:
            h = r['hour']
            if h not in hourly:
                hourly[h] = []
            hourly[h].append(r['slippage_pct'])
        
        avg_hourly = {h: sum(s)/len(s) for h, s in hourly.items()}
        
        best_hour = min(avg_hourly, key=avg_hourly.get) if avg_hourly else 10
        worst_hour = max(avg_hourly, key=avg_hourly.get) if avg_hourly else 15
        
        # Grades
        grades = [self._get_grade(s) for s in slippages]
        n = len(grades)
        
        # Recommendations
        recs = []
        avg_slip = sum(slippages) / len(slippages)
        
        if avg_slip > 0.20:
            recs.append("Consider using limit orders")
        if worst_hour in [9, 15]:
            recs.append(f"Avoid trading at hour {worst_hour}")
        if best_hour:
            recs.append(f"Best execution at hour {best_hour}")
        
        return ExecutionStats(
            total_trades=n,
            avg_slippage_pct=avg_slip,
            best_execution=min(slippages),
            worst_execution=max(slippages),
            best_time_window=f"{best_hour}:00",
            worst_time_window=f"{worst_hour}:00",
            grade_a_pct=grades.count('A')/n*100,
            grade_b_pct=grades.count('B')/n*100,
            grade_c_pct=grades.count('C')/n*100,
            grade_d_pct=grades.count('D')/n*100,
            recommendations=recs
        )
    
    def get_optimal_time(self) -> int:
        """Get best hour for execution"""
        if not self.records:
            return 10
        
        hourly = {}
        for r in self.records:
            h = r['hour']
            if h not in hourly:
                hourly[h] = []
            hourly[h].append(r['slippage_pct'])
        
        avg_hourly = {h: sum(s)/len(s) for h, s in hourly.items()}
        return min(avg_hourly, key=avg_hourly.get)
    
    def _get_grade(self, slippage: float) -> str:
        if slippage < 0.05:
            return "A"
        elif slippage < 0.15:
            return "B"
        elif slippage < 0.30:
            return "C"
        return "D"
    
    def _empty_stats(self) -> ExecutionStats:
        return ExecutionStats(0, 0, 0, 0, "10:00", "15:00", 0, 0, 0, 0, [])
    
    def _save(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.records, f)
        except: pass
    
    def _load(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.records = json.load(f)
        except: pass


def get_execution_tracker() -> ExecutionTracker:
    return ExecutionTracker()


if __name__ == "__main__":
    print("Testing ExecutionTracker...")
    et = ExecutionTracker("test_exec.json")
    
    # Simulate executions
    executions = [
        ("AAPL", 150.00, 150.05),
        ("NVDA", 500.00, 500.50),
        ("TSLA", 250.00, 250.80),
        ("MSFT", 380.00, 380.10),
    ]
    
    for sym, intended, actual in executions:
        et.record(sym, intended, actual)
    
    stats = et.get_stats()
    print(f"\nExecution Stats:")
    print(f"  Trades: {stats.total_trades}")
    print(f"  Avg Slippage: {stats.avg_slippage_pct:.2f}%")
    print(f"  Grade A: {stats.grade_a_pct:.0f}%")
    print(f"  Best Time: {stats.best_time_window}")
    print(f"  Recommendations: {stats.recommendations}")
