import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import warnings
import importlib
import ast
warnings.filterwarnings('ignore')

sys.path.append(r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading")

# Auto-discover modules from kis-auto-trading directory
def discover_all_modules():
    SKIP_FILES = {
        'all_modules_backtest', 'complete_117_backtest', 'comprehensive_backtest',
        'truly_ultimate_backtest', 'ultimate_backtest', 'market_beating_backtest',
        'enhanced_backtester', 'backtester', 'integration_test', 'main', 
        'trader', 'dashboard', 'config', 'auth', 'database', '__init__'
    }
    
    modules = {}
    analyzers = {}
    
    # Python files in local kis-auto-trading directory
    src_dir = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading"
    py_files = [f[:-3] for f in os.listdir(src_dir) if f.endswith('.py') and not f.startswith('__')]
    
    # Temporary append path
    sys.path.insert(0, src_dir)
    
    for module_name in py_files:
        if module_name in SKIP_FILES:
            continue
            
        try:
            mod = importlib.import_module(module_name)
            
            with open(os.path.join(src_dir, f'{module_name}.py'), 'r', encoding='utf-8') as f:
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
                                analyzers[module_name] = {
                                    'class': cls,
                                    'instance': instance,
                                    'name': class_name
                                }
                                modules[module_name] = cls
                                break
                            except TypeError:
                                try:
                                    instance = cls(symbol='QQQ')
                                    analyzers[module_name] = {
                                        'class': cls,
                                        'instance': instance,
                                        'name': class_name
                                    }
                                    modules[module_name] = cls
                                    break
                                except Exception as err:
                                    print("⚠️ [all_modules_backtest_vs_qqq.py] Fallback triggered:", err)
                            except Exception as err:
                                print("⚠️ [all_modules_backtest_vs_qqq.py] Fallback triggered:", err)
        except Exception as err:
            print("⚠️ [all_modules_backtest_vs_qqq.py] Fallback triggered:", err)
            
    return modules, analyzers

print("[ALL-MODULES] Discovering modules...")
ALL_MODULES, ALL_ANALYZERS = discover_all_modules()
print(f"[ALL-MODULES] Loaded: {len(ALL_MODULES)} modules")
print(f"[ALL-MODULES] Active analyzers: {len(ALL_ANALYZERS)}")

class UltimateAllModulesBacktester:
    CATEGORY_WEIGHTS = {
        'global_macro': 0.12, 'risk': 0.12, 'technical': 0.18, 'momentum': 0.12,
        'sentiment': 0.10, 'fundamental': 0.08, 'ml_ai': 0.10, 'execution': 0.08,
        'event': 0.05, 'volume': 0.05,
    }
    
    MODULE_CATEGORIES = {
        'global_macro': 'global_macro', 'yen_carry': 'global_macro', 'geopolitical': 'global_macro',
        'oil_impact': 'global_macro', 'intermarket': 'global_macro', 'fed_watch': 'global_macro',
        'credit_spreads': 'global_macro', 'crypto_sentiment': 'global_macro',
        'manipulation_defense': 'risk', 'liquidity_filter': 'risk', 'anti_fragility': 'risk',
        'stress_test': 'risk', 'drawdown_controller': 'risk', 'drawdown_recovery': 'risk',
        'correlation_regime': 'risk', 'volatility_filter': 'risk', 'emergency_stop': 'risk',
        'risk_manager': 'risk', 'risk_parity': 'risk',
        'multi_timeframe': 'technical', 'mean_reversion': 'technical', 'support_resistance': 'technical',
        'fibonacci': 'technical', 'candlestick': 'technical', 'gap_fill': 'technical',
        'divergence': 'technical', 'trend_strength': 'technical', 'indicators': 'technical',
        'technical_analyzer': 'technical',
        'momentum_analyzer': 'momentum', 'accumulation': 'momentum', 'sector_rotation': 'momentum',
        'etf_flows': 'momentum', 'screener': 'momentum',
        'market_psychology': 'sentiment', 'seasonality': 'sentiment', 'news_analyzer': 'sentiment',
        'insider_tracker': 'sentiment', 'options_flow': 'sentiment', 'sentiment_analyzer': 'sentiment',
        'fundamental_analyzer': 'fundamental', 'earnings_analyzer': 'fundamental',
        'earnings_calendar': 'fundamental', 'factor_analysis': 'fundamental',
        'ml_predictor': 'ml_ai', 'ai_judge': 'ml_ai', 'alpha_generator': 'ml_ai',
        'regime_detector': 'ml_ai', 'market_regime': 'ml_ai', 'adaptive_strategy': 'ml_ai',
        'position_sizer': 'execution', 'dynamic_stop': 'execution', 'exit_optimizer': 'execution',
        'smart_order': 'execution', 'order_manager': 'execution', 'trailing_stop': 'execution',
        'hedge_manager': 'execution', 'cost_model': 'execution', 'tax_optimizer': 'execution',
        'event_calendar': 'event', 'economic_calendar': 'event',
        'volume_profile': 'volume',
    }
    
    def __init__(self, initial_capital: float = 150000000.0):
        self.initial_capital = initial_capital
        self.modules = ALL_MODULES
        self.analyzers = ALL_ANALYZERS
        
    def run_backtest(self, period_days: int = 365, aggressive: bool = True) -> Dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get market data (QQQ)
        benchmark_ticker = 'QQQ'
        qqq_raw = yf.download(benchmark_ticker, start=start_date.strftime('%Y-%m-%d'),
                             end=end_date.strftime('%Y-%m-%d'), progress=False)
                             
        if hasattr(qqq_raw.columns, 'get_level_values'):
            qqq_raw.columns = qqq_raw.columns.get_level_values(0)
            
        if qqq_raw.empty:
            print("Error: No market data")
            return {}
            
        benchmark_df = qqq_raw['Close']
        if isinstance(benchmark_df, pd.DataFrame):
            benchmark_df = benchmark_df.iloc[:, 0]
            
        benchmark_df = benchmark_df.ffill().bfill()
        
        # Get QQQ Open/High/Low/Volume for strategy price feed simulation
        spy = qqq_raw.copy()
        
        # Analyze with ALL modules
        print("[1/3] Analyzing with ALL modules...")
        signals = self._analyze_all()
        
        # Run simulation
        print("[2/3] Running Simulation...")
        results = self._simulate(spy, benchmark_df, signals, aggressive)
        
        # Print results
        print("\n[3/3] Results")
        print("-" * 70)
        self._print_results(results)
        
        return results
        
    def _analyze_all(self) -> Dict:
        signals = {}
        defaults = {
            'global_macro': 55, 'yen_carry': 70, 'crypto': 50, 'geopolitical': 60,
            'oil': 55, 'intermarket': 55, 'fed': 50, 'credit_spreads': 50,
            'manipulation_risk': 10, 'liquidity': 85, 'anti_fragility': 60,
            'stress': 20, 'drawdown_risk': 10, 'correlation_risk': 20,
            'volatility': 55, 'emergency': 5,
            'multi_tf': 65, 'mean_reversion': 50, 'support_resistance': 60,
            'fibonacci': 50, 'candlestick': 50, 'volume_profile': 55,
            'gap_fill': 50, 'divergence': 50, 'trend_strength': 65,
            'momentum': 65, 'accumulation': 55, 'sector_rotation': 55, 'etf_flows': 60,
            'psychology': 55, 'seasonality': 55, 'news': 60, 'insider': 55, 'options_flow': 60,
            'fundamental': 65, 'earnings': 60, 'factor': 55,
            'ml_prediction': 60, 'ai_confidence': 65, 'alpha': 60, 'regime': 55,
            'position_size': 0.8, 'stop_level': -0.05, 'exit_score': 45,
        }
        signals.update(defaults)
        
        for mod_name, data in self.analyzers.items():
            instance = data['instance']
            try:
                result = None
                for method in ['analyze', 'get_signal', 'calculate', 'check']:
                    if hasattr(instance, method):
                        try:
                            result = getattr(instance, method)()
                            break
                        except:
                            try:
                                result = getattr(instance, method)('QQQ')
                                break
                            except Exception as err:
                                print("⚠️ [all_modules_backtest_vs_qqq.py] Fallback triggered:", err)
                
                if result is not None:
                    if hasattr(result, 'score'):
                        signals[mod_name] = result.score
                    elif hasattr(result, 'sentiment_score'):
                        signals[mod_name] = result.sentiment_score
                    elif hasattr(result, 'risk_score'):
                        signals[mod_name] = 100 - result.risk_score
                    elif isinstance(result, (int, float)):
                        signals[mod_name] = min(100, max(0, result))
            except Exception as err:
                print("⚠️ [all_modules_backtest_vs_qqq.py] Fallback triggered:", err)
        return signals

    def _simulate(self, data: pd.DataFrame, benchmark_df: pd.Series, signals: Dict, aggressive: bool) -> Dict:
        capital = self.initial_capital
        prices = data['Close'].values.flatten()
        highs = data['High'].values.flatten()
        lows = data['Low'].values.flatten()
        volumes = data['Volume'].values.flatten()
        
        sma10 = pd.Series(prices).rolling(10).mean().values
        sma20 = pd.Series(prices).rolling(20).mean().values
        sma50 = pd.Series(prices).rolling(50).mean().values
        sma200 = pd.Series(prices).rolling(200).mean().values
        
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = (100 - (100 / (1 + rs))).values
        
        ema12 = pd.Series(prices).ewm(span=12).mean().values
        ema26 = pd.Series(prices).ewm(span=26).mean().values
        macd = ema12 - ema26
        macd_signal = pd.Series(macd).ewm(span=9).mean().values
        
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(prices, 1)), np.abs(lows - np.roll(prices, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        vol_sma = pd.Series(volumes).rolling(20).mean().values
        
        min_position = 0.60 if aggressive else 0.40
        max_position = 0.98 if aggressive else 0.80
        rebalance_threshold = 0.10
        
        equity_curve = [capital]
        trades = []
        start_idx = 60
        shares = 0
        cash = capital
        peak = capital
        max_dd = 0
        
        # Portfolio weight calculation
        composite = self._calculate_composite(signals)
        initial_size = np.clip(composite / 100 + 0.2, min_position, max_position)
        
        shares = (capital * initial_size) / prices[start_idx]
        cash = capital * (1 - initial_size)
        
        for i in range(start_idx + 1, len(prices)):
            current_price = prices[i]
            portfolio_value = cash + shares * current_price
            
            score = self._calculate_complete_score(
                i, prices, sma10, sma20, sma50, sma200,
                rsi, macd, macd_signal, atr, volumes, vol_sma,
                signals
            )
            
            target_size = np.clip((score - 30) / 60 + min_position, min_position, max_position)
            current_size = (shares * current_price) / portfolio_value if portfolio_value > 0 else 0
            
            if abs(target_size - current_size) > rebalance_threshold:
                target_shares = (portfolio_value * target_size) / current_price
                if target_shares > shares:
                    buy_shares = target_shares - shares
                    cost = buy_shares * current_price
                    if cost <= cash:
                        shares = target_shares
                        cash -= cost
                        trades.append({'type': 'ADD'})
                else:
                    sell_shares = shares - target_shares
                    proceeds = sell_shares * current_price
                    shares = target_shares
                    cash += proceeds
                    trades.append({'type': 'REDUCE'})
            
            equity = cash + shares * current_price
            equity_curve.append(equity)
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
            
        final_value = cash + shares * prices[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        benchmark_start = benchmark_df.iloc[start_idx]
        benchmark_end = benchmark_df.iloc[-1]
        benchmark_return = (benchmark_end - benchmark_start) / benchmark_start * 100
        
        # Benchmark MDD
        qqq_values = benchmark_df.values.flatten()
        qqq_series = pd.Series(qqq_values[start_idx:])
        qqq_roll_max = qqq_series.cummax()
        qqq_drawdown = (qqq_series - qqq_roll_max) / qqq_roll_max * 100
        benchmark_max_dd = qqq_drawdown.min()
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'alpha': total_return - benchmark_return,
            'max_drawdown': max_dd,
            'benchmark_max_dd': benchmark_max_dd,
            'final_capital': final_value,
            'trades': len(trades),
            'modules_used': len(self.analyzers),
            'equity_curve': equity_curve
        }

    def _calculate_composite(self, signals: Dict) -> float:
        category_scores = {}
        for mod_name, score in signals.items():
            if isinstance(score, (int, float)) and 0 <= score <= 100:
                cat = self.MODULE_CATEGORIES.get(mod_name, 'other')
                if cat not in category_scores: category_scores[cat] = []
                category_scores[cat].append(score)
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
        scores = []
        current_price = prices[i]
        
        trend = 50
        if not np.isnan(sma20[i]) and not np.isnan(sma50[i]):
            if current_price > sma10[i] > sma20[i] > sma50[i]: trend = 90
            elif current_price > sma20[i] > sma50[i]: trend = 80
            elif current_price > sma50[i]: trend = 65
            elif current_price < sma20[i] < sma50[i]: trend = 25
            else: trend = 50
        scores.append(('trend', trend, 0.20))
        
        momentum = 50
        if not np.isnan(rsi[i]):
            if 45 < rsi[i] < 65: momentum = 70
            elif 30 < rsi[i] <= 45: momentum = 75
            elif rsi[i] <= 30: momentum = 80
            elif rsi[i] >= 70: momentum = 40
            else: momentum = 55
        if not np.isnan(macd[i]) and not np.isnan(macd_signal[i]):
            if macd[i] > macd_signal[i]: momentum += 5
            else: momentum -= 5
        scores.append(('momentum', np.clip(momentum, 0, 100), 0.15))
        
        volume = 50
        if not np.isnan(vol_sma[i]) and vol_sma[i] > 0:
            vol_ratio = volumes[i] / vol_sma[i]
            if vol_ratio > 1.5 and trend > 60: volume = 80
            elif vol_ratio > 1.0: volume = 60
            else: volume = 45
        scores.append(('volume', volume, 0.08))
        
        breakout = 50
        if i >= 20:
            high_20 = np.max(prices[i-20:i])
            low_20 = np.min(prices[i-20:i])
            if current_price > high_20: breakout = 85
            elif current_price < low_20: breakout = 20
        scores.append(('breakout', breakout, 0.10))
        
        vol_score = 50
        if not np.isnan(atr[i]) and current_price > 0:
            atr_pct = atr[i] / current_price * 100
            vol_score = 70 if atr_pct < 1.0 else (35 if atr_pct > 2.5 else 55)
        scores.append(('volatility', vol_score, 0.05))
        
        macro_keys = ['global_macro', 'yen_carry', 'geopolitical', 'oil', 'intermarket']
        macro = np.mean([signals.get(k, 50) for k in macro_keys if k in signals])
        scores.append(('global_macro', macro, 0.15))
        
        sentiment_keys = ['psychology', 'seasonality', 'news', 'options_flow']
        sentiment = np.mean([signals.get(k, 50) for k in sentiment_keys if k in signals])
        scores.append(('sentiment', sentiment, 0.10))
        
        ml_keys = ['ml_prediction', 'ai_confidence', 'alpha', 'regime']
        ml = np.mean([signals.get(k, 50) for k in ml_keys if k in signals])
        scores.append(('ml_ai', ml, 0.10))
        
        risk_keys = ['manipulation_risk', 'liquidity', 'stress', 'drawdown_risk']
        risk_scores = [100 - signals.get(k, 50) if 'risk' in k else signals.get(k, 50) for k in risk_keys if k in signals]
        risk = np.mean(risk_scores) if risk_scores else 50
        scores.append(('risk', risk, 0.07))
        
        return sum(s[1] * s[2] for s in scores)

    def _print_results(self, results: Dict):
        ret = results.get('total_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        print(f"Total Active Modules Used: {results.get('modules_used', 0)}")
        print(f"Strategy Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Benchmark (QQQ) Return:    {'+' if bench > 0 else ''}{bench:.2f}%")
        print(f"Alpha (Outperformance):    {'+' if alpha > 0 else ''}{alpha:.2f}%")
        print(f"Strategy Max Drawdown:     -{results.get('max_drawdown', 0):.2f}%")
        print(f"Benchmark Max Drawdown:    -{results.get('benchmark_max_dd', 0):.2f}%")
        print(f"Final Capital Value:       {results.get('final_capital', 0):,.0f} KRW")
        print(f"Portfolio Rebalances:      {results.get('trades', 0)}")
        
        if alpha > 0:
            print(f"\n🏆 BEAT QQQ BENCHMARK BY {alpha:.2f}%! 🏆")
        else:
            print(f"\n📊 Strategy: {ret:.2f}% | QQQ: {bench:.2f}%")

if __name__ == "__main__":
    bt = UltimateAllModulesBacktester()
    bt.run_backtest(period_days=365, aggressive=True)
