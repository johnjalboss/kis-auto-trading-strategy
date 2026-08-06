"""
ULTIMATE ALL-MODULES BACKTESTER
================================
Imports and uses ALL available modules for maximum intelligence.
Auto-detects and loads all analyzer classes from the project.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import warnings
import importlib
import os
import ast
warnings.filterwarnings('ignore')

# ============================================================================
# AUTO-DISCOVER AND IMPORT ALL MODULES
# ============================================================================

def discover_all_modules():
    """Automatically discover and import all analyzer classes"""
    
    # Skip these files (not analyzers)
    SKIP_FILES = {
        'all_modules_backtest', 'complete_117_backtest', 'comprehensive_backtest',
        'truly_ultimate_backtest', 'ultimate_backtest', 'market_beating_backtest',
        'enhanced_backtester', 'backtester', 'integration_test', 'main', 
        'trader', 'dashboard', 'config', 'auth', 'database', '__init__'
    }
    
    modules = {}
    analyzers = {}
    
    # Get all Python files
    py_files = [f[:-3] for f in os.listdir('.') if f.endswith('.py') and not f.startswith('__')]
    
    for module_name in py_files:
        if module_name in SKIP_FILES:
            continue
            
        try:
            # Import the module
            mod = importlib.import_module(module_name)
            
            # Get the source file and parse it
            with open(f'{module_name}.py', 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # Find all non-dataclass classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a dataclass (skip those)
                    is_dataclass = any(
                        (isinstance(d, ast.Name) and d.id == 'dataclass') or
                        (isinstance(d, ast.Attribute) and d.attr == 'dataclass')
                        for d in node.decorator_list
                    )
                    
                    if not is_dataclass:
                        class_name = node.name
                        if hasattr(mod, class_name):
                            cls = getattr(mod, class_name)
                            # Try to instantiate without arguments
                            try:
                                instance = cls()
                                analyzers[module_name] = {
                                    'class': cls,
                                    'instance': instance,
                                    'name': class_name
                                }
                                modules[module_name] = cls
                                break  # Take first valid class
                            except TypeError:
                                # Needs arguments, try with common patterns
                                try:
                                    instance = cls(symbol='SPY')
                                    analyzers[module_name] = {
                                        'class': cls,
                                        'instance': instance,
                                        'name': class_name
                                    }
                                    modules[module_name] = cls
                                    break
                                except Exception as err:
                                    print("⚠️ [all_modules_backtest.py] Fallback triggered:", err)
                            except Exception as err:
                                print("⚠️ [all_modules_backtest.py] Fallback triggered:", err)
                                
        except Exception as e:
            print("⚠️ [all_modules_backtest.py] Fallback triggered:", e)
    
    return modules, analyzers

print("[ALL-MODULES] Discovering modules...")
ALL_MODULES, ALL_ANALYZERS = discover_all_modules()
print(f"[ALL-MODULES] Loaded: {len(ALL_MODULES)} modules")
print(f"[ALL-MODULES] Active analyzers: {len(ALL_ANALYZERS)}")


class UltimateAllModulesBacktester:
    """
    THE ULTIMATE BACKTESTER
    
    Uses EVERY available module for maximum trading intelligence.
    Strategy: Always invested with dynamic sizing based on ALL signals.
    """
    
    # Category weights for scoring
    CATEGORY_WEIGHTS = {
        'global_macro': 0.12,
        'risk': 0.12,
        'technical': 0.18,
        'momentum': 0.12,
        'sentiment': 0.10,
        'fundamental': 0.08,
        'ml_ai': 0.10,
        'execution': 0.08,
        'event': 0.05,
        'volume': 0.05,
    }
    
    # Module to category mapping
    MODULE_CATEGORIES = {
        'global_macro': 'global_macro',
        'yen_carry': 'global_macro',
        'geopolitical': 'global_macro',
        'oil_impact': 'global_macro',
        'intermarket': 'global_macro',
        'fed_watch': 'global_macro',
        'credit_spreads': 'global_macro',
        'crypto_sentiment': 'global_macro',
        
        'manipulation_defense': 'risk',
        'liquidity_filter': 'risk',
        'anti_fragility': 'risk',
        'stress_test': 'risk',
        'drawdown_controller': 'risk',
        'drawdown_recovery': 'risk',
        'correlation_regime': 'risk',
        'volatility_filter': 'risk',
        'emergency_stop': 'risk',
        'risk_manager': 'risk',
        'risk_parity': 'risk',
        
        'multi_timeframe': 'technical',
        'mean_reversion': 'technical',
        'support_resistance': 'technical',
        'fibonacci': 'technical',
        'candlestick': 'technical',
        'gap_fill': 'technical',
        'divergence': 'technical',
        'trend_strength': 'technical',
        'indicators': 'technical',
        'technical_analyzer': 'technical',
        
        'momentum_analyzer': 'momentum',
        'accumulation': 'momentum',
        'sector_rotation': 'momentum',
        'etf_flows': 'momentum',
        'screener': 'momentum',
        
        'market_psychology': 'sentiment',
        'seasonality': 'sentiment',
        'news_analyzer': 'sentiment',
        'insider_tracker': 'sentiment',
        'options_flow': 'sentiment',
        'sentiment_analyzer': 'sentiment',
        
        'fundamental_analyzer': 'fundamental',
        'earnings_analyzer': 'fundamental',
        'earnings_calendar': 'fundamental',
        'factor_analysis': 'fundamental',
        
        'ml_predictor': 'ml_ai',
        'ai_judge': 'ml_ai',
        'alpha_generator': 'ml_ai',
        'regime_detector': 'ml_ai',
        'market_regime': 'ml_ai',
        'adaptive_strategy': 'ml_ai',
        
        'position_sizer': 'execution',
        'dynamic_stop': 'execution',
        'exit_optimizer': 'execution',
        'smart_order': 'execution',
        'order_manager': 'execution',
        'trailing_stop': 'execution',
        'hedge_manager': 'execution',
        'cost_model': 'execution',
        'tax_optimizer': 'execution',
        
        'event_calendar': 'event',
        'economic_calendar': 'event',
        
        'volume_profile': 'volume',
    }
    
    def __init__(self, initial_capital: float = 1500000):
        self.initial_capital = initial_capital
        self.modules = ALL_MODULES
        self.analyzers = ALL_ANALYZERS
        
        print(f"\n[ULTIMATE] Active Modules: {len(self.modules)}")
        print(f"[ULTIMATE] Categories: {self._count_by_category()}")
    
    def _count_by_category(self) -> Dict[str, int]:
        """Count modules by category"""
        counts = {}
        for mod_name in self.analyzers:
            cat = self.MODULE_CATEGORIES.get(mod_name, 'other')
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def run_backtest(self, period_days: int = 365, aggressive: bool = True) -> Dict:
        """Run backtest with ALL modules"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"\n{'='*70}")
        print("ULTIMATE ALL-MODULES BACKTEST")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Active Modules: {len(self.analyzers)}")
        print(f"Mode: {'AGGRESSIVE' if aggressive else 'CONSERVATIVE'}")
        print()
        
        # Get market data
        spy = yf.download('SPY', start=start_date.strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
            
        if spy.empty:
            print("Error: No market data")
            return {}
        
        # Analyze with ALL modules
        print("[1/3] Analyzing with ALL modules...")
        signals = self._analyze_all()
        self._print_signals(signals)
        
        # Run simulation
        print("\n[2/3] Running Simulation...")
        results = self._simulate(spy, signals, aggressive)
        
        # Print results
        print("\n[3/3] Results")
        print("-"*70)
        self._print_results(results)
        
        return results
    
    def _analyze_all(self) -> Dict:
        """Get signals from ALL available analyzers"""
        signals = {}
        
        # Initialize with defaults
        defaults = {
            'global_macro': 50, 'yen_carry': 70, 'crypto': 50, 'geopolitical': 50,
            'oil': 60, 'intermarket': 55, 'fed': 50, 'credit_spreads': 50,
            'manipulation_risk': 20, 'liquidity': 80, 'anti_fragility': 50,
            'stress': 30, 'drawdown_risk': 20, 'correlation_risk': 30,
            'volatility': 50, 'emergency': 10,
            'multi_tf': 60, 'mean_reversion': 50, 'support_resistance': 60,
            'fibonacci': 50, 'candlestick': 50, 'volume_profile': 50,
            'gap_fill': 50, 'divergence': 50, 'trend_strength': 60,
            'momentum': 60, 'accumulation': 50, 'sector_rotation': 50, 'etf_flows': 55,
            'psychology': 50, 'seasonality': 50, 'news': 50, 'insider': 50, 'options_flow': 50,
            'fundamental': 50, 'earnings': 50, 'factor': 50,
            'ml_prediction': 55, 'ai_confidence': 60, 'alpha': 55, 'regime': 50,
            'position_size': 0.7, 'stop_level': -0.05, 'exit_score': 50,
        }
        signals.update(defaults)
        
        # Try to get real signals from each analyzer
        for mod_name, data in self.analyzers.items():
            instance = data['instance']
            
            try:
                # Try common analysis methods
                result = None
                for method in ['analyze', 'get_signal', 'calculate', 'check']:
                    if hasattr(instance, method):
                        try:
                            result = getattr(instance, method)()
                            break
                        except:
                            try:
                                result = getattr(instance, method)('SPY')
                                break
                            except Exception as err:
                                print("⚠️ [all_modules_backtest.py] Fallback triggered:", err)
                
                if result is not None:
                    # Extract score from result
                    if hasattr(result, 'score'):
                        signals[mod_name] = result.score
                    elif hasattr(result, 'sentiment_score'):
                        signals[mod_name] = result.sentiment_score
                    elif hasattr(result, 'risk_score'):
                        signals[mod_name] = 100 - result.risk_score
                    elif hasattr(result, 'signal_strength'):
                        signals[mod_name] = result.signal_strength
                    elif hasattr(result, 'overall_risk'):
                        risk_map = {"RISK_OFF": 20, "CAUTION": 40, "NEUTRAL": 50, "RISK_ON": 80}
                        signals[mod_name] = risk_map.get(result.overall_risk, 50)
                    elif hasattr(result, 'impact_severity'):
                        signals[mod_name] = 100 - result.impact_severity
                    elif hasattr(result, 'fear_greed_index'):
                        signals[mod_name] = result.fear_greed_index
                    elif hasattr(result, 'combined_score'):
                        signals[mod_name] = 50 + result.combined_score
                    elif isinstance(result, (int, float)):
                        signals[mod_name] = min(100, max(0, result))
                        
            except Exception as err:
                print("⚠️ [all_modules_backtest.py] Fallback triggered:", err)
        
        return signals
    
    def _print_signals(self, signals: Dict):
        """Print signals by category"""
        categories = {}
        
        for mod_name, score in signals.items():
            if isinstance(score, (int, float)) and 0 <= score <= 100:
                cat = self.MODULE_CATEGORIES.get(mod_name, 'other')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(score)
        
        for cat, scores in sorted(categories.items()):
            if scores:
                avg = np.mean(scores)
                status = "+" if avg > 55 else "-" if avg < 45 else " "
                print(f"   {cat:15}: {avg:.0f}/100 [{status}] ({len(scores)} signals)")
    
    def _simulate(self, data: pd.DataFrame, signals: Dict, aggressive: bool) -> Dict:
        """Run simulation with ALL signals"""
        
        capital = self.initial_capital
        prices = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        
        # Technical indicators
        sma10 = pd.Series(prices).rolling(10).mean().values
        sma20 = pd.Series(prices).rolling(20).mean().values
        sma50 = pd.Series(prices).rolling(50).mean().values
        sma200 = pd.Series(prices).rolling(200).mean().values
        
        # RSI
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = (100 - (100 / (1 + rs))).values
        
        # MACD
        ema12 = pd.Series(prices).ewm(span=12).mean().values
        ema26 = pd.Series(prices).ewm(span=26).mean().values
        macd = ema12 - ema26
        macd_signal = pd.Series(macd).ewm(span=9).mean().values
        
        # ATR
        tr = np.maximum(highs - lows,
                       np.maximum(np.abs(highs - np.roll(prices, 1)),
                                  np.abs(lows - np.roll(prices, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        
        # Volume SMA
        vol_sma = pd.Series(volumes).rolling(20).mean().values
        
        # Simulation parameters
        if aggressive:
            min_position = 0.60   # Minimum 60% invested
            max_position = 0.98  # Maximum 98% invested
            rebalance_threshold = 0.12  # Rebalance if 12% off target
        else:
            min_position = 0.40
            max_position = 0.80
            rebalance_threshold = 0.15
        
        # Tracking
        equity_curve = [capital]
        trades = []
        
        start_idx = 60
        shares = 0
        cash = capital
        peak = capital
        max_dd = 0
        
        # Calculate initial composite
        composite = self._calculate_composite(signals)
        initial_size = np.clip(composite / 100 + 0.2, min_position, max_position)
        
        shares = (capital * initial_size) / prices[start_idx]
        cash = capital * (1 - initial_size)
        
        print(f"   Composite Signal: {composite:.0f}/100")
        print(f"   Initial Position: {initial_size*100:.0f}%")
        
        for i in range(start_idx + 1, len(prices)):
            current_price = prices[i]
            portfolio_value = cash + shares * current_price
            
            # Calculate score using ALL factors
            score = self._calculate_complete_score(
                i, prices, sma10, sma20, sma50, sma200,
                rsi, macd, macd_signal, atr, volumes, vol_sma,
                signals
            )
            
            # Target position based on score
            target_size = np.clip(
                (score - 30) / 60 + min_position,
                min_position,
                max_position
            )
            
            current_size = (shares * current_price) / portfolio_value if portfolio_value > 0 else 0
            
            # Rebalance if needed
            if abs(target_size - current_size) > rebalance_threshold:
                target_shares = (portfolio_value * target_size) / current_price
                
                if target_shares > shares:
                    buy_shares = target_shares - shares
                    cost = buy_shares * current_price
                    if cost <= cash:
                        shares = target_shares
                        cash -= cost
                        trades.append({'type': 'ADD', 'size': target_size})
                else:
                    sell_shares = shares - target_shares
                    proceeds = sell_shares * current_price
                    shares = target_shares
                    cash += proceeds
                    trades.append({'type': 'REDUCE', 'size': target_size})
            
            # Track equity
            equity = cash + shares * current_price
            equity_curve.append(equity)
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Final value
        final_value = cash + shares * prices[-1]
        
        # Calculate returns
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
            'modules_used': len(self.analyzers),
            'equity_curve': equity_curve
        }
    
    def _calculate_composite(self, signals: Dict) -> float:
        """Calculate composite score from all signals"""
        category_scores = {}
        
        for mod_name, score in signals.items():
            if isinstance(score, (int, float)) and 0 <= score <= 100:
                cat = self.MODULE_CATEGORIES.get(mod_name, 'other')
                if cat not in category_scores:
                    category_scores[cat] = []
                category_scores[cat].append(score)
        
        # Weighted average
        total = 0
        weight_sum = 0
        
        for cat, scores in category_scores.items():
            weight = self.CATEGORY_WEIGHTS.get(cat, 0.05)
            total += np.mean(scores) * weight
            weight_sum += weight
        
        return total / weight_sum if weight_sum > 0 else 50
    
    def _calculate_complete_score(self, i, prices, sma10, sma20, sma50, sma200,
                                  rsi, macd, macd_signal, atr, volumes, vol_sma,
                                  signals) -> float:
        """Calculate complete score using ALL indicators"""
        
        scores = []
        current_price = prices[i]
        
        # TREND (0.20)
        trend = 50
        if not np.isnan(sma20[i]) and not np.isnan(sma50[i]):
            if current_price > sma10[i] > sma20[i] > sma50[i]:
                trend = 90
            elif current_price > sma20[i] > sma50[i]:
                trend = 80
            elif current_price > sma50[i]:
                trend = 65
            elif current_price < sma20[i] < sma50[i]:
                trend = 25
            else:
                trend = 50
        scores.append(('trend', trend, 0.20))
        
        # MOMENTUM (0.15)
        momentum = 50
        if not np.isnan(rsi[i]):
            if 45 < rsi[i] < 65:
                momentum = 70
            elif 30 < rsi[i] <= 45:
                momentum = 75
            elif rsi[i] <= 30:
                momentum = 80
            elif rsi[i] >= 70:
                momentum = 40
            else:
                momentum = 55
        if not np.isnan(macd[i]) and not np.isnan(macd_signal[i]):
            if macd[i] > macd_signal[i]:
                momentum += 5
            else:
                momentum -= 5
        scores.append(('momentum', np.clip(momentum, 0, 100), 0.15))
        
        # VOLUME (0.08)
        volume = 50
        if not np.isnan(vol_sma[i]) and vol_sma[i] > 0:
            vol_ratio = volumes[i] / vol_sma[i]
            if vol_ratio > 1.5 and trend > 60:
                volume = 80
            elif vol_ratio > 1.0:
                volume = 60
            else:
                volume = 45
        scores.append(('volume', volume, 0.08))
        
        # BREAKOUT (0.10)
        breakout = 50
        if i >= 20:
            high_20 = np.max(prices[i-20:i])
            low_20 = np.min(prices[i-20:i])
            if current_price > high_20:
                breakout = 85
            elif current_price < low_20:
                breakout = 20
        scores.append(('breakout', breakout, 0.10))
        
        # VOLATILITY (0.05)
        vol_score = 50
        if not np.isnan(atr[i]) and current_price > 0:
            atr_pct = atr[i] / current_price * 100
            vol_score = 70 if atr_pct < 1.0 else (35 if atr_pct > 2.5 else 55)
        scores.append(('volatility', vol_score, 0.05))
        
        # GLOBAL MACRO (0.15)
        macro_keys = ['global_macro', 'yen_carry', 'geopolitical', 'oil', 'intermarket']
        macro = np.mean([signals.get(k, 50) for k in macro_keys if k in signals])
        scores.append(('global_macro', macro, 0.15))
        
        # SENTIMENT (0.10)
        sentiment_keys = ['psychology', 'seasonality', 'news', 'options_flow']
        sentiment = np.mean([signals.get(k, 50) for k in sentiment_keys if k in signals])
        scores.append(('sentiment', sentiment, 0.10))
        
        # ML/AI (0.10)
        ml_keys = ['ml_prediction', 'ai_confidence', 'alpha', 'regime']
        ml = np.mean([signals.get(k, 50) for k in ml_keys if k in signals])
        scores.append(('ml_ai', ml, 0.10))
        
        # RISK (0.07)
        risk_keys = ['manipulation_risk', 'liquidity', 'stress', 'drawdown_risk']
        risk_scores = [100 - signals.get(k, 50) if 'risk' in k else signals.get(k, 50) 
                      for k in risk_keys if k in signals]
        risk = np.mean(risk_scores) if risk_scores else 50
        scores.append(('risk', risk, 0.07))
        
        # Calculate weighted composite
        composite = sum(s[1] * s[2] for s in scores)
        
        return composite
    
    def _print_results(self, results: Dict):
        """Print final results"""
        ret = results.get('total_return', 0)
        ann = results.get('annual_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        print(f"Modules Used:     {results.get('modules_used', 0)}")
        print(f"Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Annual Return:    {'+' if ann > 0 else ''}{ann:.2f}%")
        print(f"Benchmark (SPY):  {'+' if bench > 0 else ''}{bench:.2f}%")
        print(f"Alpha:            {'+' if alpha > 0 else ''}{alpha:.2f}%")
        print(f"Max Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")
        print(f"Rebalances:       {results.get('trades', 0)}")
        
        if alpha > 0:
            print(f"\n🏆 BEAT THE MARKET BY {alpha:.2f}%! 🏆")
        else:
            print(f"\n📊 Strategy: {ret:.2f}% | Benchmark: {bench:.2f}%")


def run_all_modules_backtest():
    """Run backtest with ALL modules"""
    
    bt = UltimateAllModulesBacktester(initial_capital=1500000)
    results = {}
    
    print("\n### 1 YEAR - AGGRESSIVE ###")
    results['1yr_agg'] = bt.run_backtest(period_days=365, aggressive=True)
    
    print("\n### 3 YEARS - AGGRESSIVE ###")
    results['3yr_agg'] = bt.run_backtest(period_days=1095, aggressive=True)
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY - ALL MODULES")
    print(f"{'='*70}")
    
    for name, res in results.items():
        if res:
            print(f"{name}: Return {res['total_return']:+.2f}% | "
                  f"Alpha {res['alpha']:+.2f}% | "
                  f"MDD {res['max_drawdown']:.2f}% | "
                  f"Modules: {res['modules_used']}")
    
    return results


if __name__ == "__main__":
    run_all_modules_backtest()
