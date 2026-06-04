"""
Performance Attribution
=========================
Track which strategies and signals work best.
"""

from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime
from loguru import logger
import json
import os


@dataclass
class StrategyStats:
    name: str
    trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float
    profit_factor: float
    best_trade: float
    worst_trade: float


class PerformanceAttribution:
    """
    Track performance by:
    - Strategy type
    - Market regime
    - Signal type
    - Time of day
    - Sector
    """
    
    def __init__(self, state_file: str = "performance_attribution.json"):
        self.state_file = state_file
        self.trades: List[Dict] = []
        self._load()
    
    def record_trade(self, 
                     symbol: str,
                     strategy: str,
                     regime: str,
                     signal_type: str,
                     sector: str,
                     pnl: float,
                     pnl_pct: float):
        """Record a trade for attribution"""
        
        trade = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'strategy': strategy,
            'regime': regime,
            'signal_type': signal_type,
            'sector': sector,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }
        self.trades.append(trade)
        self._save()
    
    def get_strategy_stats(self) -> List[StrategyStats]:
        """Get stats by strategy"""
        strategies = {}
        
        for t in self.trades:
            strat = t['strategy']
            if strat not in strategies:
                strategies[strat] = []
            strategies[strat].append(t['pnl'])
        
        results = []
        for name, pnls in strategies.items():
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            results.append(StrategyStats(
                name=name,
                trades=len(pnls),
                wins=len(wins),
                losses=len(losses),
                win_rate=len(wins)/len(pnls)*100 if pnls else 0,
                total_pnl=sum(pnls),
                avg_pnl=sum(pnls)/len(pnls) if pnls else 0,
                profit_factor=sum(wins)/abs(sum(losses)) if losses and sum(losses) else 0,
                best_trade=max(pnls) if pnls else 0,
                worst_trade=min(pnls) if pnls else 0
            ))
        
        return sorted(results, key=lambda x: x.total_pnl, reverse=True)
    
    def get_best_performers(self) -> Dict:
        """Find best performing combinations"""
        return {
            'best_strategy': self._get_best('strategy'),
            'best_regime': self._get_best('regime'),
            'best_sector': self._get_best('sector'),
            'worst_strategy': self._get_worst('strategy'),
            'worst_regime': self._get_worst('regime')
        }
    
    def _get_best(self, key: str) -> str:
        groups = {}
        for t in self.trades:
            k = t.get(key, 'unknown')
            if k not in groups:
                groups[k] = []
            groups[k].append(t['pnl'])
        
        if not groups:
            return "N/A"
        
        avg_pnl = {k: sum(v)/len(v) for k, v in groups.items()}
        return max(avg_pnl, key=avg_pnl.get)
    
    def _get_worst(self, key: str) -> str:
        groups = {}
        for t in self.trades:
            k = t.get(key, 'unknown')
            if k not in groups:
                groups[k] = []
            groups[k].append(t['pnl'])
        
        if not groups:
            return "N/A"
        
        avg_pnl = {k: sum(v)/len(v) for k, v in groups.items()}
        return min(avg_pnl, key=avg_pnl.get)
    
    def _save(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({'trades': self.trades}, f)
        except: pass
    
    def _load(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                self.trades = data.get('trades', [])
        except: pass
        
    def analyze(self) -> dict:
        """Perform attribution analysis and return a summary dict"""
        stats = self.get_strategy_stats()
        best = self.get_best_performers()
        
        summary = "No trades recorded for attribution yet."
        if stats:
            best_strat = best.get('best_strategy', 'N/A')
            best_pnl = stats[0].total_pnl if stats else 0
            summary = f"Best Strategy: {best_strat} (${best_pnl:+.2f} P&L). Total strategies analyzed: {len(stats)}."
            
        return {
            'summary': summary,
            'stats': [dict(
                name=s.name, trades=s.trades, wins=s.wins, losses=s.losses,
                win_rate=s.win_rate, total_pnl=s.total_pnl, avg_pnl=s.avg_pnl,
                profit_factor=s.profit_factor
            ) for s in stats],
            'best_performers': best
        }


def get_attribution() -> PerformanceAttribution:
    return PerformanceAttribution()


if __name__ == "__main__":
    print("Testing PerformanceAttribution...")
    pa = PerformanceAttribution("test_attribution.json")
    
    # Simulate trades
    trades = [
        ("AAPL", "MOMENTUM", "BULL", "ALPHA", "XLK", 150),
        ("NVDA", "MOMENTUM", "BULL", "ALPHA", "XLK", 300),
        ("TSLA", "REVERSAL", "VOLATILE", "OVERSOLD", "XLY", -100),
        ("MSFT", "MOMENTUM", "BULL", "ALPHA", "XLK", 200),
        ("AMD", "REVERSAL", "SIDEWAYS", "OVERSOLD", "XLK", 50),
    ]
    
    for sym, strat, regime, sig, sector, pnl in trades:
        pa.record_trade(sym, strat, regime, sig, sector, pnl, pnl/1000*100)
    
    print("\nStrategy Stats:")
    for s in pa.get_strategy_stats():
        print(f"  {s.name}: WR={s.win_rate:.0f}%, PF={s.profit_factor:.1f}, PnL=${s.total_pnl}")
    
    print(f"\nBest Performers: {pa.get_best_performers()}")
