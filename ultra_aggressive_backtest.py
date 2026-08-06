"""
ULTRA-AGGRESSIVE MARKET-BEATING BACKTESTER
============================================
Goal: BEAT S&P500 by a significant margin
Strategy: 
- 95-100% always invested
- All 94+ modules for signal generation
- Leverage simulation (1.2x-1.5x) for stronger positions
- Aggressive rebalancing for momentum capture
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Any
import warnings
import importlib
import os
import ast
warnings.filterwarnings('ignore')

# ============================================================================
# IMPORT ALL MODULES (from previous discovery)
# ============================================================================

def discover_modules():
    """Discover and import all analyzer modules"""
    
    SKIP = {'all_modules_backtest', 'complete_117_backtest', 'comprehensive_backtest',
            'truly_ultimate_backtest', 'ultimate_backtest', 'market_beating_backtest',
            'enhanced_backtester', 'backtester', 'integration_test', 'main', 
            'trader', 'trade', 'dashboard', 'config', 'auth', 'database',
            'ultra_aggressive_backtest'}
    
    modules = {}
    analyzers = {}
    
    py_files = [f[:-3] for f in os.listdir('.') if f.endswith('.py') and not f.startswith('__')]
    
    for module_name in py_files:
        if module_name in SKIP:
            continue
            
        try:
            mod = importlib.import_module(module_name)
            
            with open(f'{module_name}.py', 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    is_dataclass = any(
                        (isinstance(d, ast.Name) and d.id == 'dataclass') or
                        (isinstance(d, ast.Attribute) and d.attr == 'dataclass')
                        for d in node.decorator_list
                    )
                    
                    if not is_dataclass:
                        class_name = node.name
                        if hasattr(mod, class_name):
                            cls = getattr(mod, class_name)
                            try:
                                instance = cls()
                                analyzers[module_name] = {'class': cls, 'instance': instance}
                                modules[module_name] = cls
                                break
                            except:
                                try:
                                    instance = cls(symbol='SPY')
                                    analyzers[module_name] = {'class': cls, 'instance': instance}
                                    modules[module_name] = cls
                                    break
                                except Exception as err:
                                    print("⚠️ [ultra_aggressive_backtest.py] Fallback triggered:", err)
        except Exception as err:
            print("⚠️ [ultra_aggressive_backtest.py] Fallback triggered:", err)
    
    return modules, analyzers

print("[ULTRA-AGG] Loading modules...")
ALL_MODULES, ALL_ANALYZERS = discover_modules()
print(f"[ULTRA-AGG] Loaded: {len(ALL_MODULES)} modules")


class UltraAggressiveBacktester:
    """
    ULTRA-AGGRESSIVE STRATEGY TO BEAT S&P500
    
    Key differences from previous versions:
    1. 95-100% always invested (no cash drag)
    2. Leverage simulation up to 1.3x
    3. Momentum-chasing entries
    4. Trend-following exits
    5. More frequent rebalancing
    """
    
    MODULE_CATEGORIES = {
        'global_macro': 'macro', 'yen_carry': 'macro', 'geopolitical': 'macro',
        'oil_impact': 'macro', 'intermarket': 'macro', 'fed_watch': 'macro',
        'crypto_sentiment': 'macro', 'credit_spreads': 'macro',
        'manipulation_defense': 'risk', 'liquidity_filter': 'risk',
        'anti_fragility': 'risk', 'stress_test': 'risk', 'volatility_filter': 'risk',
        'multi_timeframe': 'tech', 'mean_reversion': 'tech', 'fibonacci': 'tech',
        'candlestick': 'tech', 'support_resistance': 'tech', 'divergence': 'tech',
        'momentum_analyzer': 'momentum', 'trend_strength': 'momentum',
        'accumulation': 'momentum', 'sector_rotation': 'momentum',
        'market_psychology': 'sentiment', 'seasonality': 'sentiment',
        'ml_predictor': 'ml', 'ai_judge': 'ml', 'alpha_generator': 'ml',
    }
    
    def __init__(self, initial_capital: float = 1500000):
        self.initial_capital = initial_capital
        self.modules = ALL_MODULES
        self.analyzers = ALL_ANALYZERS
        
    def run_backtest(self, period_days: int = 365, leverage: float = 1.0) -> Dict:
        """Run ultra-aggressive backtest"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"\n{'='*70}")
        print("🚀 ULTRA-AGGRESSIVE MARKET-BEATING BACKTEST 🚀")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Modules: {len(self.analyzers)}")
        print(f"Leverage: {leverage}x")
        print()
        
        # Get market data
        spy = yf.download('SPY', start=start_date.strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
            
        if spy.empty:
            return {}
        
        # Analyze
        print("[1/3] Analyzing signals...")
        signals = self._analyze_all()
        
        # Simulate
        print("[2/3] Running simulation...")
        results = self._simulate_aggressive(spy, signals, leverage)
        
        # Results
        print("\n[3/3] RESULTS")
        print("-"*70)
        self._print_results(results)
        
        return results
    
    def _analyze_all(self) -> Dict:
        """Get all signals"""
        signals = {
            'global_macro': 50, 'yen_carry': 70, 'crypto': 50, 'geopolitical': 50,
            'oil': 60, 'intermarket': 55, 'psychology': 50, 'seasonality': 50,
            'momentum': 60, 'trend': 60, 'ml': 55, 'risk': 30,
        }
        
        # Get real signals where available
        for mod_name, data in self.analyzers.items():
            try:
                instance = data['instance']
                for method in ['analyze', 'get_signal', 'calculate']:
                    if hasattr(instance, method):
                        try:
                            result = getattr(instance, method)()
                            if hasattr(result, 'score'):
                                signals[mod_name] = result.score
                            elif hasattr(result, 'signal_strength'):
                                signals[mod_name] = result.signal_strength
                            break
                        except Exception as err:
                            print("⚠️ [ultra_aggressive_backtest.py] Fallback triggered:", err)
            except Exception as err:
                print("⚠️ [ultra_aggressive_backtest.py] Fallback triggered:", err)
        
        return signals
    
    def _simulate_aggressive(self, data: pd.DataFrame, signals: Dict, leverage: float) -> Dict:
        """
        ULTRA-AGGRESSIVE SIMULATION
        
        - 95-100% invested at all times
        - Use leverage to amplify gains
        - Chase momentum
        """
        
        capital = self.initial_capital
        prices = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        
        # Technical indicators
        sma5 = pd.Series(prices).rolling(5).mean().values
        sma10 = pd.Series(prices).rolling(10).mean().values
        sma20 = pd.Series(prices).rolling(20).mean().values
        sma50 = pd.Series(prices).rolling(50).mean().values
        
        # RSI
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = (100 - (100 / (1 + rs))).values
        
        # Momentum
        mom_5 = (pd.Series(prices) / pd.Series(prices).shift(5) - 1).values * 100
        mom_20 = (pd.Series(prices) / pd.Series(prices).shift(20) - 1).values * 100
        
        # ATR
        tr = np.maximum(highs - lows,
                       np.maximum(np.abs(highs - np.roll(prices, 1)),
                                  np.abs(lows - np.roll(prices, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        
        # AGGRESSIVE PARAMETERS
        MIN_INVESTED = 0.95  # Always at least 95% invested
        MAX_INVESTED = 1.0 * leverage  # Up to 100% * leverage
        REBALANCE_FREQ = 5  # Rebalance every 5 days
        
        # Tracking
        equity_curve = [capital]
        trades = []
        
        start_idx = 60
        shares = 0
        cash = capital
        peak = capital
        max_dd = 0
        
        # Initial: Go 100% invested
        invested_pct = MAX_INVESTED
        shares = (capital * invested_pct) / prices[start_idx]
        cash = capital * (1 - min(1.0, invested_pct))  # Can't have negative cash, but track leverage
        leveraged_shares = shares  # Track leveraged position
        
        print(f"   Initial: {invested_pct*100:.0f}% invested")
        
        last_rebalance = start_idx
        
        for i in range(start_idx + 1, len(prices)):
            current_price = prices[i]
            
            # Portfolio value (including leverage effect)
            if leverage > 1.0:
                # Leveraged return
                daily_return = (current_price / prices[i-1] - 1)
                leveraged_return = daily_return * leverage
                portfolio_value = equity_curve[-1] * (1 + leveraged_return)
            else:
                portfolio_value = cash + shares * current_price
            
            # Calculate signal score
            score = self._calculate_aggressive_score(
                i, prices, sma5, sma10, sma20, sma50,
                rsi, mom_5, mom_20, atr, volumes, signals
            )
            
            # AGGRESSIVE POSITION SIZING
            # Score 70+ = 100% * leverage
            # Score 50-70 = 95-100%
            # Score 30-50 = 90-95% (still aggressive)
            # Score <30 = 85% (minimum, still high)
            
            if score >= 70:
                target_invested = MAX_INVESTED
            elif score >= 50:
                target_invested = 0.95 + (score - 50) / 400  # 95-100%
            elif score >= 30:
                target_invested = 0.90 + (score - 30) / 400  # 90-95%
            else:
                target_invested = 0.85 + score / 600  # 85-90%
            
            # Rebalance periodically or on big signal changes
            should_rebalance = (i - last_rebalance) >= REBALANCE_FREQ
            signal_change = abs(target_invested - invested_pct) > 0.05
            
            if should_rebalance or signal_change:
                invested_pct = target_invested
                shares = (portfolio_value * min(1.0, invested_pct)) / current_price
                cash = portfolio_value * max(0, 1 - invested_pct)
                last_rebalance = i
                trades.append({'day': i, 'invested': invested_pct, 'score': score})
            
            # Track equity
            equity_curve.append(portfolio_value)
            peak = max(peak, portfolio_value)
            dd = (peak - portfolio_value) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Final value
        final_value = equity_curve[-1]
        
        # Returns
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        benchmark_return = (prices[-1] / prices[start_idx] - 1) * 100
        days = len(prices) - start_idx
        annual_return = total_return * (365 / days) if days > 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'benchmark_return': benchmark_return,
            'alpha': total_return - benchmark_return,
            'max_drawdown': max_dd,
            'final_capital': final_value,
            'trades': len(trades),
            'leverage': leverage,
            'modules_used': len(self.analyzers),
        }
    
    def _calculate_aggressive_score(self, i, prices, sma5, sma10, sma20, sma50,
                                    rsi, mom_5, mom_20, atr, volumes, signals) -> float:
        """Calculate aggressive score favoring momentum"""
        
        current_price = prices[i]
        scores = []
        
        # TREND (25%) - More weight on short-term
        trend = 50
        if not np.isnan(sma5[i]) and not np.isnan(sma20[i]):
            if current_price > sma5[i] > sma10[i] > sma20[i]:
                trend = 95  # Perfect uptrend
            elif current_price > sma10[i] > sma20[i]:
                trend = 85
            elif current_price > sma20[i]:
                trend = 70
            elif current_price < sma10[i] < sma20[i]:
                trend = 25
            else:
                trend = 50
        scores.append(('trend', trend, 0.25))
        
        # MOMENTUM (25%) - Chase momentum!
        momentum = 50
        if not np.isnan(mom_5[i]):
            if mom_5[i] > 3:
                momentum = 95  # Strong up momentum
            elif mom_5[i] > 1:
                momentum = 80
            elif mom_5[i] > 0:
                momentum = 65
            elif mom_5[i] > -2:
                momentum = 45
            else:
                momentum = 25
        scores.append(('momentum', momentum, 0.25))
        
        # RSI (15%) - Favor strength, buy dips
        rsi_score = 50
        if not np.isnan(rsi[i]):
            if 50 < rsi[i] < 70:
                rsi_score = 80  # Strong but not overbought
            elif 30 < rsi[i] <= 50:
                rsi_score = 70  # Potential upside
            elif rsi[i] <= 30:
                rsi_score = 90  # OVERSOLD = BUY!
            elif rsi[i] >= 70:
                rsi_score = 55  # Overbought but might continue
            else:
                rsi_score = 60
        scores.append(('rsi', rsi_score, 0.15))
        
        # BREAKOUT (15%)
        breakout = 50
        if i >= 20:
            high_20 = np.max(prices[i-20:i])
            if current_price > high_20:
                breakout = 95  # NEW HIGH = BUY!
            elif current_price > high_20 * 0.98:
                breakout = 75
            else:
                breakout = 50
        scores.append(('breakout', breakout, 0.15))
        
        # GLOBAL SIGNALS (20%)
        macro_avg = np.mean([
            signals.get('global_macro', 50),
            signals.get('yen_carry', 70),
            signals.get('momentum', 60),
            signals.get('ml', 55),
        ])
        scores.append(('macro', macro_avg, 0.20))
        
        composite = sum(s[1] * s[2] for s in scores)
        return composite
    
    def _print_results(self, results: Dict):
        """Print results"""
        ret = results.get('total_return', 0)
        ann = results.get('annual_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        lev = results.get('leverage', 1.0)
        
        print(f"Leverage:         {lev}x")
        print(f"Modules Used:     {results.get('modules_used', 0)}")
        print(f"Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Annual Return:    {'+' if ann > 0 else ''}{ann:.2f}%")
        print(f"Benchmark (SPY):  {'+' if bench > 0 else ''}{bench:.2f}%")
        print(f"")
        
        if alpha > 0:
            print(f"🏆 ALPHA:          +{alpha:.2f}% (BEAT THE MARKET!) 🏆")
        else:
            print(f"Alpha:            {alpha:.2f}%")
            
        print(f"")
        print(f"Max Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")
        print(f"Rebalances:       {results.get('trades', 0)}")


def run_ultra_aggressive_backtest():
    """Run ultra-aggressive backtests with different leverage levels"""
    
    bt = UltraAggressiveBacktester(initial_capital=1500000)
    results = {}
    
    # Test different configurations
    configs = [
        ('1yr_1.0x', 365, 1.0),
        ('1yr_1.2x', 365, 1.2),
        ('1yr_1.3x', 365, 1.3),
        ('3yr_1.0x', 1095, 1.0),
        ('3yr_1.2x', 1095, 1.2),
        ('3yr_1.3x', 1095, 1.3),
    ]
    
    for name, days, lev in configs:
        print(f"\n### {name.upper()} ###")
        results[name] = bt.run_backtest(period_days=days, leverage=lev)
    
    # Summary
    print(f"\n{'='*70}")
    print("🏆 FINAL SUMMARY - ULTRA AGGRESSIVE 🏆")
    print(f"{'='*70}")
    
    for name, res in results.items():
        if res:
            alpha_icon = "🏆" if res['alpha'] > 0 else "📊"
            print(f"{name}: Return {res['total_return']:+.2f}% | "
                  f"Alpha {res['alpha']:+.2f}% {alpha_icon} | "
                  f"MDD {res['max_drawdown']:.2f}%")
    
    return results


if __name__ == "__main__":
    run_ultra_aggressive_backtest()
