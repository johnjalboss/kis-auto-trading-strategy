"""
Fundamental Analyzer
======================
Analyze company fundamentals (EPS, PE, Revenue, etc.)
"""

from dataclasses import dataclass
from typing import Optional, List
import yfinance as yf
from loguru import logger


@dataclass
class FundamentalData:
    symbol: str
    
    # Valuation
    pe_ratio: float
    forward_pe: float
    peg_ratio: float
    price_to_book: float
    price_to_sales: float
    
    # Profitability
    eps: float
    eps_growth: float
    revenue_growth: float
    profit_margin: float
    roe: float
    
    # Health
    debt_to_equity: float
    current_ratio: float
    free_cash_flow: float
    
    # Score
    value_score: int  # 0-100
    quality_score: int
    growth_score: int
    overall_score: int
    
    recommendation: str  # "STRONG", "MODERATE", "WEAK", "AVOID"
    details: List[str]


class FundamentalAnalyzer:
    """
    Fundamental Analysis Engine
    
    Scores:
    1. Value (PE, PB, PS) - Low is better
    2. Quality (ROE, margins) - High is better
    3. Growth (EPS growth, Revenue growth) - High is better
    """
    
    def __init__(self):
        pass
    
    def analyze(self, symbol: str) -> FundamentalData:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Valuation
            pe = info.get('trailingPE', 0) or 0
            fwd_pe = info.get('forwardPE', 0) or 0
            peg = info.get('pegRatio', 0) or 0
            pb = info.get('priceToBook', 0) or 0
            ps = info.get('priceToSalesTrailing12Months', 0) or 0
            
            # Profitability
            eps = info.get('trailingEps', 0) or 0
            eps_growth = info.get('earningsGrowth', 0) or 0
            rev_growth = info.get('revenueGrowth', 0) or 0
            margin = info.get('profitMargins', 0) or 0
            roe = info.get('returnOnEquity', 0) or 0
            
            # Health
            de = info.get('debtToEquity', 0) or 0
            cr = info.get('currentRatio', 0) or 0
            fcf = info.get('freeCashflow', 0) or 0
            
            details = []
            
            # Value Score (lower PE = higher score)
            if pe > 0:
                if pe < 15:
                    value = 90
                    details.append("LOW_PE")
                elif pe < 25:
                    value = 70
                elif pe < 40:
                    value = 50
                else:
                    value = 30
                    details.append("HIGH_PE")
            else:
                value = 50
            
            # Quality Score
            quality = 50
            if roe > 0.20:
                quality += 20
                details.append("HIGH_ROE")
            if margin > 0.15:
                quality += 15
            if de < 100:
                quality += 15
            
            # Growth Score
            growth = 50
            if eps_growth > 0.20:
                growth += 25
                details.append("STRONG_EPS_GROWTH")
            elif eps_growth > 0.10:
                growth += 15
            elif eps_growth < 0:
                growth -= 20
                details.append("NEGATIVE_EPS_GROWTH")
            
            if rev_growth > 0.15:
                growth += 20
                details.append("STRONG_REVENUE")
            
            # Overall
            overall = int(value * 0.3 + quality * 0.35 + growth * 0.35)
            
            # Recommendation
            if overall >= 75:
                rec = "STRONG"
            elif overall >= 60:
                rec = "MODERATE"
            elif overall >= 45:
                rec = "WEAK"
            else:
                rec = "AVOID"
            
            return FundamentalData(
                symbol=symbol,
                pe_ratio=pe,
                forward_pe=fwd_pe,
                peg_ratio=peg,
                price_to_book=pb,
                price_to_sales=ps,
                eps=eps,
                eps_growth=eps_growth * 100,
                revenue_growth=rev_growth * 100,
                profit_margin=margin * 100,
                roe=roe * 100,
                debt_to_equity=de,
                current_ratio=cr,
                free_cash_flow=fcf,
                value_score=value,
                quality_score=min(100, quality),
                growth_score=min(100, growth),
                overall_score=overall,
                recommendation=rec,
                details=details
            )
            
        except Exception as e:
            logger.debug(f"Fundamental analysis failed for {symbol}: {e}")
            return self._empty(symbol)
    
    def _empty(self, symbol: str) -> FundamentalData:
        return FundamentalData(symbol, 0,0,0,0,0,0,0,0,0,0,0,0,0,50,50,50,50,"UNKNOWN",[])


def get_fundamental_analyzer() -> FundamentalAnalyzer:
    return FundamentalAnalyzer()


if __name__ == "__main__":
    print("Testing FundamentalAnalyzer...")
    fa = FundamentalAnalyzer()
    
    for sym in ["AAPL", "NVDA", "TSLA"]:
        f = fa.analyze(sym)
        print(f"\n{sym}:")
        print(f"  PE: {f.pe_ratio:.1f} | Fwd PE: {f.forward_pe:.1f}")
        print(f"  EPS: ${f.eps:.2f} | Growth: {f.eps_growth:+.1f}%")
        print(f"  ROE: {f.roe:.1f}% | Margin: {f.profit_margin:.1f}%")
        print(f"  Scores: Value={f.value_score} Quality={f.quality_score} Growth={f.growth_score}")
        print(f"  Overall: {f.overall_score} → {f.recommendation}")
        print(f"  Details: {f.details}")
