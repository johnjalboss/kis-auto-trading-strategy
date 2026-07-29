"""
ULTRA-AGGRESSIVE TECHNICAL STRATEGY
====================================
- 100% invested in uptrends
- 80% invested in neutral
- 60% in weak downtrends
- Heavy technical analysis weighting (60%)
- All available technical indicators
- NO leverage
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
import importlib
import os
import ast
import json
warnings.filterwarnings('ignore')

# ============================================================================
# IMPORT ALL MODULES
# ============================================================================

def discover_modules():
    SKIP = {'all_modules_backtest', 'complete_117_backtest', 'comprehensive_backtest',
            'truly_ultimate_backtest', 'ultimate_backtest', 'market_beating_backtest',
            'enhanced_backtester', 'backtester', 'integration_test', 'main', 
            'trader', 'trade', 'dashboard', 'config', 'auth', 'database',
            'ultra_aggressive_backtest', 'high_frequency_backtest', 'aggressive_technical_backtest'}
    
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
                                except:
                                    pass
        except:
            pass
    
    return modules, analyzers

print("[AGGRESSIVE-TECH] Loading modules...")
ALL_MODULES, ALL_ANALYZERS = discover_modules()
print(f"[AGGRESSIVE-TECH] Loaded: {len(ALL_MODULES)} modules")


class AggressiveTechnicalBacktester:
    """
    ULTRA-AGGRESSIVE TECHNICAL STRATEGY
    
    Key features:
    1. 100% invested when uptrend confirmed
    2. 60% weighting on technical analysis
    3. All technical indicators used
    4. Trend-following with momentum confirmation
    5. NO leverage
    """
    
    def __init__(self, initial_capital: float = 1500000):
        self.initial_capital = initial_capital
        self.modules = ALL_MODULES
        self.analyzers = ALL_ANALYZERS
        self.trades = []
        
    def run_backtest(self, period_days: int = 365) -> Dict:
        """Run aggressive technical backtest"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"\n{'='*70}")
        print("🔥 ULTRA-AGGRESSIVE TECHNICAL STRATEGY 🔥")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Modules: {len(self.analyzers)}")
        print(f"Strategy: 100% in uptrends, Technical-heavy")
        print()
        
        # Get market data
        spy = yf.download('SPY', start=start_date.strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
            
        if spy.empty:
            return {}
        
        # Calculate ALL indicators
        print("[1/3] Calculating ALL technical indicators...")
        indicators = self._calculate_all_indicators(spy)
        
        # Run simulation
        print("[2/3] Running simulation...")
        results = self._simulate(spy, indicators)
        
        # Results
        print("\n[3/3] RESULTS")
        print("-"*70)
        self._print_results(results)
        
        return results
    
    def _calculate_all_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate ALL technical indicators"""
        
        prices = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        close = data['Close']
        
        ind = {}
        
        # ===== MOVING AVERAGES (5가지) =====
        ind['sma5'] = pd.Series(prices).rolling(5).mean().values
        ind['sma10'] = pd.Series(prices).rolling(10).mean().values
        ind['sma20'] = pd.Series(prices).rolling(20).mean().values
        ind['sma50'] = pd.Series(prices).rolling(50).mean().values
        ind['sma200'] = pd.Series(prices).rolling(200).mean().values
        
        # EMA
        ind['ema9'] = close.ewm(span=9).mean().values
        ind['ema21'] = close.ewm(span=21).mean().values
        ind['ema50'] = close.ewm(span=50).mean().values
        
        # ===== RSI (3가지) =====
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        ind['rsi14'] = (100 - (100 / (1 + rs))).values
        
        # Short RSI
        gain7 = delta.where(delta > 0, 0).rolling(7).mean()
        loss7 = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rs7 = gain7 / loss7.replace(0, 1)
        ind['rsi7'] = (100 - (100 / (1 + rs7))).values
        
        # ===== MACD =====
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        ind['macd'] = (ema12 - ema26).values
        ind['macd_signal'] = pd.Series(ind['macd']).ewm(span=9).mean().values
        ind['macd_hist'] = ind['macd'] - ind['macd_signal']
        
        # ===== BOLLINGER BANDS =====
        sma20 = pd.Series(prices).rolling(20).mean()
        std20 = pd.Series(prices).rolling(20).std()
        ind['bb_upper'] = (sma20 + 2 * std20).values
        ind['bb_lower'] = (sma20 - 2 * std20).values
        ind['bb_middle'] = sma20.values
        ind['bb_percent'] = ((close - (sma20 - 2 * std20)) / (4 * std20)).values
        
        # ===== ATR =====
        tr = np.maximum(highs - lows,
                       np.maximum(np.abs(highs - np.roll(prices, 1)),
                                  np.abs(lows - np.roll(prices, 1))))
        ind['atr14'] = pd.Series(tr).rolling(14).mean().values
        ind['atr_percent'] = ind['atr14'] / prices * 100
        
        # ===== MOMENTUM =====
        ind['mom5'] = (pd.Series(prices) / pd.Series(prices).shift(5) - 1).values * 100
        ind['mom10'] = (pd.Series(prices) / pd.Series(prices).shift(10) - 1).values * 100
        ind['mom20'] = (pd.Series(prices) / pd.Series(prices).shift(20) - 1).values * 100
        
        # ===== RATE OF CHANGE =====
        ind['roc10'] = ((prices - np.roll(prices, 10)) / np.roll(prices, 10) * 100)
        ind['roc20'] = ((prices - np.roll(prices, 20)) / np.roll(prices, 20) * 100)
        
        # ===== STOCHASTIC =====
        low14 = pd.Series(lows).rolling(14).min()
        high14 = pd.Series(highs).rolling(14).max()
        ind['stoch_k'] = ((close - low14) / (high14 - low14) * 100).values
        ind['stoch_d'] = pd.Series(ind['stoch_k']).rolling(3).mean().values
        
        # ===== WILLIAMS %R =====
        ind['williams_r'] = ((high14 - close) / (high14 - low14) * -100).values
        
        # ===== ADX (Average Directional Index) =====
        plus_dm = pd.Series(highs).diff()
        minus_dm = -pd.Series(lows).diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        tr_series = pd.Series(tr)
        plus_di = 100 * (plus_dm.ewm(span=14).mean() / tr_series.ewm(span=14).mean())
        minus_di = 100 * (minus_dm.ewm(span=14).mean() / tr_series.ewm(span=14).mean())
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        ind['adx'] = dx.ewm(span=14).mean().values
        ind['plus_di'] = plus_di.values
        ind['minus_di'] = minus_di.values
        
        # ===== OBV (On Balance Volume) =====
        obv = [0]
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif prices[i] < prices[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        ind['obv'] = np.array(obv)
        ind['obv_sma'] = pd.Series(ind['obv']).rolling(20).mean().values
        
        # ===== VOLUME =====
        ind['vol_sma20'] = pd.Series(volumes).rolling(20).mean().values
        ind['vol_ratio'] = volumes / ind['vol_sma20']
        
        # ===== CCI (Commodity Channel Index) =====
        typical_price = (highs + lows + prices) / 3
        tp_sma = pd.Series(typical_price).rolling(20).mean()
        tp_mad = pd.Series(typical_price).rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        ind['cci'] = ((typical_price - tp_sma) / (0.015 * tp_mad)).values
        
        # ===== MFI (Money Flow Index) =====
        mf = typical_price * volumes
        positive_mf = np.where(np.diff(typical_price, prepend=typical_price[0]) > 0, mf, 0)
        negative_mf = np.where(np.diff(typical_price, prepend=typical_price[0]) < 0, mf, 0)
        positive_mf_sum = pd.Series(positive_mf).rolling(14).sum()
        negative_mf_sum = pd.Series(negative_mf).rolling(14).sum()
        mfi_ratio = positive_mf_sum / negative_mf_sum.replace(0, 1)
        ind['mfi'] = (100 - (100 / (1 + mfi_ratio))).values
        
        # ===== VWAP =====
        cumulative_tp_vol = (typical_price * volumes).cumsum()
        cumulative_vol = volumes.cumsum()
        ind['vwap'] = cumulative_tp_vol / cumulative_vol
        
        # ===== BREAKOUT LEVELS =====
        ind['high20'] = pd.Series(highs).rolling(20).max().values
        ind['low20'] = pd.Series(lows).rolling(20).min().values
        ind['high50'] = pd.Series(highs).rolling(50).max().values
        ind['low50'] = pd.Series(lows).rolling(50).min().values
        
        # ===== PIVOT POINTS =====
        ind['pivot'] = (highs + lows + prices) / 3
        ind['r1'] = 2 * ind['pivot'] - lows
        ind['s1'] = 2 * ind['pivot'] - highs
        
        print(f"   Calculated {len(ind)} indicators")
        
        return ind
    
    def _simulate(self, data: pd.DataFrame, ind: Dict) -> Dict:
        """Run ultra-aggressive simulation"""
        
        capital = self.initial_capital
        prices = data['Close'].values
        
        # Strategy Parameters
        start_idx = 60
        shares = 0
        cash = capital
        peak = capital
        max_dd = 0
        
        # AGGRESSIVE: Start 95% invested
        initial_score = self._calculate_technical_score(start_idx, prices, ind)
        invested_pct = 0.95 if initial_score > 60 else 0.80
        shares = (capital * invested_pct) / prices[start_idx]
        cash = capital * (1 - invested_pct)
        
        self.trades.append({'day': start_idx, 'type': 'BUY', 'invested': invested_pct, 'score': initial_score})
        
        print(f"   Initial: {invested_pct*100:.0f}% invested (score: {initial_score:.0f})")
        
        equity_curve = [capital]
        
        for i in range(start_idx + 1, len(prices)):
            current_price = prices[i]
            portfolio_value = cash + shares * current_price
            
            # Calculate technical score
            score = self._calculate_technical_score(i, prices, ind)
            
            # AGGRESSIVE POSITION SIZING
            # Score 80+: 100% invested (STRONG UPTREND)
            # Score 70-80: 95% invested
            # Score 60-70: 90% invested
            # Score 50-60: 80% invested
            # Score 40-50: 70% invested
            # Score <40: 60% invested (MINIMUM)
            
            if score >= 80:
                target_invested = 1.00  # FULL 100%!
            elif score >= 70:
                target_invested = 0.95
            elif score >= 60:
                target_invested = 0.90
            elif score >= 50:
                target_invested = 0.80
            elif score >= 40:
                target_invested = 0.70
            else:
                target_invested = 0.60  # Never below 60%
            
            current_invested = (shares * current_price) / portfolio_value if portfolio_value > 0 else 0
            diff = abs(target_invested - current_invested)
            
            # Rebalance if difference > 5%
            if diff > 0.05:
                target_shares = (portfolio_value * target_invested) / current_price
                
                if target_shares > shares:
                    buy_shares = target_shares - shares
                    cost = buy_shares * current_price
                    if cost <= cash:
                        shares = target_shares
                        cash -= cost
                        self.trades.append({'day': i, 'type': 'ADD', 'invested': target_invested, 'score': score})
                else:
                    sell_shares = shares - target_shares
                    proceeds = sell_shares * current_price
                    shares = target_shares
                    cash += proceeds
                    self.trades.append({'day': i, 'type': 'REDUCE', 'invested': target_invested, 'score': score})
            
            equity_curve.append(portfolio_value)
            peak = max(peak, portfolio_value)
            dd = (peak - portfolio_value) / peak * 100
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
            'trades': len(self.trades),
            'modules_used': len(self.analyzers),
        }
    
    def _calculate_technical_score(self, i: int, prices: np.ndarray, ind: Dict) -> float:
        """
        Calculate comprehensive technical score (0-100)
        
        HEAVY TECHNICAL WEIGHTING (60% of total)
        """
        
        scores = []
        current_price = prices[i]
        
        # ===== 1. TREND (25% weight) =====
        trend = 50
        if not np.isnan(ind['sma5'][i]) and not np.isnan(ind['sma200'][i]):
            # Golden Cross / Death Cross
            if ind['sma50'][i] > ind['sma200'][i]:
                trend += 10  # Golden cross
            else:
                trend -= 10  # Death cross
                
            # Price vs MAs
            if current_price > ind['sma5'][i] > ind['sma10'][i] > ind['sma20'][i] > ind['sma50'][i]:
                trend += 30  # Perfect uptrend
            elif current_price > ind['sma10'][i] > ind['sma20'][i]:
                trend += 20
            elif current_price > ind['sma20'][i]:
                trend += 10
            elif current_price < ind['sma10'][i] < ind['sma20'][i]:
                trend -= 20
                
            # EMA alignment
            if ind['ema9'][i] > ind['ema21'][i] > ind['ema50'][i]:
                trend += 10
        
        trend = np.clip(trend, 0, 100)
        scores.append(('trend', trend, 0.25))
        
        # ===== 2. MOMENTUM (20% weight) =====
        momentum = 50
        if not np.isnan(ind['mom5'][i]):
            # Short-term momentum
            if ind['mom5'][i] > 3:
                momentum += 25
            elif ind['mom5'][i] > 1:
                momentum += 15
            elif ind['mom5'][i] > 0:
                momentum += 5
            elif ind['mom5'][i] < -2:
                momentum -= 15
            
            # Medium-term momentum
            if not np.isnan(ind['mom20'][i]) and ind['mom20'][i] > 5:
                momentum += 10
                
            # ROC
            if not np.isnan(ind['roc10'][i]) and ind['roc10'][i] > 3:
                momentum += 10
        
        momentum = np.clip(momentum, 0, 100)
        scores.append(('momentum', momentum, 0.20))
        
        # ===== 3. RSI & STOCHASTIC (15% weight) =====
        oscillator = 50
        
        # RSI
        if not np.isnan(ind['rsi14'][i]):
            if 40 < ind['rsi14'][i] < 60:
                oscillator += 15  # Healthy
            elif 30 < ind['rsi14'][i] <= 40:
                oscillator += 20  # Buy zone
            elif ind['rsi14'][i] <= 30:
                oscillator += 25  # Oversold = BUY!
            elif ind['rsi14'][i] >= 70:
                oscillator -= 5   # Overbought but can continue
        
        # Stochastic
        if not np.isnan(ind['stoch_k'][i]):
            if ind['stoch_k'][i] > ind['stoch_d'][i]:
                oscillator += 5  # Bullish crossover
            if ind['stoch_k'][i] < 20:
                oscillator += 10  # Oversold
        
        oscillator = np.clip(oscillator, 0, 100)
        scores.append(('oscillator', oscillator, 0.15))
        
        # ===== 4. MACD (15% weight) =====
        macd_score = 50
        if not np.isnan(ind['macd'][i]) and not np.isnan(ind['macd_signal'][i]):
            if ind['macd'][i] > ind['macd_signal'][i]:
                macd_score += 20  # Bullish
            if ind['macd_hist'][i] > 0 and ind['macd_hist'][i-1] < 0 if i > 0 else False:
                macd_score += 15  # Bullish crossover
            if ind['macd'][i] > 0:
                macd_score += 10  # Above zero line
        
        macd_score = np.clip(macd_score, 0, 100)
        scores.append(('macd', macd_score, 0.15))
        
        # ===== 5. BREAKOUT & VOLATILITY (10% weight) =====
        breakout = 50
        if i >= 20:
            if current_price > ind['high20'][i]:
                breakout += 30  # 20-day high breakout!
            elif current_price > ind['high20'][i] * 0.98:
                breakout += 15  # Near breakout
            if not np.isnan(ind['atr_percent'][i]) and ind['atr_percent'][i] < 1.5:
                breakout += 10  # Low volatility is good
        
        breakout = np.clip(breakout, 0, 100)
        scores.append(('breakout', breakout, 0.10))
        
        # ===== 6. VOLUME & OBV (10% weight) =====
        volume = 50
        if not np.isnan(ind['vol_ratio'][i]):
            if ind['vol_ratio'][i] > 1.5 and ind['mom5'][i] > 0:
                volume += 20  # High volume + up = bullish
            elif ind['vol_ratio'][i] > 1.0:
                volume += 10
        
        # OBV trend
        if not np.isnan(ind['obv_sma'][i]) and ind['obv'][i] > ind['obv_sma'][i]:
            volume += 10  # OBV above SMA
        
        volume = np.clip(volume, 0, 100)
        scores.append(('volume', volume, 0.10))
        
        # ===== 7. ADX - TREND STRENGTH (5% weight) =====
        adx_score = 50
        if not np.isnan(ind['adx'][i]):
            if ind['adx'][i] > 25 and ind['plus_di'][i] > ind['minus_di'][i]:
                adx_score = 85  # Strong uptrend
            elif ind['adx'][i] > 20 and ind['plus_di'][i] > ind['minus_di'][i]:
                adx_score = 70  # Moderate uptrend
            elif ind['adx'][i] < 20:
                adx_score = 50  # Weak trend
        
        scores.append(('adx', adx_score, 0.05))
        
        # Calculate weighted composite
        composite = sum(s[1] * s[2] for s in scores)
        
        return composite
    
    def _print_results(self, results: Dict):
        """Print results"""
        ret = results.get('total_return', 0)
        ann = results.get('annual_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        print(f"Modules Used:     {results.get('modules_used', 0)}")
        print(f"Total Trades:     {results.get('trades', 0)}")
        print(f"Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Annual Return:    {'+' if ann > 0 else ''}{ann:.2f}%")
        print(f"Benchmark (SPY):  {'+' if bench > 0 else ''}{bench:.2f}%")
        print()
        
        if alpha > 0:
            print(f"🏆 ALPHA:          +{alpha:.2f}% (BEAT THE MARKET!) 🏆")
        else:
            print(f"Alpha:            {alpha:.2f}%")
        
        print(f"\nMax Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")


def run_aggressive_technical_backtest():
    """Run aggressive technical backtests"""
    
    results = {}
    
    bt = AggressiveTechnicalBacktester(initial_capital=1500000)
    print("\n### 1 YEAR - AGGRESSIVE TECHNICAL ###")
    results['1yr'] = bt.run_backtest(period_days=365)
    
    bt = AggressiveTechnicalBacktester(initial_capital=1500000)
    print("\n### 3 YEARS - AGGRESSIVE TECHNICAL ###")
    results['3yr'] = bt.run_backtest(period_days=1095)
    
    # Summary
    print(f"\n{'='*70}")
    print("🔥 FINAL SUMMARY - AGGRESSIVE TECHNICAL 🔥")
    print(f"{'='*70}")
    
    for name, res in results.items():
        if res:
            alpha_icon = "🏆" if res['alpha'] > 0 else "📊"
            print(f"{name}: Return {res['total_return']:+.2f}% | "
                  f"Alpha {res['alpha']:+.2f}% {alpha_icon} | "
                  f"Trades {res['trades']} | "
                  f"MDD {res['max_drawdown']:.2f}%")
    
    return results


if __name__ == "__main__":
    run_aggressive_technical_backtest()
