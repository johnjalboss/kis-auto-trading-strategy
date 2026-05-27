"""
Geopolitical Risk Monitor
============================
Track geopolitical events affecting markets.
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class GeopoliticalRisk:
    region: str
    event_type: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    market_impact: str
    sectors_affected: List[str]


@dataclass
class GeopoliticalAnalysis:
    overall_risk_level: str  # "LOW", "ELEVATED", "HIGH", "EXTREME"
    risk_score: int  # 0-100
    
    active_risks: List[GeopoliticalRisk]
    
    # Trading implications
    reduce_exposure: bool
    hedge_recommended: bool
    safe_havens: List[str]
    vulnerable_sectors: List[str]
    
    recommendation: str

    @property
    def score(self) -> int:
        """
        Normalize Geopolitical risk_score into a trading score.
        Risk is inversely proportional to stock bullishness:
        - EXTREME risk (-80)
        - HIGH risk (-50)
        - ELEVATED risk (-20)
        - LOW risk (+15)
        """
        if self.overall_risk_level == "EXTREME":
            return -80
        elif self.overall_risk_level == "HIGH":
            return -50
        elif self.overall_risk_level == "ELEVATED":
            return -20
        else:
            return 15



class GeopoliticalMonitor:
    """
    Geopolitical Risk Monitoring
    
    Key Risks:
    1. US-China Tensions (trade, tech)
    2. Middle East (oil supply)
    3. Taiwan Situation
    4. Russia-Ukraine
    5. North Korea
    6. European Politics
    7. US Elections/Policy
    
    Market Impact:
    - Defense stocks ↑ during tensions
    - Oil spikes during ME conflicts
    - Tech suffers on China tensions
    - Gold/bonds rise on uncertainty
    """
    
    # Known risk factors (simplified - in production fetch from news API)
    RISK_FACTORS = {
        'US_CHINA': {
            'regions': ['China', 'Taiwan', 'US'],
            'sectors': ['XLK', 'SOXX', 'FXI'],
            'description': 'US-China tech/trade tensions',
            'safe_havens': ['GLD', 'TLT']
        },
        'MIDDLE_EAST': {
            'regions': ['Iran', 'Israel', 'Saudi Arabia'],
            'sectors': ['XLE', 'USO', 'JETS'],
            'description': 'Middle East conflict risk',
            'safe_havens': ['XLE', 'GLD']
        },
        'RUSSIA_UKRAINE': {
            'regions': ['Russia', 'Ukraine', 'Europe'],
            'sectors': ['EWG', 'VGK', 'WEAT'],
            'description': 'Russia-Ukraine war',
            'safe_havens': ['GLD', 'DBA']
        },
        'TAIWAN': {
            'regions': ['Taiwan', 'China'],
            'sectors': ['SOXX', 'TSM', 'XLK'],
            'description': 'Taiwan strait tensions',
            'safe_havens': ['GLD', 'TLT', 'XLU']
        },
        'NORTH_KOREA': {
            'regions': ['North Korea', 'South Korea', 'Japan'],
            'sectors': ['EWY', 'EWJ', 'ITA'],
            'description': 'North Korea nuclear risk',
            'safe_havens': ['GLD', 'ITA']
        }
    }
    
    def __init__(self):
        self.active_risks: List[GeopoliticalRisk] = []
    
    def analyze(self) -> GeopoliticalAnalysis:
        """Analyze current geopolitical risks"""
        
        import yfinance as yf
        import traceback
        
        risk_score = 10  # Base level
        active_risks = []
        all_sectors = []
        all_havens = []
        
        try:
            # 1. Real Mathematical Proxy for Geopolitical Risk
            # We use Defense (ITA), Gold (GLD), and Oil (USO) vs SPY to measure global tension
            tickers = yf.download(['ITA', 'GLD', 'USO', 'SPY'], period='5d', progress=False)['Close']
            
            # Calculate 3-day momentum
            if len(tickers) >= 4:
                mom_ita = (tickers['ITA'].iloc[-1] / tickers['ITA'].iloc[-4]) - 1
                mom_gld = (tickers['GLD'].iloc[-1] / tickers['GLD'].iloc[-4]) - 1
                mom_uso = (tickers['USO'].iloc[-1] / tickers['USO'].iloc[-4]) - 1
                mom_spy = (tickers['SPY'].iloc[-1] / tickers['SPY'].iloc[-4]) - 1
                
                # Rule 1: War/Tension Proxy (Defense & Oil spike, Market drops)
                if mom_ita > 0.02 and mom_uso > 0.03 and mom_spy < 0:
                    risk_score += 40
                    active_risks.append(GeopoliticalRisk(
                        region="Global", event_type="CONFLICT_ESCALATION", severity="HIGH",
                        description="Defense & Oil surging against market drop (Proxy)",
                        market_impact="High Volatility", sectors_affected=['XLE', 'ITA']
                    ))
                    all_sectors.extend(['XLE', 'ITA'])
                    all_havens.extend(['GLD', 'TLT'])
                
                # Rule 2: Safe Haven Flight (Gold spikes, Market drops)
                if mom_gld > 0.02 and mom_spy < -0.01:
                    risk_score += 30
                    active_risks.append(GeopoliticalRisk(
                        region="Global", event_type="FLIGHT_TO_SAFETY", severity="MEDIUM",
                        description="Sudden flight to gold (Proxy)",
                        market_impact="Risk-Off", sectors_affected=['XLP', 'XLU']
                    ))
                    all_havens.extend(['GLD', 'TLT', 'CHF'])
                    
                # Rule 3: Energy Shock
                if mom_uso > 0.05:
                    risk_score += 20
                    active_risks.append(GeopoliticalRisk(
                        region="Middle East / Russia", event_type="ENERGY_SHOCK", severity="MEDIUM",
                        description="Oil price shock detected (Proxy)",
                        market_impact="Inflation Fear", sectors_affected=['XLE', 'XLY']
                    ))
                    
        except Exception as e:
            logger.debug(f"Geopolitical proxy calculation failed: {e}")
            risk_score = 10 # Fallback
            
        # Determine overall level
        if risk_score >= 80:
            level = "EXTREME"
            reduce = True
            hedge = True
        elif risk_score >= 60:
            level = "HIGH"
            reduce = True
            hedge = True
        elif risk_score >= 40:
            level = "ELEVATED"
            reduce = False
            hedge = True
        else:
            level = "LOW"
            reduce = False
            hedge = False
        
        # Unique lists
        unique_sectors = list(set(all_sectors))
        unique_havens = list(set(all_havens))
        
        # Recommendation
        if level == "EXTREME":
            rec = "[CRITICAL] EXTREME RISK: Maximum defense, reduce all positions"
        elif level == "HIGH":
            rec = "[WARNING] HIGH RISK: Reduce exposure, hedge with gold"
        elif level == "ELEVATED":
            rec = "[CAUTION] ELEVATED: Monitor closely, consider hedges"
        else:
            rec = "[OK] LOW: Normal trading, no major geopolitical concerns"
        
        return GeopoliticalAnalysis(
            overall_risk_level=level,
            risk_score=risk_score,
            active_risks=active_risks,
            reduce_exposure=reduce,
            hedge_recommended=hedge,
            safe_havens=unique_havens,
            vulnerable_sectors=unique_sectors,
            recommendation=rec
        )
    
    def check_specific_risk(self, risk_type: str) -> bool:
        """Check if specific risk is elevated"""
        return risk_type in self.RISK_FACTORS


def get_geopolitical() -> GeopoliticalMonitor:
    return GeopoliticalMonitor()


if __name__ == "__main__":
    print("Testing GeopoliticalMonitor...")
    gp = GeopoliticalMonitor()
    
    analysis = gp.analyze()
    
    print(f"\n{'='*60}")
    print("GEOPOLITICAL RISK ANALYSIS")
    print('='*60)
    print(f"Overall Level: {analysis.overall_risk_level} (Score: {analysis.risk_score})")
    print(f"\nActive Risks ({len(analysis.active_risks)}):")
    for r in analysis.active_risks:
        print(f"  • {r.region}: {r.description} ({r.severity})")
    print(f"\nReduce Exposure: {analysis.reduce_exposure}")
    print(f"Hedge Recommended: {analysis.hedge_recommended}")
    print(f"Safe Havens: {analysis.safe_havens}")
    print(f"Vulnerable: {analysis.vulnerable_sectors}")
    print(f"\nRecommendation: {analysis.recommendation}")
