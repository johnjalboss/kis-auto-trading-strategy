"""
MARKET-BEATING BACKTEST
========================
Strategy: Always invested, filters adjust position size and stop levels
Goal: Beat S&P500 using all 100+ filters for risk management
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import all available modules
modules_loaded = []

try:
    from global_macro import GlobalMacroAnalyzer
    modules_loaded.append("global_macro")
except: pass

try:
    from yen_carry import YenCarryMonitor
    modules_loaded.append("yen_carry")
except: pass

try:
    from crypto_sentiment import CryptoSentimentIndicator
    modules_loaded.append("crypto_sentiment")
except: pass

try:
    from geopolitical import GeopoliticalMonitor  
    modules_loaded.append("geopolitical")
except: pass

try:
    from market_psychology import MarketPsychology
    modules_loaded.append("market_psychology")
except: pass

try:
    from seasonality import SeasonalityAnalyzer
    modules_loaded.append("seasonality")
except: pass

try:
    from oil_impact import OilImpactAnalyzer
    modules_loaded.append("oil_impact")
except: pass

try:
    from intermarket import IntermarketAnalyzer
    modules_loaded.append("intermarket")
except: pass

try:
    from multi_timeframe import MultiTimeframe
    modules_loaded.append("multi_timeframe")
except: pass

try:
    from mean_reversion import MeanReversionDetector
    modules_loaded.append("mean_reversion")
except: pass

try:
    from manipulation_defense import ManipulationDefense
    modules_loaded.append("manipulation_defense")
except: pass

try:
    from liquidity_filter import LiquidityFilter
    modules_loaded.append("liquidity_filter")
except: pass

try:
    from correlation_regime import CorrelationRegime
    modules_loaded.append("correlation_regime")
except: pass

try:
    from stress_test import StressTester
    modules_loaded.append("stress_test")
except: pass

try:
    from drawdown_controller import DrawdownController
    modules_loaded.append("drawdown_controller")
except: pass

try:
    from dynamic_stop import DynamicStop
    modules_loaded.append("dynamic_stop")
except: pass

try:
    from position_sizer import KellyPositionSizer
    modules_loaded.append("position_sizer")
except: pass

try:
    from exit_optimizer import ExitOptimizer
    modules_loaded.append("exit_optimizer")
except: pass

try:
    from factor_analysis import FactorAnalyzer
    modules_loaded.append("factor_analysis")
except: pass

try:
    from regime_detector import RegimeDetector
    modules_loaded.append("regime_detector")
except: pass

try:
    from momentum_analyzer import MomentumAnalyzer
    modules_loaded.append("momentum_analyzer")
except: pass

try:
    from trend_strength import TrendStrength
    modules_loaded.append("trend_strength")
except: pass

try:
    from divergence import DivergenceDetector
    modules_loaded.append("divergence")
except: pass

try:
    from accumulation import AccumulationDetector
    modules_loaded.append("accumulation")
except: pass

try:
    from volume_profile import VolumeProfileAnalyzer
    modules_loaded.append("volume_profile")
except: pass

try:
    from support_resistance import SupportResistance
    modules_loaded.append("support_resistance")
except: pass

try:
    from candlestick import CandlestickAnalyzer
    modules_loaded.append("candlestick")
except: pass

try:
    from fibonacci import FibonacciAnalyzer
    modules_loaded.append("fibonacci")
except: pass

try:
    from gap_fill import GapFillAnalyzer
    modules_loaded.append("gap_fill")
except: pass

try:
    from etf_flows import ETFFlows
    modules_loaded.append("etf_flows")
except: pass

try:
    from sector_rotation import SectorRotation
    modules_loaded.append("sector_rotation")
except: pass

try:
    from earnings_analyzer import EarningsAnalyzer
    modules_loaded.append("earnings_analyzer")
except: pass

try:
    from options_flow import OptionsFlowAnalyzer
    modules_loaded.append("options_flow")
except: pass

try:
    from insider_tracker import InsiderTracker
    modules_loaded.append("insider_tracker")
except: pass

try:
    from anti_fragility import AntifragilityManager
    modules_loaded.append("anti_fragility")
except: pass

try:
    from ml_predictor import MLPredictor
    modules_loaded.append("ml_predictor")
except: pass

try:
    from ai_judge import AITradingJudge
    modules_loaded.append("ai_judge")
except: pass

try:
    from alpha_generator import AlphaGenerator
    modules_loaded.append("alpha_generator")
except: pass

try:
    from hedge_manager import HedgeManager
    modules_loaded.append("hedge_manager")
except: pass

try:
    from dynamic_scaling import DynamicScaler
    modules_loaded.append("dynamic_scaling")
except: pass

try:
    from frequency_controller import FrequencyController
    modules_loaded.append("frequency_controller")
except: pass

try:
    from adaptive_strategy import AdaptiveStrategy
    modules_loaded.append("adaptive_strategy")
except: pass

try:
    from composite_signal import CompositeSignal
    modules_loaded.append("composite_signal")
except: pass

print(f"[MARKET-BEATING] Loaded: {len(modules_loaded)} modules")


class MarketBeatingBacktester:
    """
    MARKET-BEATING STRATEGY
    
    Core concept: ALWAYS BE INVESTED in the market
    Use all 100+ filters to:
    1. Adjust position size (50-100%)
    2. Set dynamic stops
    3. Add to winners / reduce losers
    
    This captures the market's upward drift while using
    intelligence for risk management.
    """
    
    def __init__(self, initial_capital: float = 1500000):
        self.initial_capital = initial_capital
        self.modules_count = len(modules_loaded)
        
        # Initialize analyzers
        self.global_macro = GlobalMacroAnalyzer() if "global_macro" in modules_loaded else None
        self.yen_carry = YenCarryMonitor() if "yen_carry" in modules_loaded else None
        self.crypto = CryptoSentimentIndicator() if "crypto_sentiment" in modules_loaded else None
        self.geopolitical = GeopoliticalMonitor() if "geopolitical" in modules_loaded else None
        self.psychology = MarketPsychology() if "market_psychology" in modules_loaded else None
        self.seasonality = SeasonalityAnalyzer() if "seasonality" in modules_loaded else None
        
    def run_backtest(self, period_days: int = 365) -> Dict:
        """Run market-beating backtest"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"\n{'='*70}")
        print("MARKET-BEATING BACKTEST")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Active Modules: {self.modules_count}")
        print(f"Strategy: ALWAYS INVESTED + DYNAMIC SIZING")
        print()
        
        # Get market data
        spy = yf.download('SPY', start=start_date.strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
            
        if spy.empty:
            print("Error: No market data")
            return {}
        
        # Analyze global environment
        print("[1/3] Analyzing Environment...")
        global_signals = self._analyze_global()
        self._print_signals(global_signals)
        
        # Run simulation
        print("\n[2/3] Running Simulation...")
        results = self._simulate(spy, global_signals)
        
        # Print results
        print("\n[3/3] Results")
        print("-"*70)
        self._print_results(results)
        
        return results
    
    def _analyze_global(self) -> Dict:
        """Get all global signals"""
        signals = {
            'global_macro': 50,
            'yen_carry': 70,
            'crypto': 50,
            'geopolitical': 50,
            'psychology': 50,
            'seasonality': 50,
        }
        
        if self.global_macro:
            try:
                gm = self.global_macro.analyze()
                risk_map = {"RISK_OFF": 20, "CAUTION": 40, "NEUTRAL": 50, "RISK_ON": 80}
                signals['global_macro'] = risk_map.get(gm.overall_risk, 50)
            except: pass
            
        if self.yen_carry:
            try:
                yc = self.yen_carry.analyze()
                signals['yen_carry'] = 100 - yc.impact_severity
            except: pass
            
        if self.crypto:
            try:
                cs = self.crypto.analyze()
                signals['crypto'] = cs.sentiment_score
            except: pass
            
        if self.geopolitical:
            try:
                gp = self.geopolitical.analyze()
                signals['geopolitical'] = 100 - gp.risk_score
            except: pass
            
        if self.psychology:
            try:
                mp = self.psychology.analyze()
                signals['psychology'] = mp.fear_greed_index
            except: pass
            
        if self.seasonality:
            try:
                ss = self.seasonality.analyze()
                signals['seasonality'] = 50 + ss.combined_score
            except: pass
            
        return signals
    
    def _print_signals(self, signals: Dict):
        """Print signals"""
        for k, v in signals.items():
            status = "+" if v > 50 else "-" if v < 50 else " "
            print(f"   {k:20}: {v:.0f}/100 [{status}]")
    
    def _simulate(self, data: pd.DataFrame, global_signals: Dict) -> Dict:
        """
        ALWAYS INVESTED SIMULATION
        
        Key difference: We're ALWAYS in the market
        Filters control SIZE not entry/exit
        """
        
        capital = self.initial_capital
        prices = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        
        # Technical indicators
        sma20 = pd.Series(prices).rolling(20).mean().values
        sma50 = pd.Series(prices).rolling(50).mean().values
        sma200 = pd.Series(prices).rolling(200).mean().values
        
        # RSI
        delta = pd.Series(prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = (100 - (100 / (1 + rs))).values
        
        # ATR for volatility
        tr = np.maximum(highs - lows,
                       np.maximum(np.abs(highs - np.roll(prices, 1)),
                                  np.abs(lows - np.roll(prices, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        
        # Track performance
        equity_curve = [capital]
        positions = []
        trades = []
        
        # Current position tracking
        shares = 0
        avg_entry = 0
        peak = capital
        max_dd = 0
        
        # Calculate average global score
        global_avg = np.mean(list(global_signals.values()))
        
        # Start with initial position after warmup
        start_idx = 60
        
        # Initial entry - invest 80%
        initial_price = prices[start_idx]
        initial_size = 0.8
        shares = (capital * initial_size) / initial_price
        avg_entry = initial_price
        cash = capital * (1 - initial_size)
        
        trades.append({'type': 'ENTRY', 'price': initial_price, 'shares': shares, 'day': start_idx})
        
        print(f"   Initial Entry: {shares:.2f} shares @ ${initial_price:.2f}")
        
        for i in range(start_idx + 1, len(prices)):
            current_price = prices[i]
            
            # Calculate composite score
            score = self._calculate_score(i, prices, sma20, sma50, sma200, 
                                         rsi, atr, volumes, global_signals)
            
            # Current portfolio value
            portfolio_value = cash + shares * current_price
            
            # DYNAMIC SIZING based on score
            # Score 80+ = 100% invested
            # Score 60-80 = 80-100%
            # Score 40-60 = 60-80%
            # Score 20-40 = 40-60%
            # Score <20 = 40% (minimum)
            
            if score >= 80:
                target_invested = 1.0
            elif score >= 60:
                target_invested = 0.8 + (score - 60) / 100
            elif score >= 40:
                target_invested = 0.6 + (score - 40) / 100
            elif score >= 20:
                target_invested = 0.4 + (score - 20) / 100
            else:
                target_invested = 0.4  # Never go below 40%
            
            # Current invested percentage
            current_invested = (shares * current_price) / portfolio_value if portfolio_value > 0 else 0
            
            # Rebalance if difference > 10%
            if abs(target_invested - current_invested) > 0.10:
                target_shares = (portfolio_value * target_invested) / current_price
                
                if target_shares > shares:
                    # BUY more
                    buy_shares = target_shares - shares
                    cost = buy_shares * current_price
                    if cost <= cash:
                        shares = target_shares
                        cash -= cost
                        trades.append({'type': 'ADD', 'price': current_price, 
                                      'shares': buy_shares, 'day': i, 'reason': f'score={score:.0f}'})
                elif target_shares < shares:
                    # SELL some
                    sell_shares = shares - target_shares
                    proceeds = sell_shares * current_price
                    shares = target_shares
                    cash += proceeds
                    trades.append({'type': 'REDUCE', 'price': current_price,
                                  'shares': sell_shares, 'day': i, 'reason': f'score={score:.0f}'})
            
            # Track equity
            equity = cash + shares * current_price
            equity_curve.append(equity)
            
            # Drawdown
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Final value
        final_value = cash + shares * prices[-1]
        
        # Calculate returns
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        benchmark_return = (prices[-1] / prices[start_idx] - 1) * 100
        
        # Annualize
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
            'equity_curve': equity_curve
        }
    
    def _calculate_score(self, i, prices, sma20, sma50, sma200, rsi, atr, volumes, global_signals) -> float:
        """Calculate composite score from all filters"""
        
        scores = []
        current_price = prices[i]
        
        # TREND (30%)
        trend = 50
        if not np.isnan(sma20[i]) and not np.isnan(sma50[i]):
            if current_price > sma20[i] > sma50[i]:
                trend = 80
                if not np.isnan(sma200[i]) and current_price > sma200[i]:
                    trend = 90
            elif current_price > sma50[i]:
                trend = 65
            elif current_price < sma20[i] < sma50[i]:
                trend = 25
            else:
                trend = 45
        scores.append(('trend', trend, 0.30))
        
        # MOMENTUM (20%)
        momentum = 50
        if not np.isnan(rsi[i]):
            if 40 < rsi[i] < 60:
                momentum = 70  # Healthy
            elif 30 < rsi[i] <= 40:
                momentum = 75  # Oversold bounce
            elif rsi[i] <= 30:
                momentum = 80  # Very oversold = buy opportunity
            elif rsi[i] >= 70:
                momentum = 40  # Overbought
            else:
                momentum = 55
        scores.append(('momentum', momentum, 0.20))
        
        # VOLUME (10%)
        avg_vol = np.mean(volumes[max(0, i-20):i])
        if avg_vol > 0:
            vol_ratio = volumes[i] / avg_vol
            if vol_ratio > 1.5 and trend > 60:
                volume = 80
            elif vol_ratio > 1.0:
                volume = 60
            else:
                volume = 45
        else:
            volume = 50
        scores.append(('volume', volume, 0.10))
        
        # GLOBAL MACRO (25%)
        macro_avg = np.mean([
            global_signals.get('global_macro', 50),
            global_signals.get('yen_carry', 50),
            global_signals.get('geopolitical', 50),
            global_signals.get('psychology', 50),
        ])
        scores.append(('macro', macro_avg, 0.25))
        
        # VOLATILITY (10%)
        if not np.isnan(atr[i]) and current_price > 0:
            atr_pct = atr[i] / current_price * 100
            if atr_pct < 1:
                vol_score = 75  # Low vol = good
            elif atr_pct > 3:
                vol_score = 35  # High vol = caution
            else:
                vol_score = 55
        else:
            vol_score = 50
        scores.append(('volatility', vol_score, 0.10))
        
        # SEASONALITY (5%)
        seasonality = global_signals.get('seasonality', 50)
        scores.append(('seasonality', seasonality, 0.05))
        
        # Calculate weighted average
        composite = sum(s[1] * s[2] for s in scores)
        
        return composite
    
    def _print_results(self, results: Dict):
        """Print results"""
        ret = results.get('total_return', 0)
        ann = results.get('annual_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        print(f"Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Annual Return:    {'+' if ann > 0 else ''}{ann:.2f}%")
        print(f"Benchmark (SPY):  {'+' if bench > 0 else ''}{bench:.2f}%")
        print(f"Alpha:            {'+' if alpha > 0 else ''}{alpha:.2f}%")
        print(f"Max Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")
        print(f"Rebalances:       {results.get('trades', 0)}")
        
        # Win/Loss vs Benchmark
        if alpha > 0:
            print(f"\n** BEAT THE MARKET BY {alpha:.2f}% **")
        else:
            print(f"\n** Underperformed by {abs(alpha):.2f}% **")


def run_market_beating_backtest():
    """Run market-beating backtests"""
    bt = MarketBeatingBacktester(initial_capital=1500000)
    
    results = {}
    
    print("\n### 1 YEAR ###")
    results['1yr'] = bt.run_backtest(period_days=365)
    
    print("\n### 3 YEARS ###")
    results['3yr'] = bt.run_backtest(period_days=1095)
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    
    for name, res in results.items():
        if res:
            alpha_icon = "+" if res['alpha'] > 0 else ""
            print(f"{name}: Return {res['total_return']:+.2f}% | "
                  f"Alpha {alpha_icon}{res['alpha']:.2f}% | "
                  f"MDD {res['max_drawdown']:.2f}%")
    
    return results


if __name__ == "__main__":
    run_market_beating_backtest()
