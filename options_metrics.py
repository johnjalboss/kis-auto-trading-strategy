"""
Options Metrics Module
======================
Max Pain, GEX (Gamma Exposure), Put/Call Ratio, and other options-based signals.

These metrics help understand:
1. Max Pain - Where market makers want price to expire
2. GEX - Gamma Exposure affects price stability
3. Put/Call Ratio - Sentiment indicator
4. Unusual Options Activity - Smart money signals
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger
import warnings
warnings.filterwarnings('ignore')


@dataclass
class OptionsMetrics:
    """Complete options metrics for a symbol"""
    symbol: str
    max_pain: float
    max_pain_distance: float  # Distance from current price (%)
    gex: float  # Gamma Exposure (simplified)
    gex_signal: str  # POSITIVE, NEGATIVE, NEUTRAL
    put_call_ratio: float
    put_call_signal: str  # BULLISH, BEARISH, NEUTRAL
    iv_rank: float  # Implied Volatility rank (0-100)
    unusual_activity: bool
    options_score: int  # 0-100 overall score
    timestamp: datetime


class OptionsAnalyzer:
    """
    Options-based analysis for trading signals
    
    Key Metrics:
    1. MAX PAIN - The strike price where options expiring worthless causes 
       maximum loss to option holders (and max profit to market makers)
       -> Price tends to gravitate toward max pain near expiration
       
    2. GEX (Gamma Exposure) - Net gamma of market makers
       -> Positive GEX = MM sell when price rises, buy when falls = stability
       -> Negative GEX = MM buy when price rises, sell when falls = volatility
       
    3. PUT/CALL RATIO - Sentiment indicator
       -> High (>1) = Bearish sentiment (contrarian bullish)
       -> Low (<0.7) = Bullish sentiment (contrarian bearish)
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        
    def analyze(self, symbol: str) -> Optional[OptionsMetrics]:
        """Get comprehensive options analysis"""
        
        try:
            # Check cache
            if symbol in self.cache:
                if datetime.now() < self.cache_expiry.get(symbol, datetime.min):
                    return self.cache[symbol]
            
            ticker = yf.Ticker(symbol)
            current_price = self._get_current_price(ticker)
            
            if current_price is None:
                return None
            
            # Get options chain
            expirations = ticker.options
            if not expirations:
                return self._default_metrics(symbol, current_price)
            
            # Use nearest expiration
            nearest_exp = expirations[0]
            
            try:
                chain = ticker.option_chain(nearest_exp)
                calls = chain.calls
                puts = chain.puts
            except:
                return self._default_metrics(symbol, current_price)
            
            # Calculate metrics
            max_pain = self._calculate_max_pain(calls, puts, current_price)
            max_pain_dist = (max_pain / current_price - 1) * 100 if max_pain else 0
            
            gex, gex_signal = self._calculate_gex(calls, puts, current_price)
            
            pcr, pcr_signal = self._calculate_put_call_ratio(calls, puts)
            
            iv_rank = self._calculate_iv_rank(ticker)
            
            unusual = self._detect_unusual_activity(calls, puts)
            
            # Calculate overall score
            score = self._calculate_options_score(
                max_pain_dist, gex_signal, pcr, iv_rank, unusual
            )
            
            result = OptionsMetrics(
                symbol=symbol,
                max_pain=max_pain,
                max_pain_distance=max_pain_dist,
                gex=gex,
                gex_signal=gex_signal,
                put_call_ratio=pcr,
                put_call_signal=pcr_signal,
                iv_rank=iv_rank,
                unusual_activity=unusual,
                options_score=score,
                timestamp=datetime.now()
            )
            
            # Cache for 5 minutes
            self.cache[symbol] = result
            self.cache_expiry[symbol] = datetime.now() + timedelta(minutes=5)
            
            return result
            
        except Exception as e:
            logger.debug(f"Options analysis failed for {symbol}: {e}")
            return self._default_metrics(symbol, 0)
    
    def _get_current_price(self, ticker) -> Optional[float]:
        """Get current stock price"""
        try:
            hist = ticker.history(period='1d')
            if not hist.empty:
                return hist['Close'].iloc[-1]
            info = ticker.info
            return info.get('regularMarketPrice') or info.get('currentPrice')
        except:
            return None
    
    def _calculate_max_pain(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                           current_price: float) -> float:
        """
        Calculate Max Pain strike
        
        Max Pain = Strike where total option holder loss is maximized
        """
        try:
            if calls.empty or puts.empty:
                return current_price
            
            strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
            
            min_pain = float('inf')
            max_pain_strike = current_price
            
            for strike in strikes:
                # Calculate total intrinsic value at this strike for all options
                call_pain = 0
                put_pain = 0
                
                # Call pain: sum of (strike - current_strike) * OI for ITM calls
                for _, row in calls.iterrows():
                    if strike > row['strike']:
                        call_pain += (strike - row['strike']) * row.get('openInterest', 0)
                
                # Put pain: sum of (current_strike - strike) * OI for ITM puts
                for _, row in puts.iterrows():
                    if strike < row['strike']:
                        put_pain += (row['strike'] - strike) * row.get('openInterest', 0)
                
                total_pain = call_pain + put_pain
                
                if total_pain < min_pain:
                    min_pain = total_pain
                    max_pain_strike = strike
            
            return max_pain_strike
            
        except Exception as e:
            logger.debug(f"Max pain calc error: {e}")
            return current_price
    
    def _calculate_gex(self, calls: pd.DataFrame, puts: pd.DataFrame, 
                       current_price: float) -> Tuple[float, str]:
        """
        Calculate simplified Gamma Exposure (GEX)
        
        GEX = Sum of (Gamma * OI * 100 * Price^2 / 1e9) for all options
        Calls contribute positive gamma, puts contribute negative gamma to MM
        
        Positive GEX = Market makers dampen moves (buy low, sell high)
        Negative GEX = Market makers amplify moves (buy high, sell low)
        """
        try:
            total_gex = 0
            
            # Call gamma (positive for MM when they're short calls)
            if not calls.empty and 'gamma' in calls.columns:
                for _, row in calls.iterrows():
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    # Positive gamma from calls (MM short calls)
                    total_gex += gamma * oi * 100 * current_price ** 2 / 1e9
            
            # Put gamma (negative for MM when they're short puts)
            if not puts.empty and 'gamma' in puts.columns:
                for _, row in puts.iterrows():
                    gamma = row.get('gamma', 0) or 0
                    oi = row.get('openInterest', 0) or 0
                    # Negative gamma from puts (MM short puts)
                    total_gex -= gamma * oi * 100 * current_price ** 2 / 1e9
            
            # Interpret GEX
            if total_gex > 1:
                signal = "POSITIVE"  # Stable, mean-reverting
            elif total_gex < -1:
                signal = "NEGATIVE"  # Volatile, trend-following
            else:
                signal = "NEUTRAL"
            
            return total_gex, signal
            
        except Exception as e:
            logger.debug(f"GEX calc error: {e}")
            return 0, "NEUTRAL"
    
    def _calculate_put_call_ratio(self, calls: pd.DataFrame, 
                                   puts: pd.DataFrame) -> Tuple[float, str]:
        """
        Calculate Put/Call ratio based on volume or OI
        
        PCR > 1.0 = Bearish sentiment (contrarian bullish)
        PCR < 0.7 = Bullish sentiment (contrarian bearish)
        PCR 0.7-1.0 = Neutral
        """
        try:
            call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
            put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0
            
            if call_volume > 0:
                pcr = put_volume / call_volume
            else:
                call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
                put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0
                pcr = put_oi / call_oi if call_oi > 0 else 1.0
            
            # Interpret (contrarian)
            if pcr > 1.0:
                signal = "BULLISH"  # High puts = crowd bearish = contrarian bullish
            elif pcr < 0.7:
                signal = "BEARISH"  # Low puts = crowd bullish = contrarian bearish
            else:
                signal = "NEUTRAL"
            
            return pcr, signal
            
        except Exception as e:
            logger.debug(f"PCR calc error: {e}")
            return 1.0, "NEUTRAL"
    
    def _calculate_iv_rank(self, ticker) -> float:
        """
        Calculate IV Rank (0-100)
        
        IV Rank = (Current IV - 52wk Low IV) / (52wk High IV - 52wk Low IV)
        
        High IV Rank (>70) = Options expensive, sell premium
        Low IV Rank (<30) = Options cheap, buy premium
        """
        try:
            hist = ticker.history(period='1y')
            if len(hist) < 20:
                return 50
            
            # Use historical volatility as proxy
            returns = np.log(hist['Close'] / hist['Close'].shift(1))
            rolling_vol = returns.rolling(20).std() * np.sqrt(252) * 100
            
            current_vol = rolling_vol.iloc[-1]
            vol_min = rolling_vol.min()
            vol_max = rolling_vol.max()
            
            if vol_max > vol_min:
                iv_rank = (current_vol - vol_min) / (vol_max - vol_min) * 100
            else:
                iv_rank = 50
            
            return min(100, max(0, iv_rank))
            
        except Exception as e:
            logger.debug(f"IV Rank calc error: {e}")
            return 50
    
    def _detect_unusual_activity(self, calls: pd.DataFrame, 
                                  puts: pd.DataFrame) -> bool:
        """
        Detect unusual options activity
        
        Signals:
        - Volume >> OI (new positions)
        - Large block trades
        - OTM options with high volume
        """
        try:
            # Check for volume > OI (unusual)
            unusual = False
            
            if not calls.empty and 'volume' in calls.columns and 'openInterest' in calls.columns:
                calls_unusual = (calls['volume'] > calls['openInterest'] * 5).any()
                unusual = unusual or calls_unusual
            
            if not puts.empty and 'volume' in puts.columns and 'openInterest' in puts.columns:
                puts_unusual = (puts['volume'] > puts['openInterest'] * 5).any()
                unusual = unusual or puts_unusual
            
            return unusual
            
        except:
            return False
    
    def _calculate_options_score(self, max_pain_dist: float, gex_signal: str,
                                  pcr: float, iv_rank: float, 
                                  unusual: bool) -> int:
        """
        Calculate overall options-based trading score (0-100)
        
        Higher score = More bullish options signals
        """
        score = 50  # Start neutral
        
        # Max Pain (20 pts)
        if abs(max_pain_dist) < 2:
            score += 10  # Price near max pain = stable
        elif max_pain_dist > 3:
            score += 15  # Price below max pain = bullish pull
        elif max_pain_dist < -3:
            score -= 10  # Price above max pain = bearish pull
        
        # GEX (20 pts)
        if gex_signal == "POSITIVE":
            score += 15  # Stable market
        elif gex_signal == "NEGATIVE":
            score -= 10  # Volatile market
        
        # Put/Call Ratio (contrarian, 20 pts)
        if pcr > 1.2:
            score += 15  # High puts = contrarian bullish
        elif pcr > 1.0:
            score += 8
        elif pcr < 0.6:
            score -= 10  # Low puts = contrarian bearish
        
        # IV Rank (10 pts)
        if iv_rank < 30:
            score += 5  # Cheap options
        elif iv_rank > 70:
            score -= 5  # Expensive options
        
        # Unusual Activity (10 pts)
        if unusual:
            score += 5  # Smart money signal
        
        return min(100, max(0, score))
    
    def _default_metrics(self, symbol: str, price: float) -> OptionsMetrics:
        """Return default metrics when data unavailable"""
        return OptionsMetrics(
            symbol=symbol,
            max_pain=price,
            max_pain_distance=0,
            gex=0,
            gex_signal="NEUTRAL",
            put_call_ratio=1.0,
            put_call_signal="NEUTRAL",
            iv_rank=50,
            unusual_activity=False,
            options_score=50,
            timestamp=datetime.now()
        )
    
    def get_market_gex(self, symbols: List[str] = None) -> Dict:
        """
        Get aggregate market GEX from major symbols
        
        High market GEX = Expect range-bound
        Low market GEX = Expect breakout moves
        """
        if symbols is None:
            symbols = ['SPY', 'QQQ', 'IWM']
        
        results = {}
        total_gex = 0
        
        for sym in symbols:
            metrics = self.analyze(sym)
            if metrics:
                results[sym] = {
                    'gex': metrics.gex,
                    'signal': metrics.gex_signal,
                    'max_pain': metrics.max_pain,
                    'pcr': metrics.put_call_ratio
                }
                total_gex += metrics.gex
        
        avg_gex = total_gex / len(symbols) if symbols else 0
        
        return {
            'individual': results,
            'aggregate_gex': avg_gex,
            'market_signal': "STABLE" if avg_gex > 0 else "VOLATILE"
        }


