"""
Composite Signal Engine (Master Integrator)
=============================================
Combines ALL filters into a single trading decision.

This is the brain of the system - aggregates 50+ signals
into one actionable score.

Categories:
1. Macro (regime, VIX, Fed, economy)
2. Technical (trend, momentum, patterns)
3. Fundamental (earnings, insider, valuation)
4. Smart Money (flow, options, institutions)
5. Sentiment (social, news, fear/greed)
6. Risk (tail risk, position size, stops)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import pandas as pd
import numpy as np
import concurrent.futures

import data_proxy
from base_adapters import get_available_adapters

from loguru import logger


class ActionType(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    HOLD = "HOLD"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class CategoryScore:
    """Individual category score"""
    category: str
    score: int  # -100 to +100
    weight: float
    signals: List[str]


@dataclass
class CompositeSignal:
    """Master composite signal"""
    symbol: str
    timestamp: str
    
    # Final Decision
    action: ActionType
    confidence: int  # 0-100
    composite_score: int  # -100 to +100
    
    # Category Breakdown
    macro_score: CategoryScore
    technical_score: CategoryScore
    fundamental_score: CategoryScore
    smart_money_score: CategoryScore
    sentiment_score: CategoryScore
    risk_score: CategoryScore
    
    # Position Guidance
    position_size_pct: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    
    # Key Signals
    bullish_signals: List[str]
    bearish_signals: List[str]
    warnings: List[str]
    
    # Summary
    summary: str


class CompositeSignalEngine:
    """
    Master Signal Aggregator
    
    Weighting:
    - Macro: 15% (regime sets the stage)
    - Technical: 25% (timing)
    - Fundamental: 20% (quality)
    - Smart Money: 20% (follow the money)
    - Sentiment: 10% (contrarian)
    - Risk: 10% (protection)
    
    Decision Matrix:
    - Score > 60: STRONG_BUY
    - Score 40-60: BUY
    - Score 20-40: WEAK_BUY
    - Score -20 to 20: HOLD
    - Score -40 to -20: WEAK_SELL
    - Score -60 to -40: SELL
    - Score < -60: STRONG_SELL
    
    Confidence based on:
    - Category agreement
    - Signal strength
    - Historical accuracy
    """
    
    WEIGHTS = {
        'macro': 0.20,          # Increased from 0.10. Market trend is critical for swing.
        'technical': 0.35,      # Remains 0.35. Price action is king.
        'fundamental': 0.15,    # Increased from 0.10 for Earnings Surprises/PEAD.
        'smart_money': 0.20,    # Remains 0.20. Options flow & institutional buying.
        'sentiment': 0.10,      # Reduced from 0.15. Less noise, focus on real catalysts.
        'risk': 0.00            # Reduced to 0.00. Risk is handled by Position Sizer, not signal score.
    }
    
    def __init__(self):
        self._cache = {}  # {(analyzer_name, symbol): (result, timestamp)}
        self._import_analyzers()
    
    def _import_analyzers(self):
        """Auto-discover all analyzers adhering to BaseAnalyzer interface"""
        self.analyzers = {}
        self._cache = {} # Clear cache on reload
        
        # Load all adapter wrappers dynamically
        available_adapters = get_available_adapters()
        for adapter_class in available_adapters:
            try:
                adapter_instance = adapter_class()
                # Add checks to ensure the analyzer is not None and has the required attributes before access.
                if adapter_instance is None:
                    logger.warning(f"Skipping None adapter instance from {adapter_class.__name__}")
                    continue
                if not hasattr(adapter_instance, 'category') or not hasattr(adapter_instance, 'name') or not hasattr(adapter_instance, 'analyze'):
                    logger.warning(f"Skipping adapter {adapter_class.__name__} due to missing required attributes (category, name, or analyze method).")
                    continue

                # Group by category
                cat = adapter_instance.category.lower()
                if cat not in self.analyzers:
                    self.analyzers[cat] = []
                self.analyzers[cat].append(adapter_instance)
                logger.debug(f"Loaded analyzer: {adapter_instance.name} -> {cat}")
            except Exception as e:
                logger.warning(f"Failed to load analyzer {adapter_class.__name__}: {e}")
                
        logger.info(f"CompositeSignalEngine loaded advanced analyzers across {len(self.analyzers)} categories.")
    
    def _run_analyzers_async(self, category_key: str, df: pd.DataFrame, **kwargs) -> tuple[int, list]:
        """Runs all analyzers for a given category asynchronously with caching"""
        import time
        from datetime import datetime
        
        score = 0
        signals = []
        if category_key not in self.analyzers or not self.analyzers[category_key]:
            return score, signals

        symbol = kwargs.get('symbol', 'GLOBAL')
        now = time.time()
        
        # 30-minute cache for symbol-specific, 2-hour for macro/global
        CACHE_LONG = 7200  # 2 hours
        CACHE_SHORT = 1800 # 30 mins

        pending_analyzers = []
        for analyzer in self.analyzers[category_key]:
            # Defensive check for missing attributes in legacy/poorly implemented modules
            is_dep = getattr(analyzer, 'is_symbol_dependent', True)
            ana_name = getattr(analyzer, 'name', analyzer.__class__.__name__)
            
            cache_key = (ana_name, symbol if is_dep else 'GLOBAL')
            
            if cache_key in self._cache:
                cached_res, timestamp = self._cache[cache_key]
                expiry = CACHE_SHORT if is_dep else CACHE_LONG
                if now - timestamp < expiry:
                    score += cached_res.get('score', 0)
                    signals.extend(cached_res.get('signals', []))
                    continue
            
            pending_analyzers.append(analyzer)

        if not pending_analyzers:
            return score, signals
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_analyzer = {
                executor.submit(analyzer.analyze, df, **kwargs): analyzer 
                for analyzer in pending_analyzers
            }
            for future in concurrent.futures.as_completed(future_to_analyzer):
                analyzer = future_to_analyzer[future]
                try:
                    result = future.result(timeout=10.0) # Increased timeout for slow macro
                    
                    # Update cache
                    is_dep_inner = getattr(analyzer, 'is_symbol_dependent', True)
                    cache_key = (getattr(analyzer, 'name', analyzer.__class__.__name__), symbol if is_dep_inner else 'GLOBAL')
                    self._cache[cache_key] = (result, now)
                    
                    score += result.get('score', 0)
                    signals.extend(result.get('signals', []))
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Analyzer {analyzer.name} timed out.")
                except Exception as e:
                    logger.error(f"Analyzer {analyzer.name} raised {e}")
                    
        return score, signals
    
    def analyze(self, symbol: str, df: Optional[pd.DataFrame] = None, **kwargs) -> CompositeSignal:
        """Generate composite signal"""
        from datetime import datetime
        
        # Fetch basic data for calculations
        if df is None:
            df = self._fetch_data(symbol)
        
        if df is None or len(df) < 30:
            return self._unknown_result(symbol)
        
        close = df['Close']
        volume = df['Volume']
        current_price = float(close.iloc[-1])
        
        # Calculate category scores
        macro = self._calculate_macro_score(df, symbol, **kwargs)
        technical = self._calculate_technical_score(df, symbol, **kwargs)
        fundamental = self._calculate_fundamental_score(df, symbol, **kwargs)
        smart_money = self._calculate_smart_money_score(df, symbol, **kwargs)
        sentiment = self._calculate_sentiment_score(df, symbol, **kwargs)
        risk = self._calculate_risk_score(df, symbol, **kwargs)
        
        # Weighted composite
        composite = (
            macro.score * self.WEIGHTS['macro'] +
            technical.score * self.WEIGHTS['technical'] +
            fundamental.score * self.WEIGHTS['fundamental'] +
            smart_money.score * self.WEIGHTS['smart_money'] +
            sentiment.score * self.WEIGHTS['sentiment'] +
            risk.score * self.WEIGHTS['risk']
        )
        composite = int(max(-100, min(100, composite)))
        
        # Determine action (Aggressive Thresholds)
        if composite > 50:
            action = ActionType.STRONG_BUY
        elif composite > 25:
            action = ActionType.BUY
        elif composite > 10:
            action = ActionType.WEAK_BUY
        elif composite > -15:
            action = ActionType.HOLD
        elif composite > -30:
            action = ActionType.WEAK_SELL
        elif composite > -50:
            action = ActionType.SELL
        else:
            action = ActionType.STRONG_SELL
        
        # Calculate confidence
        scores = [macro.score, technical.score, fundamental.score, 
                  smart_money.score, sentiment.score, risk.score]
        
        # Agreement = low standard deviation
        score_std = np.std(scores)
        base_confidence = 70
        
        if score_std < 15:
            confidence = min(95, base_confidence + 25)
        elif score_std < 25:
            confidence = base_confidence
        elif score_std < 40:
            confidence = max(40, base_confidence - 20)
        else:
            confidence = max(30, base_confidence - 35)
        
        # Boost confidence if composite is extreme
        if abs(composite) > 50:
            confidence = min(95, confidence + 10)
        
        # Collect signals
        bullish = []
        bearish = []
        warnings = []
        
        for cat in [macro, technical, fundamental, smart_money, sentiment, risk]:
            for sig in cat.signals:
                if cat.score > 20:
                    bullish.append(f"{cat.category}: {sig}")
                elif cat.score < -20:
                    bearish.append(f"{cat.category}: {sig}")
        
        # Position sizing (Confidence-scaled dynamic sizing)
        import config
        # Target size per position based on max slots (e.g., 5 slots = 20% each)
        target_pct = 1.0 / max(1, config.MAX_POSITIONS)
        
        # Base size scales proportionally to the slot allocation
        if action in [ActionType.STRONG_BUY, ActionType.STRONG_SELL]:
            base_pct = target_pct        # Full 1x allocation
        elif action in [ActionType.BUY, ActionType.SELL]:
            base_pct = target_pct * 0.8  # 0.8x allocation
        elif action in [ActionType.WEAK_BUY, ActionType.WEAK_SELL]:
            base_pct = target_pct * 0.5  # 0.5x allocation
        else:
            base_pct = 0.0
        
        # Confidence scaling: mild adjustment (e.g., 60% conf -> 0.86x, 90% -> 1.04x)
        conf_mult = 0.5 + (confidence / 100.0) * 0.6
        position_pct = base_pct * conf_mult
        
        # Hard cap at user's max single position configuration (default 35%)
        position_pct = min(position_pct, config.MAX_POSITION_PCT)
        
        # Adjust for risk score
        if risk.score < -30:
            position_pct *= 0.5
            warnings.append("HIGH_RISK:Reducing size")
        
        # Calculate stops
        atr = self._calculate_atr(df)
        stop_loss = current_price - (2 * atr) if action.value.endswith('BUY') else current_price + (2 * atr)
        take_profit = current_price + (3 * atr) if action.value.endswith('BUY') else current_price - (3 * atr)
        risk_reward = 1.5
        
        # Summary
        summary = self._generate_summary(action, composite, confidence, 
                                         bullish[:3], bearish[:3], warnings)
        
        return CompositeSignal(
            symbol=symbol,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action=action,
            confidence=confidence,
            composite_score=composite,
            macro_score=macro,
            technical_score=technical,
            fundamental_score=fundamental,
            smart_money_score=smart_money,
            sentiment_score=sentiment,
            risk_score=risk,
            position_size_pct=position_pct,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            bullish_signals=bullish,
            bearish_signals=bearish,
            warnings=warnings,
            summary=summary
        )
    
    def _calculate_macro_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate macro environment score"""
        score = 20
        signals = []
        
        # Async run all MACRO modules (e.g. regime_detector, fed_watch)
        async_score, async_signals = self._run_analyzers_async('macro', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
            
        return CategoryScore("MACRO", min(100, max(-100, score)), self.WEIGHTS['macro'], signals)
    
    def _calculate_technical_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate technical score"""
        close = df['Close']
        signals = []
        score = 0
        
        # Async run all TECHNICAL modules (alpha, squeeze, candlestick, etc.)
        async_score, async_signals = self._run_analyzers_async('technical', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
        
        # Trend
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        current = close.iloc[-1]
        
        if current > sma20 > sma50:
            score += 30
            signals.append("UPTREND")
        elif current < sma20 < sma50:
            score -= 30
            signals.append("DOWNTREND")
        
        # RSI
        rsi = self._calculate_rsi(close)
        if rsi < 30:
            score += 25
            signals.append(f"RSI_OVERSOLD:{rsi:.0f}")
        elif rsi > 70:
            score -= 25
            signals.append(f"RSI_OVERBOUGHT:{rsi:.0f}")
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9).mean()
        
        if macd.iloc[-1] > macd_signal.iloc[-1] and macd.iloc[-2] <= macd_signal.iloc[-2]:
            score += 20
            signals.append("MACD_BULLISH_CROSS")
        elif macd.iloc[-1] < macd_signal.iloc[-1] and macd.iloc[-2] >= macd_signal.iloc[-2]:
            score -= 20
            signals.append("MACD_BEARISH_CROSS")
        
        # Overextension Penalty
        # Stocks >15% above SMA20 have a higher reversal risk
        dist_from_sma20 = (current - float(sma20)) / float(sma20)
        if dist_from_sma20 > 0.15:
            score -= 30
            signals.append(f"OVEREXTENDED:{dist_from_sma20:.1%}_vs_SMA20")
        elif dist_from_sma20 > 0.10:
            score -= 15
            signals.append(f"EXTENDED:{dist_from_sma20:.1%}_vs_SMA20")

        return CategoryScore("TECHNICAL", max(-100, min(100, score)),
                            self.WEIGHTS['technical'], signals)
    
    def _calculate_fundamental_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate fundamental score"""
        signals = []
        score = 0
        
        async_score, async_signals = self._run_analyzers_async('fundamental', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
        
        # Use price momentum as a proxy for earnings momentum
        ret_20d = (df['Close'].iloc[-1] / df['Close'].iloc[-20] - 1) * 100
        
        if ret_20d > 5:
            score += 20
            signals.append("POSITIVE_MOMENTUM")
        elif ret_20d < -5:
            score -= 20
            signals.append("NEGATIVE_MOMENTUM")
        
        # Short-term Surge Penalty
        # Fade parabolic moves, but allow strong momentum
        ret_5d = (df['Close'].iloc[-1] / df['Close'].iloc[-5] - 1) * 100 if len(df) >= 5 else 0
        if ret_5d > 20:
            score -= 25
            signals.append(f"PARABOLIC_5D:{ret_5d:.1f}%")
        elif ret_5d > 15:
            score -= 10
            signals.append(f"SURGE_5D:{ret_5d:.1f}%")

        return CategoryScore("FUNDAMENTAL", score,
                            self.WEIGHTS['fundamental'], signals)
    
    def _calculate_smart_money_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate smart money score"""
        signals = []
        score = 0
        
        # Async run all SMART_MONEY modules (options_flow, institutional, etc)
        async_score, async_signals = self._run_analyzers_async('smart_money', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
        
        # Volume analysis as proxy
        volume = df['Volume']
        close = df['Close']
        
        avg_vol = volume.tail(20).mean()
        recent_vol = volume.tail(5).mean()
        price_change = close.iloc[-1] / close.iloc[-5] - 1
        
        # Volume + price direction
        if recent_vol > avg_vol * 1.5 and price_change > 0:
            score += 25
            signals.append("SMART_ACCUMULATION")
        elif recent_vol > avg_vol * 1.5 and price_change < 0:
            score -= 25
            signals.append("DISTRIBUTION")
        
        return CategoryScore("SMART_MONEY", score, 
                            self.WEIGHTS['smart_money'], signals)
    
    def _calculate_sentiment_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate sentiment score"""
        signals = []
        score = 0
        
        async_score, async_signals = self._run_analyzers_async('sentiment', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
        
        # Use volatility as fear proxy
        returns = df['Close'].pct_change()
        vol = returns.tail(10).std() * np.sqrt(252) * 100
        
        if vol > 40:
            score += 20  # High fear = contrarian buy
            signals.append("FEAR_OPPORTUNITY")
        elif vol < 15:
            score -= 10  # Low vol = complacency
            signals.append("COMPLACENCY")
        
        return CategoryScore("SENTIMENT", score, 
                            self.WEIGHTS['sentiment'], signals)
    
    def _calculate_risk_score(self, df: pd.DataFrame, symbol: str, **kwargs) -> CategoryScore:
        """Calculate risk score"""
        signals = []
        score = 0
        
        async_score, async_signals = self._run_analyzers_async('risk', df, symbol=symbol, **kwargs)
        score += async_score
        signals.extend(async_signals)
        
        close = df['Close']
        returns = close.pct_change()
        
        # Calculate drawdown (distance from 50-day high)
        high_50d = float(close.tail(50).max())
        current_price = float(close.iloc[-1])
        drawdown = (current_price - high_50d) / high_50d if high_50d > 0 else 0
        
        # ?? Drawdown: reward healthy pullbacks, penalize near-highs ????????
        # Near all-time high = higher reversal risk for new entries
        # A 3-10% pullback from recent high = better risk/reward entry point
        if -0.10 <= drawdown <= -0.03:
            score += 25                    # Sweet spot: pulled back but still healthy
            signals.append("HEALTHY_PULLBACK")
        elif drawdown > -0.02:
            score -= 15                    # Within 2% of 50d high = chasing top
            signals.append("NEAR_50D_HIGH_RISK")
        elif drawdown < -0.20:
            score -= 30
            signals.append("HIGH_DRAWDOWN")
        
        # Volatility
        vol = returns.std() * np.sqrt(252)
        if vol < 0.25:
            score += 20
            signals.append("LOW_VOL")
        elif vol > 0.50:
            score -= 30
            signals.append("HIGH_VOL")
        
        return CategoryScore("RISK", score, self.WEIGHTS['risk'], signals)
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        high = df['High']
        low = df['Low']
        close = df['Close']
        
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': abs(high - close.shift()),
            'lc': abs(low - close.shift())
        }).max(axis=1)
        
        return float(tr.rolling(period).mean().iloc[-1])
    
    def _generate_summary(self, action: ActionType, score: int, confidence: int,
                         bullish: List[str], bearish: List[str], warnings: List[str]) -> str:
        """Generate human-readable summary"""
        emoji = {
            ActionType.STRONG_BUY: "\U0001F680",
            ActionType.BUY: "\U0001F7E2",
            ActionType.WEAK_BUY: "\U0001F4C8",
            ActionType.HOLD: "\u26AA",
            ActionType.WEAK_SELL: "\U0001F4C9",
            ActionType.SELL: "\U0001F534",
            ActionType.STRONG_SELL: "\U0001F4A5"
        }
        
        summary = f"{emoji.get(action, '')} {action.value} (Score: {score:+d}, Confidence: {confidence}%)\n"
        
        if bullish:
            summary += f"\U0001F4C8 Bullish: {', '.join(bullish[:3])}\n"
        if bearish:
            summary += f"\U0001F4C9 Bearish: {', '.join(bearish[:3])}\n"
        if warnings:
            summary += f"\u26A0 Warnings: {', '.join(warnings)}"
        
        return summary.strip()
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            import kis_data
            df = kis_data.download(symbol, period='90d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _unknown_result(self, symbol: str) -> CompositeSignal:
        """Unknown result"""
        from datetime import datetime
        return CompositeSignal(
            symbol=symbol, timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action=ActionType.HOLD, confidence=0, composite_score=0,
            macro_score=CategoryScore("MACRO", 0, 0.15, []),
            technical_score=CategoryScore("TECHNICAL", 0, 0.25, []),
            fundamental_score=CategoryScore("FUNDAMENTAL", 0, 0.20, []),
            smart_money_score=CategoryScore("SMART_MONEY", 0, 0.20, []),
            sentiment_score=CategoryScore("SENTIMENT", 0, 0.10, []),
            risk_score=CategoryScore("RISK", 0, 0.10, []),
            position_size_pct=0, entry_price=0, stop_loss=0, take_profit=0, risk_reward=0,
            bullish_signals=[], bearish_signals=[], warnings=["NO_DATA"],
            summary="Unable to analyze"
        )


# Global
_engine = None

def get_composite_engine() -> CompositeSignalEngine:
    global _engine
    if _engine is None:
        _engine = CompositeSignalEngine()
    return _engine


# ============================================================
# Convenience wrapper (used by strategy.py check_entry)
# ============================================================

# Per-symbol result cache: {symbol: (CompositeSignal, timestamp)}
_signal_result_cache: dict = {}
_SIGNAL_CACHE_TTL = 1800  # 30 minutes

def get_signal(symbol: str) -> CompositeSignal:
    """
    Return a cached CompositeSignal for `symbol`, refreshing only when
    the TTL has expired.  Avoids running all 70+ analyzers on every
    strategy.check_entry() call during a screener loop.
    """
    import time
    global _signal_result_cache
    now = time.time()
    cached = _signal_result_cache.get(symbol)
    if cached is not None:
        result, ts = cached
        if now - ts < _SIGNAL_CACHE_TTL:
            return result
    engine = get_composite_engine()
    result = engine.analyze(symbol)
    _signal_result_cache[symbol] = (result, now)
    return result


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing CompositeSignalEngine...")
    
    engine = CompositeSignalEngine()
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*70}")
        print(f"COMPOSITE ANALYSIS: {symbol}")
        print('='*70)
        
        result = engine.analyze(symbol)
        
        print(f"\n{result.summary}")
        print()
        print("Category Breakdown:")
        print(f"  ? Macro:       {result.macro_score.score:+4d} | {result.macro_score.signals}")
        print(f"  ? Technical:   {result.technical_score.score:+4d} | {result.technical_score.signals}")
        print(f"  ? Fundamental: {result.fundamental_score.score:+4d} | {result.fundamental_score.signals}")
        print(f"  ? Smart Money: {result.smart_money_score.score:+4d} | {result.smart_money_score.signals}")
        print(f"  ??Sentiment:   {result.sentiment_score.score:+4d} | {result.sentiment_score.signals}")
        print(f"  ? Risk:        {result.risk_score.score:+4d} | {result.risk_score.signals}")
        print()
        print(f"Position: {result.position_size_pct:.1%}")
        print(f"Entry: ${result.entry_price:.2f}")
        print(f"Stop: ${result.stop_loss:.2f}")
        print(f"Target: ${result.take_profit:.2f}")
        print(f"R/R: {result.risk_reward:.1f}")
