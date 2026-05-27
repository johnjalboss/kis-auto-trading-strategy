"""
Yen Carry Trade Monitor
==========================
Monitor yen carry trade unwinding risk.
"""

from dataclasses import dataclass
import pandas as pd
import yfinance as yf
from loguru import logger


@dataclass
class YenCarrySignal:
    usdjpy: float
    usdjpy_change_5d: float
    
    # Yen strength
    yen_trend: str  # "STRENGTHENING", "WEAKENING", "STABLE"
    yen_momentum: float
    
    # Carry trade status
    carry_status: str  # "BUILDING", "STABLE", "UNWINDING", "CRISIS"
    unwind_risk: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    # Market impact
    impact_severity: int  # 0-100
    affected_markets: list
    
    recommendation: str

    @property
    def score(self) -> int:
        if self.carry_status == "CRISIS":
            return -90
        elif self.carry_status == "UNWINDING":
            return -70
        elif self.carry_status == "UNSTABLE":
            return -40
        elif self.carry_status == "BUILDING":
            return 20
        else:
            return 10


class YenCarryMonitor:
    """
    Yen Carry Trade Monitor
    
    What is Yen Carry:
    - Borrow cheap yen (low rates)
    - Invest in higher yield assets
    - Profit from rate differential
    
    Why it matters:
    - $20+ trillion in carry trades
    - Yen strength forces unwinding
    - Unwinding causes global selloff
    - August 2024 crash was carry unwind
    
    Warning Signs:
    1. USD/JPY dropping fast (yen strengthening)
    2. BOJ rate hike signals
    3. VIX spiking with yen strength
    4. Japanese stocks falling
    """
    
    def __init__(self):
        pass
    
    def analyze(self) -> YenCarrySignal:
        """Analyze yen carry trade risk"""
        
        try:
            # Get USD/JPY data (via FXY inverse ETF)
            fxy = yf.download('FXY', period='1mo', progress=False)
            if hasattr(fxy.columns, 'get_level_values'):
                fxy.columns = fxy.columns.get_level_values(0)
            
            # Also check Japanese stocks
            ewj = yf.download('EWJ', period='1mo', progress=False)
            if hasattr(ewj.columns, 'get_level_values'):
                ewj.columns = ewj.columns.get_level_values(0)
            
            if fxy.empty:
                return self._default()
            
            # FXY is yen strength - when FXY rises, yen strengthens
            fxy_current = float(fxy['Close'].iloc[-1])
            fxy_5d_ago = float(fxy['Close'].iloc[-5]) if len(fxy) > 5 else fxy_current
            fxy_change = (fxy_current / fxy_5d_ago - 1) * 100
            
            # Approximate USD/JPY from FXY (inverse relationship)
            usdjpy_approx = 100 / fxy_current * 150  # Rough approximation
            
            # Determine yen trend
            if fxy_change > 2:
                yen_trend = "STRENGTHENING"
            elif fxy_change < -2:
                yen_trend = "WEAKENING"
            else:
                yen_trend = "STABLE"
            
            # Carry trade status
            if fxy_change > 5:
                carry_status = "CRISIS"
                unwind_risk = "CRITICAL"
                severity = 90
            elif fxy_change > 3:
                carry_status = "UNWINDING"
                unwind_risk = "HIGH"
                severity = 70
            elif fxy_change > 1.5:
                carry_status = "UNSTABLE"
                unwind_risk = "MEDIUM"
                severity = 50
            elif fxy_change < -1:
                carry_status = "BUILDING"
                unwind_risk = "LOW"
                severity = 20
            else:
                carry_status = "STABLE"
                unwind_risk = "LOW"
                severity = 30
            
            # Affected markets
            affected = []
            if severity >= 50:
                affected = ['US Tech (QQQ)', 'Global Equities', 'Emerging Markets', 'High Yield Bonds']
            elif severity >= 30:
                affected = ['US Tech (QQQ)', 'Risk Assets']
            
            # Recommendation
            if carry_status == "CRISIS":
                rec = "🚨 CRISIS: Yen carry unwinding! Reduce ALL risk immediately"
            elif carry_status == "UNWINDING":
                rec = "⚠️ UNWINDING: Yen strengthening fast, reduce leverage"
            elif carry_status == "UNSTABLE":
                rec = "📊 WATCH: Yen gaining, monitor carry unwind risk"
            else:
                rec = "✅ Yen carry stable, no immediate risk"
            
            return YenCarrySignal(
                usdjpy=usdjpy_approx,
                usdjpy_change_5d=-fxy_change,  # Inverse
                yen_trend=yen_trend,
                yen_momentum=fxy_change,
                carry_status=carry_status,
                unwind_risk=unwind_risk,
                impact_severity=severity,
                affected_markets=affected,
                recommendation=rec
            )
            
        except Exception as e:
            logger.debug(f"Yen carry error: {e}")
            return self._default()
    
    def _default(self) -> YenCarrySignal:
        return YenCarrySignal(
            150, 0, "UNKNOWN", 0, "UNKNOWN", "UNKNOWN", 0, [], "No data"
        )


def get_yen_carry() -> YenCarryMonitor:
    return YenCarryMonitor()


if __name__ == "__main__":
    print("Testing YenCarryMonitor...")
    yc = YenCarryMonitor()
    
    sig = yc.analyze()
    
    print(f"\n{'='*50}")
    print("YEN CARRY TRADE MONITOR")
    print('='*50)
    print(f"USD/JPY (approx): {sig.usdjpy:.1f}")
    print(f"5d Change: {sig.usdjpy_change_5d:+.2f}%")
    print(f"\nYen Trend: {sig.yen_trend}")
    print(f"Momentum: {sig.yen_momentum:+.2f}%")
    print(f"\nCarry Status: {sig.carry_status}")
    print(f"Unwind Risk: {sig.unwind_risk}")
    print(f"Severity: {sig.impact_severity}/100")
    print(f"Affected: {sig.affected_markets}")
    print(f"\nRecommendation: {sig.recommendation}")