# Global instance
_options_analyzer = None

def get_options_analyzer():
    global _options_analyzer
    if _options_analyzer is None:
        _options_analyzer = OptionsAnalyzer()
    return _options_analyzer


if __name__ == "__main__":
    print("Testing Options Analyzer...")
    print()
    
    analyzer = OptionsAnalyzer()
    
    # Test individual symbols
    for sym in ['SPY', 'AAPL', 'TSLA', 'NVDA']:
        print(f"=== {sym} ===")
        metrics = analyzer.analyze(sym)
        if metrics:
            print(f"  Max Pain: ${metrics.max_pain:.2f} ({metrics.max_pain_distance:+.1f}% from price)")
            print(f"  GEX: {metrics.gex:.2f} ({metrics.gex_signal})")
            print(f"  Put/Call: {metrics.put_call_ratio:.2f} ({metrics.put_call_signal})")
            print(f"  IV Rank: {metrics.iv_rank:.0f}")
            print(f"  Unusual: {metrics.unusual_activity}")
            print(f"  Options Score: {metrics.options_score}/100")
        print()
    
    # Test market GEX
    print("=== Market GEX ===")
    market = analyzer.get_market_gex()
    print(f"  Aggregate GEX: {market['aggregate_gex']:.2f}")
    print(f"  Market Signal: {market['market_signal']}")
