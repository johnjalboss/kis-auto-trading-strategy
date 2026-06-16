"""
Earnings Analyzer
==================
Track earnings surprises and estimate revisions.

Metrics:
1. Earnings Surprise %
2. Revenue Surprise %
3. Analyst Estimate Revisions
4. Guidance vs Consensus
5. EPS Growth Trend
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class EarningsData:
    """Earnings data"""
    eps_actual: float
    eps_estimate: float
    eps_surprise_pct: float
    
    revenue_actual: float
    revenue_estimate: float
    revenue_surprise_pct: float
    
    quarter: str  # "Q1 2024"
    report_date: Optional[datetime]


@dataclass
class EarningsSignal:
    """Earnings analysis result"""
    symbol: str
    
    # Last earnings
    last_eps_surprise: float
    last_revenue_surprise: float
    beat_streak: int  # Consecutive beats
    
    # Trends
    eps_growth_yoy: float
    revenue_growth_yoy: float
    
    # Estimate revisions
    eps_revision_30d: float  # % change in estimates
    revision_direction: str  # "UP", "DOWN", "STABLE"
    
    # Upcoming
    next_earnings_date: Optional[datetime]
    days_to_earnings: int
    
    # Scoring
    earnings_score: int  # -100 to +100
    signal: str
    details: List[str]
    days_since_earnings: int = 999  # Added for PEAD tracking


class EarningsAnalyzer:
    """
    Earnings Surprise & Revision Analysis
    
    Key Signals:
    1. Earnings beats → Post-earnings momentum
    2. Estimate revisions up → Analyst confidence
    3. Revenue + EPS beat → Strong fundamental
    4. Beat streak → Quality company
    
    Pre-Earnings Strategy:
    - Avoid buying 5 days before earnings
    - Look for estimate revisions as catalyst
    
    Scoring:
    - EPS beat >10%: +30
    - Revenue beat >5%: +20
    - Both beat: +15 bonus
    - Revisions up: +20
    - Revisions down: -25
    """
    
    def __init__(self):
        self._cache: Dict[str, EarningsSignal] = {}
    
    def analyze(self, symbol: str) -> EarningsSignal:
        """Analyze earnings for a symbol with cache protection"""
        if symbol in self._cache:
            return self._cache[symbol]
        details = []
        score = 0
        
        # Fetch data
        info = self._fetch_info(symbol)
        earnings_data = self._fetch_earnings(symbol)
        
        # Last earnings surprise
        last_eps_surprise = 0
        last_rev_surprise = 0
        beat_streak = 0
        
        if earnings_data:
            last = earnings_data[0] if earnings_data else None
            if last:
                last_eps_surprise = last.eps_surprise_pct
                last_rev_surprise = last.revenue_surprise_pct
                
                # Count beat streak
                for e in earnings_data:
                    if e.eps_surprise_pct > 0:
                        beat_streak += 1
                    else:
                        break
                
                # Score last earnings
                if last_eps_surprise >= 10:
                    score += 30
                    details.append(f"EPS_BEAT:{last_eps_surprise:+.1f}%")
                elif last_eps_surprise >= 5:
                    score += 20
                elif last_eps_surprise <= -10:
                    score -= 30
                    details.append(f"EPS_MISS:{last_eps_surprise:+.1f}%")
                elif last_eps_surprise <= -5:
                    score -= 20
                
                if last_rev_surprise >= 5:
                    score += 20
                    details.append(f"REV_BEAT:{last_rev_surprise:+.1f}%")
                elif last_rev_surprise <= -5:
                    score -= 20
                
                # Both beat bonus
                if last_eps_surprise > 0 and last_rev_surprise > 0:
                    score += 15
                    details.append("DOUBLE_BEAT")
                
                # Beat streak
                if beat_streak >= 4:
                    score += 20
                    details.append(f"BEAT_STREAK:{beat_streak}")
                elif beat_streak >= 2:
                    score += 10
        
        # Growth rates
        eps_growth = info.get('earningsGrowth', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0
        
        if eps_growth > 0.20:
            score += 20
            details.append(f"EPS_GROWTH:{eps_growth:.0%}")
        elif eps_growth < -0.10:
            score -= 15
        
        if rev_growth > 0.15:
            score += 15
            details.append(f"REV_GROWTH:{rev_growth:.0%}")
        elif rev_growth < -0.05:
            score -= 10
        
        # Estimate revisions (simplified)
        eps_revision = self._estimate_revision_trend(info)
        
        if eps_revision > 5:
            score += 20
            revision_dir = "UP"
            details.append(f"REVISIONS_UP:{eps_revision:+.1f}%")
        elif eps_revision < -5:
            score -= 25
            revision_dir = "DOWN"
            details.append(f"REVISIONS_DOWN:{eps_revision:+.1f}%")
        else:
            revision_dir = "STABLE"
        
        # Next earnings
        next_earnings, days_to = self._get_next_earnings(symbol)
        
        if days_to is not None and days_to <= 5:
            details.append(f"⚠️ EARNINGS_IN_{days_to}_DAYS")
        
        # Calculate days since last earnings report
        days_since = 999
        if earnings_data and len(earnings_data) > 0 and earnings_data[0].report_date:
            days_since = (datetime.now() - earnings_data[0].report_date).days
            
        # Signal
        if score >= 40:
            signal = "STRONG_FUNDAMENTALS"
        elif score >= 15:
            signal = "GOOD_FUNDAMENTALS"
        elif score <= -40:
            signal = "WEAK_FUNDAMENTALS"
        elif score <= -15:
            signal = "POOR_FUNDAMENTALS"
        else:
            signal = "NEUTRAL"
        
        result = EarningsSignal(
            symbol=symbol,
            last_eps_surprise=last_eps_surprise,
            last_revenue_surprise=last_rev_surprise,
            beat_streak=beat_streak,
            eps_growth_yoy=eps_growth,
            revenue_growth_yoy=rev_growth,
            eps_revision_30d=eps_revision,
            revision_direction=revision_dir,
            next_earnings_date=next_earnings,
            days_to_earnings=days_to or 999,
            earnings_score=max(-100, min(100, score)),
            signal=signal,
            details=details,
            days_since_earnings=days_since
        )
        self._cache[symbol] = result
        return result
    
    def _fetch_info(self, symbol: str) -> dict:
        """Fetch stock info via KIS API (proxy for yf.Ticker.info)"""
        try:
            import kis_data
            df = kis_data.download(symbol, period="1y", progress=False)
            if df is None or df.empty or len(df) < 60:
                return {}
            
            last_close = float(df['Close'].iloc[-1])
            close_90d_ago = float(df['Close'].iloc[-min(60, len(df))])
            close_1y_ago = float(df['Close'].iloc[0])
            
            # Calculate growth proxies from price data
            eps_growth_proxy = (last_close / close_1y_ago - 1) if close_1y_ago > 0 else 0
            rev_growth_proxy = eps_growth_proxy * 0.6  # Revenue grows slower than EPS
            
            return {
                'earningsGrowth': eps_growth_proxy,
                'revenueGrowth': rev_growth_proxy,
                'trailingPE': 0,
                'forwardPE': 0,
            }
        except Exception:
            return {}
    
    def _fetch_earnings(self, symbol: str) -> List[EarningsData]:
        """Fetch earnings history from Finnhub or yfinance"""
        # 1. Finnhub Fallback (Preempts yfinance)
        try:
            from finnhub_client import get_finnhub_client
            fh = get_finnhub_client()
            if fh.is_enabled():
                raw_earnings = fh.get_earnings_surprises(symbol)
                results = []
                for row in raw_earnings:
                    eps_act = float(row.get('actual', 0.0) or 0.0)
                    eps_est = float(row.get('estimate', 0.0) or 0.0)
                    eps_surp = float(row.get('surprisePercent', 0.0) or 0.0)
                    
                    rep_date = row.get('period', None)
                    if isinstance(rep_date, str):
                        try:
                            rep_date = datetime.strptime(rep_date, "%Y-%m-%d")
                        except:
                            rep_date = None
                            
                    results.append(EarningsData(
                        eps_actual=eps_act,
                        eps_estimate=eps_est,
                        eps_surprise_pct=eps_surp,
                        revenue_actual=0.0,
                        revenue_estimate=0.0,
                        revenue_surprise_pct=0.0,
                        quarter=f"Q{row.get('quarter', 1)} {row.get('year', 2026)}",
                        report_date=rep_date
                    ))
                if results:
                    logger.debug("Successfully fetched {} earnings surprises from Finnhub for {}", len(results), symbol)
                    return results
        except Exception as e:
            logger.error("Finnhub earnings surprises fetch failed for {}: {}", symbol, e)

        # 2. yfinance Fallback
        import os
        if os.getenv("DISABLE_YFINANCE_FALLBACK", "true").lower() == "true":
            return []
            
        try:
            import yfinance as yf
            ticker_class = getattr(yf, '_original_yf_Ticker', yf.Ticker)
            ticker = ticker_class(symbol)
            
            if hasattr(ticker, 'earnings_history'):
                hist = ticker.earnings_history
                if hist is not None and not hist.empty:
                    results = []
                    for idx, row in hist.iterrows():
                        eps_act = row.get('epsActual', 0.0)
                        eps_est = row.get('epsEstimate', 0.0)
                        eps_surp = row.get('surprisePercent', 0.0)
                        
                        eps_act = float(eps_act) if eps_act is not None else 0.0
                        eps_est = float(eps_est) if eps_est is not None else 0.0
                        eps_surp = float(eps_surp) if eps_surp is not None else 0.0
                        
                        if eps_surp == 0.0 and eps_est != 0.0:
                            eps_surp = ((eps_act - eps_est) / abs(eps_est)) * 100
                            
                        rev_act = row.get('revenueActual', 0.0)
                        rev_est = row.get('revenueEstimate', 0.0)
                        rev_surp = row.get('revenueSurprisePercent', 0.0)
                        
                        rev_act = float(rev_act) if rev_act is not None else 0.0
                        rev_est = float(rev_est) if rev_est is not None else 0.0
                        rev_surp = float(rev_surp) if rev_surp is not None else 0.0
                        
                        rep_date = row.get('reportDate', None)
                        if isinstance(rep_date, str):
                            try:
                                rep_date = datetime.strptime(rep_date[:10], "%Y-%m-%d")
                            except:
                                rep_date = None
                        
                        results.append(EarningsData(
                            eps_actual=eps_act,
                            eps_estimate=eps_est,
                            eps_surprise_pct=eps_surp,
                            revenue_actual=rev_act,
                            revenue_estimate=rev_est,
                            revenue_surprise_pct=rev_surp,
                            quarter=str(row.get('period', '')),
                            report_date=rep_date
                        ))
                    return results
        except Exception as e:
            logger.debug(f"Earnings history fetch failed for {symbol}: {e}")
        return []
    
    def _estimate_revision_trend(self, info: dict) -> float:
        """Estimate revision trend from price data"""
        forward_pe = info.get('forwardPE', 0) or 0
        trailing_pe = info.get('trailingPE', 0) or 0
        
        if forward_pe > 0 and trailing_pe > 0:
            revision_proxy = ((trailing_pe / forward_pe) - 1) * 100
            return max(-20, min(20, revision_proxy))
        
        # Use earnings growth as proxy
        eg = info.get('earningsGrowth', 0) or 0
        if eg > 0.2:
            return 10
        elif eg < -0.1:
            return -10
        return 0
    
    def _get_next_earnings(self, symbol: str) -> tuple:
        """Get next earnings date — delegated to earnings_calendar module"""
        try:
            from earnings_calendar import get_earnings_calendar
            ec = get_earnings_calendar()
            upcoming = ec.get_upcoming_earnings([symbol], days_ahead=30)
            
            if upcoming and symbol in [e.get('symbol') for e in upcoming]:
                for e in upcoming:
                    if e.get('symbol') == symbol:
                        next_date = e.get('date')
                        if next_date:
                            days_to = (next_date - datetime.now()).days
                            return next_date, max(0, days_to)
        except Exception:
            pass
        
        return None, None


# Global instance
_analyzer = None

def get_earnings_analyzer() -> EarningsAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = EarningsAnalyzer()
    return _analyzer


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing EarningsAnalyzer...")
    
    analyzer = EarningsAnalyzer()
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*50}")
        print(f"{symbol}")
        print('='*50)
        
        result = analyzer.analyze(symbol)
        
        print(f"Signal: {result.signal} ({result.earnings_score:+d})")
        print(f"Last EPS Surprise: {result.last_eps_surprise:+.1f}%")
        print(f"Beat Streak: {result.beat_streak}")
        print(f"EPS Growth YoY: {result.eps_growth_yoy:.1%}")
        print(f"Rev Growth YoY: {result.revenue_growth_yoy:.1%}")
        print(f"Revision Dir: {result.revision_direction}")
        print(f"Days to Earnings: {result.days_to_earnings}")
        print(f"Details: {result.details}")
