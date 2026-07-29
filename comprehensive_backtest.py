"""
Comprehensive Strategy Backtester
=====================================
Backtest across multiple periods and market regimes.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Tuple
from loguru import logger
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestResult:
    period: str
    regime: str
    start_date: str
    end_date: str
    
    # Returns
    total_return_pct: float
    annualized_return_pct: float
    benchmark_return_pct: float
    alpha_pct: float
    
    # Risk metrics
    max_drawdown_pct: float
    volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    
    # Trade stats
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win_pct: float
    avg_loss_pct: float
    
    # Summary
    monthly_returns: List[float]
    equity_curve: List[float]


class ComprehensiveBacktester:
    """
    Multi-Period, Multi-Regime Backtester
    
    Periods:
    - 1 Month
    - 3 Months
    - 6 Months
    - 1 Year
    - 3 Years
    
    Regimes:
    - Bull Market (2023-24 rally)
    - Bear Market (2022 crash)
    - Sideways (2015, 2018)
    - Mixed
    """
    
    # Historical regime periods (approximate)
    REGIME_PERIODS = {
        'BULL': ('2023-01-01', '2024-01-01'),      # Strong bull 2023
        'BEAR': ('2022-01-01', '2022-10-15'),      # 2022 bear market
        'SIDEWAYS': ('2015-01-01', '2015-12-31'),  # 2015 choppy
        'MIXED': ('2021-01-01', '2021-12-31'),     # 2021 volatile
        'COVID_CRASH': ('2020-02-01', '2020-04-30'),  # COVID crash & recovery
        'COVID_RECOVERY': ('2020-04-01', '2021-01-01'),  # Strong recovery
    }
    
    def __init__(self, initial_capital: float = 1500000):  # 150만원
        self.initial_capital = initial_capital
        self.results: List[BacktestResult] = []
    
    def run_all_backtests(self) -> List[BacktestResult]:
        """Run backtests for all periods and regimes"""
        
        print("="*70)
        print("COMPREHENSIVE STRATEGY BACKTEST")
        print("="*70)
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print()
        
        # 1. Period-based backtests
        periods = [
            ('1mo', 30),
            ('3mo', 90),
            ('6mo', 180),
            ('1yr', 365),
            ('3yr', 1095)
        ]
        
        print("[Period-Based Backtests]")
        print("-"*70)
        
        for period_name, days in periods:
            result = self._run_period_backtest(period_name, days)
            if result:
                self.results.append(result)
                self._print_result(result)
        
        # 2. Regime-based backtests
        print("\n[Market Regime Backtests]")
        print("-"*70)
        
        for regime_name, (start, end) in self.REGIME_PERIODS.items():
            result = self._run_regime_backtest(regime_name, start, end)
            if result:
                self.results.append(result)
                self._print_result(result)
        
        return self.results
    
    def _run_period_backtest(self, period_name: str, days: int) -> BacktestResult:
        """Run backtest for a specific period"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self._simulate_strategy(
            period=period_name,
            regime="RECENT",
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d')
        )
    
    def _run_regime_backtest(self, regime: str, start: str, end: str) -> BacktestResult:
        """Run backtest for a specific market regime"""
        
        return self._simulate_strategy(
            period=f"{regime}_PERIOD",
            regime=regime,
            start=start,
            end=end
        )
    
    def _simulate_strategy(self, period: str, regime: str, 
                           start: str, end: str) -> BacktestResult:
        """Simulate trading strategy"""
        
        try:
            # Get market data
            spy = yf.download('SPY', start=start, end=end, progress=False)
            qqq = yf.download('QQQ', start=start, end=end, progress=False)
            
            if spy.empty:
                return None
            
            if hasattr(spy.columns, 'get_level_values'):
                spy.columns = spy.columns.get_level_values(0)
            if hasattr(qqq.columns, 'get_level_values'):
                qqq.columns = qqq.columns.get_level_values(0)
            
            # Simulate strategy
            capital = self.initial_capital
            equity_curve = [capital]
            trades = []
            monthly_returns = []
            
            position = None
            entry_price = 0
            
            # Use SPY as proxy, apply our strategy signals
            prices = spy['Close'].values
            highs = spy['High'].values
            lows = spy['Low'].values
            volumes = spy['Volume'].values
            
            # Calculate indicators
            sma20 = pd.Series(prices).rolling(20).mean().values
            sma50 = pd.Series(prices).rolling(50).mean().values
            
            # RSI
            delta = pd.Series(prices).diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = (100 - (100 / (1 + rs))).values
            
            peak = capital
            max_dd = 0
            
            for i in range(60, len(prices)):  # Start after enough data
                current_price = prices[i]
                
                # OPTIMIZED AGGRESSIVE Strategy
                trend_up = prices[i] > sma20[i] if not np.isnan(sma20[i]) else False
                strong_trend = prices[i] > sma50[i] if not np.isnan(sma50[i]) else False
                trend_down = prices[i] < sma20[i] if not np.isnan(sma20[i]) else False
                rsi_val = rsi[i] if not np.isnan(rsi[i]) else 50
                
                # Trend strength
                trend_strength = (prices[i] - sma50[i]) / sma50[i] * 100 if not np.isnan(sma50[i]) else 0
                
                # Volume
                avg_vol = np.mean(volumes[i-20:i])
                vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1
                
                # ENTRY: Strong trend following
                momentum_5d = (prices[i] - prices[i-5]) / prices[i-5] if prices[i-5] > 0 else 0
                momentum_20d = (prices[i] - prices[i-20]) / prices[i-20] if prices[i-20] > 0 else 0
                
                # Buy on strong uptrend with moderate RSI
                strong_buy = strong_trend and trend_up and 40 < rsi_val < 70 and momentum_5d > 0
                # Buy breakout with volume
                breakout_buy = prices[i] > np.max(highs[i-10:i]) and vol_ratio > 1.2
                # Buy dip in uptrend
                dip_buy = strong_trend and rsi_val < 40 and momentum_20d > 0
                
                entry_signal = strong_buy or breakout_buy or dip_buy
                
                # EXIT: Trailing logic
                if position is not None:
                    pnl_pct = (current_price - entry_price) / entry_price
                    # Dynamic stop based on profit
                    if pnl_pct > 0.05:  # In profit, tighten stop
                        stop_pct = -0.02
                    else:
                        stop_pct = -0.04
                    
                    exit_signal = pnl_pct < stop_pct or rsi_val > 75 or (trend_down and pnl_pct > 0)
                else:
                    exit_signal = False
                
                if position is None and entry_signal:
                    # Adaptive position size based on trend strength
                    size_mult = min(0.8, 0.4 + abs(trend_strength) / 10)  # 40-80%
                    position = capital * size_mult / current_price
                    entry_price = current_price
                    trades.append({
                        'type': 'ENTRY',
                        'price': current_price,
                        'date': i
                    })
                
                elif position is not None:
                    pnl_pct = (current_price - entry_price) / entry_price
                    
                    # Take profit at 8% or exit signal
                    if pnl_pct > 0.08 or exit_signal:
                        profit = position * (current_price - entry_price)
                        capital += profit
                        trades.append({
                            'type': 'EXIT',
                            'price': current_price,
                            'pnl': profit,
                            'pnl_pct': pnl_pct * 100,
                            'date': i
                        })
                        position = None
                
                # Track equity
                if position is not None:
                    mark_to_market = capital + position * (current_price - entry_price)
                else:
                    mark_to_market = capital
                
                equity_curve.append(mark_to_market)
                
                # Track drawdown
                peak = max(peak, mark_to_market)
                dd = (peak - mark_to_market) / peak * 100
                max_dd = max(max_dd, dd)
            
            # Close any remaining position
            if position is not None:
                profit = position * (prices[-1] - entry_price)
                capital += profit
                trades.append({
                    'type': 'EXIT',
                    'price': prices[-1],
                    'pnl': profit,
                    'pnl_pct': ((prices[-1] - entry_price) / entry_price) * 100
                })
            
            # Calculate metrics
            total_return = (capital - self.initial_capital) / self.initial_capital * 100
            
            # Benchmark return
            benchmark_return = (prices[-1] / prices[60] - 1) * 100
            
            # Annualized return
            days_held = len(prices) - 60
            if days_held > 0:
                annual_return = total_return * (365 / days_held)
            else:
                annual_return = 0
            
            # Trade stats
            exits = [t for t in trades if t['type'] == 'EXIT']
            if exits:
                wins = [t for t in exits if t.get('pnl', 0) > 0]
                losses = [t for t in exits if t.get('pnl', 0) <= 0]
                
                win_rate = len(wins) / len(exits) * 100 if exits else 0
                
                avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
                avg_loss = abs(np.mean([t['pnl_pct'] for t in losses])) if losses else 0
                
                gross_profit = sum(t.get('pnl', 0) for t in wins)
                gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
            else:
                win_rate = 0
                avg_win = 0
                avg_loss = 0
                profit_factor = 0
            
            # Volatility and Sharpe
            returns = pd.Series(equity_curve).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 0 else 0
            sharpe = (annual_return - 5) / volatility if volatility > 0 else 0
            
            # Sortino (downside volatility)
            downside = returns[returns < 0]
            downside_vol = downside.std() * np.sqrt(252) * 100 if len(downside) > 0 else 0
            sortino = (annual_return - 5) / downside_vol if downside_vol > 0 else 0
            
            return BacktestResult(
                period=period,
                regime=regime,
                start_date=start,
                end_date=end,
                total_return_pct=round(total_return, 2),
                annualized_return_pct=round(annual_return, 2),
                benchmark_return_pct=round(benchmark_return, 2),
                alpha_pct=round(total_return - benchmark_return, 2),
                max_drawdown_pct=round(max_dd, 2),
                volatility_pct=round(volatility, 2),
                sharpe_ratio=round(sharpe, 2),
                sortino_ratio=round(sortino, 2),
                total_trades=len(exits),
                win_rate_pct=round(win_rate, 1),
                profit_factor=round(profit_factor, 2),
                avg_win_pct=round(avg_win, 2),
                avg_loss_pct=round(avg_loss, 2),
                monthly_returns=[],
                equity_curve=equity_curve[-10:]  # Last 10 points only
            )
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return None
    
    def _print_result(self, r: BacktestResult):
        """Print a single result"""
        
        # Color indicators
        ret_color = "🟢" if r.total_return_pct > 0 else "🔴"
        alpha_color = "🟢" if r.alpha_pct > 0 else "🔴"
        
        print(f"\n{r.period} ({r.regime})")
        print(f"  Period: {r.start_date} → {r.end_date}")
        print(f"  {ret_color} Return: {r.total_return_pct:+.2f}% (Annual: {r.annualized_return_pct:+.2f}%)")
        print(f"  📊 Benchmark: {r.benchmark_return_pct:+.2f}% | {alpha_color} Alpha: {r.alpha_pct:+.2f}%")
        print(f"  📉 Max DD: {r.max_drawdown_pct:.2f}% | Volatility: {r.volatility_pct:.2f}%")
        print(f"  📈 Sharpe: {r.sharpe_ratio:.2f} | Sortino: {r.sortino_ratio:.2f}")
        print(f"  🎯 Trades: {r.total_trades} | Win Rate: {r.win_rate_pct:.1f}% | PF: {r.profit_factor:.2f}")
    
    def print_summary(self):
        """Print overall summary"""
        
        if not self.results:
            print("No results to summarize")
            return
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        # By period
        print("\n[By Period - Recent]")
        print("-"*70)
        period_results = [r for r in self.results if r.regime == "RECENT"]
        for r in period_results:
            print(f"  {r.period:6} | Return: {r.total_return_pct:+8.2f}% | "
                  f"Alpha: {r.alpha_pct:+6.2f}% | "
                  f"MDD: {r.max_drawdown_pct:5.2f}% | "
                  f"WR: {r.win_rate_pct:5.1f}%")
        
        # By regime
        print("\n[By Market Regime]")
        print("-"*70)
        regime_results = [r for r in self.results if r.regime != "RECENT"]
        for r in regime_results:
            print(f"  {r.regime:15} | Return: {r.total_return_pct:+8.2f}% | "
                  f"Alpha: {r.alpha_pct:+6.2f}% | "
                  f"MDD: {r.max_drawdown_pct:5.2f}% | "
                  f"WR: {r.win_rate_pct:5.1f}%")
        
        # Overall stats
        avg_return = np.mean([r.total_return_pct for r in self.results])
        avg_alpha = np.mean([r.alpha_pct for r in self.results])
        avg_winrate = np.mean([r.win_rate_pct for r in self.results])
        
        print("\n[Overall Stats]")
        print("-"*70)
        print(f"  Average Return: {avg_return:+.2f}%")
        print(f"  Average Alpha:  {avg_alpha:+.2f}%")
        print(f"  Average WinRate: {avg_winrate:.1f}%")
        
        # Best/Worst
        best = max(self.results, key=lambda r: r.total_return_pct)
        worst = min(self.results, key=lambda r: r.total_return_pct)
        
        print(f"\n  Best:  {best.period}/{best.regime} → {best.total_return_pct:+.2f}%")
        print(f"  Worst: {worst.period}/{worst.regime} → {worst.total_return_pct:+.2f}%")


def run_comprehensive_backtest():
    """Run all backtests"""
    bt = ComprehensiveBacktester(initial_capital=1500000)  # 150만원
    bt.run_all_backtests()
    bt.print_summary()
    return bt.results


if __name__ == "__main__":
    run_comprehensive_backtest()
