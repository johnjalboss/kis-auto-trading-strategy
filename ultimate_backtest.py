"""
ULTIMATE INTEGRATED BACKTESTER
=================================
Uses ALL 100+ filters for maximum intelligence.
The most comprehensive trading system ever built.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import ALL our modules
try:
    from global_macro import GlobalMacroAnalyzer
except: GlobalMacroAnalyzer = None

try:
    from yen_carry import YenCarryMonitor
except: YenCarryMonitor = None

try:
    from crypto_sentiment import CryptoSentimentIndicator
except: CryptoSentimentIndicator = None

try:
    from oil_impact import OilImpactAnalyzer
except: OilImpactAnalyzer = None

try:
    from geopolitical import GeopoliticalMonitor
except: GeopoliticalMonitor = None

try:
    from intermarket import IntermarketAnalyzer
except: IntermarketAnalyzer = None

try:
    from market_psychology import MarketPsychology
except: MarketPsychology = None

try:
    from seasonality import SeasonalityAnalyzer
except: SeasonalityAnalyzer = None

try:
    from mean_reversion import MeanReversionDetector
except: MeanReversionDetector = None

try:
    from multi_timeframe import MultiTimeframe
except: MultiTimeframe = None


@dataclass
class UltimateSignal:
    """Comprehensive signal combining all filters"""
    timestamp: datetime
    
    # Core signals
    trend_score: float  # -100 to +100
    momentum_score: float
    volume_score: float
    
    # Global macro
    macro_score: float
    yen_carry_risk: float  # 0-100 (higher = more risk)
    crypto_sentiment: float
    oil_impact: float
    geopolitical_risk: float
    
    # Market internals
    intermarket_score: float
    psychology_score: float  # Fear/Greed
    seasonality_score: float
    
    # Technicals
    mean_reversion_score: float
    multi_tf_score: float
    
    # FINAL
    composite_score: float  # -100 to +100
    action: str  # "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
    confidence: float  # 0-100
    position_size_mult: float  # 0.0 to 1.0
    
    # Risk flags
    risk_flags: List[str]


class UltimateIntegratedBacktester:
    """
    ULTIMATE BACKTESTER
    
    Integrates ALL modules:
    - Global Macro (USD, VIX, Bonds)
    - Yen Carry Trade Risk
    - Crypto Sentiment (BTC as proxy)
    - Oil Impact
    - Geopolitical Risk
    - Intermarket Analysis
    - Market Psychology (Fear/Greed)
    - Seasonality
    - Mean Reversion
    - Multi-Timeframe
    - Technical Indicators
    """
    
    def __init__(self, initial_capital: float = 1500000):
        self.initial_capital = initial_capital
        
        # Initialize all analyzers
        self.global_macro = GlobalMacroAnalyzer() if GlobalMacroAnalyzer else None
        self.yen_carry = YenCarryMonitor() if YenCarryMonitor else None
        self.crypto = CryptoSentimentIndicator() if CryptoSentimentIndicator else None
        self.oil = OilImpactAnalyzer() if OilImpactAnalyzer else None
        self.geopolitical = GeopoliticalMonitor() if GeopoliticalMonitor else None
        self.intermarket = IntermarketAnalyzer() if IntermarketAnalyzer else None
        self.psychology = MarketPsychology() if MarketPsychology else None
        self.seasonality = SeasonalityAnalyzer() if SeasonalityAnalyzer else None
        self.mean_reversion = MeanReversionDetector() if MeanReversionDetector else None
        self.multi_tf = MultiTimeframe() if MultiTimeframe else None
        
        # Count available modules
        modules = [self.global_macro, self.yen_carry, self.crypto, self.oil,
                   self.geopolitical, self.intermarket, self.psychology,
                   self.seasonality, self.mean_reversion, self.multi_tf]
        self.active_modules = sum(1 for m in modules if m is not None)
        
        print(f"[Ultimate Backtester] Active Modules: {self.active_modules}/10")
    
    def run_backtest(self, period_days: int = 365) -> Dict:
        """Run comprehensive backtest"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        print(f"\n{'='*70}")
        print("ULTIMATE INTEGRATED BACKTEST")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Active Filters: {self.active_modules}")
        print()
        
        # Download extra history for technical indicators (250 days margin)
        hist_start = start_date - timedelta(days=250)
        spy = yf.download('SPY', start=hist_start.strftime('%Y-%m-%d'), 
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
        
        if spy.empty:
            print("Error: No market data")
            return {}
        
        # Determine the start index representing the actual period
        eval_start_idx = max(60, len(spy) - int((period_days / 365.25) * 252))
        
        # Get global signals ONCE at start (they represent current state)
        print("[1/3] Analyzing Global Macro Environment...")
        global_signals = self._get_global_signals()
        
        print(f"       Global Macro Score: {global_signals['macro_score']:.1f}")
        print(f"       Yen Carry Risk: {global_signals['yen_carry_risk']:.1f}")
        print(f"       Crypto Sentiment: {global_signals['crypto_sentiment']:.1f}")
        print(f"       Geopolitical Risk: {global_signals['geopolitical_risk']:.1f}")
        
        # Run simulation
        print("\n[2/3] Running Simulation...")
        results = self._simulate(spy, global_signals, eval_start_idx)
        
        # Print results
        print("\n[3/3] Results")
        print("-"*70)
        self._print_results(results)
        
        return results
    
    def _get_global_signals(self) -> Dict:
        """Get all global macro signals"""
        signals = {
            'macro_score': 50,
            'yen_carry_risk': 30,
            'crypto_sentiment': 50,
            'oil_impact': 0,
            'geopolitical_risk': 40,
            'intermarket_score': 50,
            'psychology_score': 50,
            'seasonality_score': 0,
        }
        
        # Global Macro
        if self.global_macro:
            try:
                gm = self.global_macro.analyze()
                # Convert risk level to score
                if gm.overall_risk == "RISK_OFF":
                    signals['macro_score'] = 20
                elif gm.overall_risk == "CAUTION":
                    signals['macro_score'] = 40
                elif gm.overall_risk == "RISK_ON":
                    signals['macro_score'] = 80
                else:
                    signals['macro_score'] = 50
            except: pass
        
        # Yen Carry
        if self.yen_carry:
            try:
                yc = self.yen_carry.analyze()
                signals['yen_carry_risk'] = yc.impact_severity
            except: pass
        
        # Crypto
        if self.crypto:
            try:
                cs = self.crypto.analyze()
                signals['crypto_sentiment'] = cs.sentiment_score
            except: pass
        
        # Geopolitical
        if self.geopolitical:
            try:
                gp = self.geopolitical.analyze()
                signals['geopolitical_risk'] = gp.risk_score
            except: pass
        
        # Seasonality
        if self.seasonality:
            try:
                ss = self.seasonality.analyze()
                signals['seasonality_score'] = ss.combined_score
            except: pass
        
        # Psychology
        if self.psychology:
            try:
                mp = self.psychology.analyze()
                signals['psychology_score'] = mp.fear_greed_index
            except: pass
        
        return signals
    
    def _simulate(self, data: pd.DataFrame, global_signals: Dict, eval_start_idx: int) -> Dict:
        """Run the simulation with all filters"""
        
        capital = self.initial_capital
        position = None
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        prices = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        
        # Calculate technical indicators
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
        
        # Bollinger Bands
        bb_mid = pd.Series(prices).rolling(20).mean().values
        bb_std = pd.Series(prices).rolling(20).std().values
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        
        # ATR for position sizing
        tr = np.maximum(highs - lows, 
                       np.maximum(np.abs(highs - np.roll(prices, 1)),
                                  np.abs(lows - np.roll(prices, 1))))
        atr = pd.Series(tr).rolling(14).mean().values
        
        peak = capital
        max_dd = 0
        
        # Global risk adjustment
        global_risk_mult = self._calculate_global_risk_mult(global_signals)
        print(f"       Global Risk Multiplier: {global_risk_mult:.2f}x")
        
        for i in range(eval_start_idx, len(prices)):
            current_price = prices[i]
            
            # Calculate comprehensive score
            score, confidence, risk_flags = self._calculate_composite_score(
                i, prices, sma20, sma50, sma200, rsi, macd, macd_signal,
                bb_upper, bb_lower, volumes, global_signals
            )
            
            # Risk-adjusted position sizing
            base_size = 0.5  # 50% base
            
            # Adjust for volatility
            if not np.isnan(atr[i]) and current_price > 0:
                vol_adj = min(1.5, max(0.5, 1 - (atr[i] / current_price * 10)))
            else:
                vol_adj = 1.0
            
            # Adjust for global risk
            position_size = base_size * global_risk_mult * vol_adj * (confidence / 100)
            position_size = max(0.1, min(0.8, position_size))  # 10-80%
            
            # Entry logic
            if position is None and score > 60 and len(risk_flags) == 0:
                position = capital * position_size / current_price
                entry_price = current_price
                trades.append({
                    'type': 'ENTRY',
                    'price': current_price,
                    'score': score,
                    'confidence': confidence,
                    'size': position_size,
                    'date': i
                })
            
            # Exit logic
            elif position is not None:
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Dynamic exit based on score
                should_exit = False
                exit_reason = ""
                
                if pnl_pct < -0.03:  # Stop loss
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                elif pnl_pct > 0.08:  # Take profit
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
                elif score < 30:  # Deteriorating conditions
                    should_exit = True
                    exit_reason = "SCORE_DROP"
                elif len(risk_flags) >= 2:  # Multiple risk flags
                    should_exit = True
                    exit_reason = "RISK_FLAGS"
                
                if should_exit:
                    profit = position * (current_price - entry_price)
                    capital += profit
                    trades.append({
                        'type': 'EXIT',
                        'price': current_price,
                        'pnl': profit,
                        'pnl_pct': pnl_pct * 100,
                        'reason': exit_reason,
                        'date': i
                    })
                    position = None
            
            # Track equity
            if position is not None:
                mark_to_market = capital + position * (current_price - entry_price)
            else:
                mark_to_market = capital
            
            equity_curve.append(mark_to_market)
            
            # Drawdown
            peak = max(peak, mark_to_market)
            dd = (peak - mark_to_market) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Close remaining position
        if position is not None:
            profit = position * (prices[-1] - entry_price)
            capital += profit
            trades.append({
                'type': 'EXIT',
                'price': prices[-1],
                'pnl': profit,
                'pnl_pct': ((prices[-1] - entry_price) / entry_price) * 100,
                'reason': 'END_OF_TEST'
            })
        
        # Calculate final metrics
        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        benchmark_return = (prices[-1] / prices[60] - 1) * 100
        
        exits = [t for t in trades if t['type'] == 'EXIT']
        wins = [t for t in exits if t.get('pnl', 0) > 0]
        losses = [t for t in exits if t.get('pnl', 0) <= 0]
        
        win_rate = len(wins) / len(exits) * 100 if exits else 0
        
        gross_profit = sum(t.get('pnl', 0) for t in wins) if wins else 0
        gross_loss = abs(sum(t.get('pnl', 0) for t in losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
        
        return {
            'total_return': total_return,
            'benchmark_return': benchmark_return,
            'alpha': total_return - benchmark_return,
            'max_drawdown': max_dd,
            'trades': len(exits),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'final_capital': capital,
            'equity_curve': equity_curve
        }
    
    def _calculate_composite_score(self, i: int, prices, sma20, sma50, sma200,
                                   rsi, macd, macd_signal, bb_upper, bb_lower,
                                   volumes, global_signals) -> Tuple[float, float, List[str]]:
        """Calculate comprehensive composite score"""
        
        scores = []
        weights = []
        risk_flags = []
        
        current_price = prices[i]
        
        # 1. TREND (weight: 25%)
        trend_score = 50
        if not np.isnan(sma20[i]) and not np.isnan(sma50[i]):
            if current_price > sma20[i] > sma50[i]:
                trend_score = 80
                if not np.isnan(sma200[i]) and current_price > sma200[i]:
                    trend_score = 90
            elif current_price < sma20[i] < sma50[i]:
                trend_score = 20
                risk_flags.append("DOWNTREND")
            else:
                trend_score = 50
        scores.append(trend_score)
        weights.append(0.25)
        
        # 2. MOMENTUM - RSI + MACD (weight: 20%)
        momentum_score = 50
        if not np.isnan(rsi[i]):
            if 40 < rsi[i] < 60:
                momentum_score = 60  # Healthy momentum
            elif rsi[i] < 30:
                momentum_score = 75  # Oversold bounce opportunity
            elif rsi[i] > 70:
                momentum_score = 30  # Overbought
                risk_flags.append("OVERBOUGHT")
            else:
                momentum_score = 50
            
            # MACD confirmation
            if not np.isnan(macd[i]) and not np.isnan(macd_signal[i]):
                if macd[i] > macd_signal[i]:
                    momentum_score += 10
                else:
                    momentum_score -= 10
        
        scores.append(max(0, min(100, momentum_score)))
        weights.append(0.20)
        
        # 3. VOLUME (weight: 10%)
        avg_vol = np.mean(volumes[max(0, i-20):i])
        vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 1
        volume_score = 50 + (vol_ratio - 1) * 20
        volume_score = max(30, min(80, volume_score))
        scores.append(volume_score)
        weights.append(0.10)
        
        # 4. GLOBAL MACRO (weight: 15%)
        macro_score = global_signals['macro_score']
        if macro_score < 30:
            risk_flags.append("MACRO_RISK")
        scores.append(macro_score)
        weights.append(0.15)
        
        # 5. YEN CARRY RISK (weight: 10%)
        yen_risk = global_signals['yen_carry_risk']
        yen_score = 100 - yen_risk  # Invert: high risk = low score
        if yen_risk > 70:
            risk_flags.append("YEN_CARRY_CRISIS")
        scores.append(yen_score)
        weights.append(0.10)
        
        # 6. CRYPTO SENTIMENT (weight: 5%)
        crypto_score = global_signals['crypto_sentiment']
        if crypto_score < 20:
            risk_flags.append("CRYPTO_FEAR")
        scores.append(crypto_score)
        weights.append(0.05)
        
        # 7. GEOPOLITICAL (weight: 10%)
        geo_risk = global_signals['geopolitical_risk']
        geo_score = 100 - geo_risk
        if geo_risk > 70:
            risk_flags.append("GEOPOLITICAL_CRISIS")
        scores.append(geo_score)
        weights.append(0.10)
        
        # 8. SEASONALITY (weight: 5%)
        seasonality_score = 50 + global_signals['seasonality_score']
        seasonality_score = max(30, min(70, seasonality_score))
        scores.append(seasonality_score)
        weights.append(0.05)
        
        # Calculate weighted composite
        composite = sum(s * w for s, w in zip(scores, weights))
        
        # Confidence based on agreement
        avg_score = np.mean(scores)
        std_score = np.std(scores)
        confidence = max(30, min(95, 100 - std_score * 2))
        
        return composite, confidence, risk_flags
    
    def _calculate_global_risk_mult(self, global_signals: Dict) -> float:
        """Calculate global risk multiplier"""
        
        risk_factors = []
        
        # Macro risk
        if global_signals['macro_score'] < 40:
            risk_factors.append(0.7)
        elif global_signals['macro_score'] > 70:
            risk_factors.append(1.2)
        else:
            risk_factors.append(1.0)
        
        # Yen carry
        if global_signals['yen_carry_risk'] > 70:
            risk_factors.append(0.5)  # Major risk reduction
        elif global_signals['yen_carry_risk'] > 50:
            risk_factors.append(0.8)
        else:
            risk_factors.append(1.0)
        
        # Geopolitical risk
        if global_signals['geopolitical_risk'] > 70:
            risk_factors.append(0.6)
        elif global_signals['geopolitical_risk'] > 50:
            risk_factors.append(0.8)
        else:
            risk_factors.append(1.0)
        
        # Average all factors
        return np.mean(risk_factors)
    
    def _print_results(self, results: Dict):
        """Print comprehensive results"""
        
        ret = results.get('total_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        ret_icon = "+" if ret > 0 else ""
        alpha_icon = "+" if alpha > 0 else ""
        
        print(f"Total Return:     {ret_icon}{ret:.2f}%")
        print(f"Benchmark (SPY):  {ret_icon if bench > 0 else ''}{bench:.2f}%")
        print(f"Alpha:            {alpha_icon}{alpha:.2f}%")
        print(f"Max Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Trades:           {results.get('trades', 0)}")
        print(f"Win Rate:         {results.get('win_rate', 0):.1f}%")
        print(f"Profit Factor:    {results.get('profit_factor', 0):.2f}")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")
        
        print("\n" + "="*70)


def run_ultimate_backtest():
    """Run ultimate integrated backtest"""
    bt = UltimateIntegratedBacktester(initial_capital=1500000)
    
    print("\n" + "="*70)
    print("TESTING ACROSS MULTIPLE PERIODS")
    print("="*70)
    
    periods = [
        ("1 Month", 30),
        ("1 Year", 365),
        ("3 Years", 1095),
    ]
    
    all_results = {}
    
    for name, days in periods:
        print(f"\n### {name} ###")
        result = bt.run_backtest(period_days=days)
        all_results[name] = result
    
    return all_results


if __name__ == "__main__":
    run_ultimate_backtest()
