"""
ETF Flow Tracker
==================
Track money flows in sector ETFs and broad market.

Metrics:
1. Sector Inflows/Outflows
2. Flow Momentum
3. Smart Money vs Retail
4. Rotation Detection
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class SectorFlow:
    """Individual sector flow data"""
    sector: str
    etf: str
    flow_5d: float    # 5-day price change as proxy
    flow_20d: float   # 20-day
    relative_strength: float
    momentum: str     # "INFLOW", "OUTFLOW", "NEUTRAL"


@dataclass
class FlowSignal:
    """ETF flow analysis"""
    # Overall market
    market_flow: str   # "RISK_ON", "RISK_OFF", "NEUTRAL"
    
    # Sector flows
    top_inflows: List[SectorFlow]
    top_outflows: List[SectorFlow]
    
    # Rotation
    rotation_type: str  # "GROWTH_TO_VALUE", "VALUE_TO_GROWTH", "DEFENSIVE", "CYCLICAL"
    rotation_strength: int
    
    # Specific sectors
    tech_flow: str
    finance_flow: str
    energy_flow: str
    defensive_flow: str
    
    # Scoring
    flow_score: int  # -100 to +100
    favored_sectors: List[str]
    avoid_sectors: List[str]
    details: List[str]


class ETFFlowTracker:
    """
    ETF Sector Flow Analysis
    
    Uses ETF price momentum as proxy for flows:
    - Rising funds = inflows
    - Falling funds = outflows
    
    Sector ETFs:
    XLK - Tech, XLF - Finance, XLE - Energy
    XLV - Healthcare, XLI - Industrials
    XLP - Staples, XLY - Consumer Disc
    XLU - Utilities, XLRE - Real Estate
    XLB - Materials, XLC - Comm Services
    
    Rotation Signals:
    - Tech rising, Utilities falling = Risk-On
    - Staples/Utilities rising = Defensive
    - Finance rising = Rate expectations up
    """
    
    SECTORS = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLE': 'Energy',
        'XLV': 'Healthcare',
        'XLI': 'Industrials',
        'XLP': 'Consumer Staples',
        'XLY': 'Consumer Discretionary',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLB': 'Materials',
        'XLC': 'Communication'
    }
    
    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def analyze(self) -> FlowSignal:
        """Analyze ETF flows"""
        details = []
        score = 0
        
        # Fetch all sector data
        flows = []
        for etf, name in self.SECTORS.items():
            df = self._fetch_data(etf)
            if df is None or df.empty:
                continue
            
            close = df['Close']
            
            # Calculate flows (price momentum as proxy)
            flow_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100 if len(close) >= 5 else 0
            flow_20d = (close.iloc[-1] / close.iloc[-20] - 1) * 100 if len(close) >= 20 else 0
            
            # Relative strength vs SPY
            spy = self._fetch_data('SPY')
            if spy is not None and len(spy) >= 5:
                spy_ret = (spy['Close'].iloc[-1] / spy['Close'].iloc[-5] - 1) * 100
                rel_strength = flow_5d - spy_ret
            else:
                rel_strength = 0
            
            if flow_5d > 2:
                momentum = "INFLOW"
            elif flow_5d < -2:
                momentum = "OUTFLOW"
            else:
                momentum = "NEUTRAL"
            
            flows.append(SectorFlow(
                sector=name,
                etf=etf,
                flow_5d=flow_5d,
                flow_20d=flow_20d,
                relative_strength=rel_strength,
                momentum=momentum
            ))
        
        # Sort by 5-day flow
        flows_sorted = sorted(flows, key=lambda x: x.flow_5d, reverse=True)
        top_inflows = flows_sorted[:3]
        top_outflows = flows_sorted[-3:]
        
        # Determine market flow
        inflow_count = len([f for f in flows if f.momentum == "INFLOW"])
        outflow_count = len([f for f in flows if f.momentum == "OUTFLOW"])
        
        if inflow_count > outflow_count + 3:
            market_flow = "RISK_ON"
            score += 25
        elif outflow_count > inflow_count + 3:
            market_flow = "RISK_OFF"
            score -= 25
        else:
            market_flow = "NEUTRAL"
        
        # Specific sector analysis
        tech_flow = self._get_flow_for('XLK', flows)
        finance_flow = self._get_flow_for('XLF', flows)
        energy_flow = self._get_flow_for('XLE', flows)
        
        # Defensive (staples + utilities)
        staples = next((f for f in flows if f.etf == 'XLP'), None)
        utilities = next((f for f in flows if f.etf == 'XLU'), None)
        if staples and utilities:
            def_avg = (staples.flow_5d + utilities.flow_5d) / 2
            if def_avg > 2:
                defensive_flow = "INFLOW"
                score -= 10  # Defensive rotation = caution
            elif def_avg < -2:
                defensive_flow = "OUTFLOW"
                score += 10
            else:
                defensive_flow = "NEUTRAL"
        else:
            defensive_flow = "NEUTRAL"
        
        # Rotation type
        tech = next((f for f in flows if f.etf == 'XLK'), None)
        xlp = next((f for f in flows if f.etf == 'XLP'), None)
        xlf = next((f for f in flows if f.etf == 'XLF'), None)
        
        if tech and xlp:
            if tech.flow_5d > 2 and xlp.flow_5d < 0:
                rotation = "GROWTH_TO_RISK"
                rotation_strength = 70
                score += 15
                details.append("GROWTH_ROTATION")
            elif xlp.flow_5d > 2 and tech.flow_5d < 0:
                rotation = "DEFENSIVE"
                rotation_strength = 60
                score -= 15
                details.append("DEFENSIVE_ROTATION")
            elif xlf and xlf.flow_5d > 2:
                rotation = "CYCLICAL"
                rotation_strength = 50
            else:
                rotation = "MIXED"
                rotation_strength = 30
        else:
            rotation = "UNKNOWN"
            rotation_strength = 0
        
        # Favored/Avoid sectors
        favored = [f.etf for f in top_inflows if f.flow_5d > 1]
        avoid = [f.etf for f in top_outflows if f.flow_5d < -1]
        
        details.append(f"INFLOWS:{[f.etf for f in top_inflows[:2]]}")
        details.append(f"OUTFLOWS:{[f.etf for f in top_outflows[:2]]}")
        
        return FlowSignal(
            market_flow=market_flow,
            top_inflows=top_inflows,
            top_outflows=top_outflows,
            rotation_type=rotation,
            rotation_strength=rotation_strength,
            tech_flow=tech_flow,
            finance_flow=finance_flow,
            energy_flow=energy_flow,
            defensive_flow=defensive_flow,
            flow_score=max(-100, min(100, score)),
            favored_sectors=favored,
            avoid_sectors=avoid,
            details=details
        )
    
    def _get_flow_for(self, etf: str, flows: List[SectorFlow]) -> str:
        """Get flow for specific ETF"""
        f = next((f for f in flows if f.etf == etf), None)
        return f.momentum if f else "NEUTRAL"
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        if symbol in self._cache:
            return self._cache[symbol]
        
        try:
            df = yf.download(symbol, period='30d', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            self._cache[symbol] = df
            return df
        except:
            return None


# Global
_tracker = None

def get_flow_tracker() -> ETFFlowTracker:
    global _tracker
    if _tracker is None:
        _tracker = ETFFlowTracker()
    return _tracker


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing ETFFlowTracker...")
    
    tracker = ETFFlowTracker()
    result = tracker.analyze()
    
    print(f"\n{'='*60}")
    print("ETF SECTOR FLOW ANALYSIS")
    print('='*60)
    print(f"Market Flow: {result.market_flow}")
    print(f"Rotation: {result.rotation_type} (Strength: {result.rotation_strength})")
    print(f"Score: {result.flow_score:+d}")
    print()
    print("📈 Top Inflows:")
    for f in result.top_inflows:
        print(f"  {f.etf} ({f.sector}): {f.flow_5d:+.1f}%")
    print()
    print("📉 Top Outflows:")
    for f in result.top_outflows:
        print(f"  {f.etf} ({f.sector}): {f.flow_5d:+.1f}%")
    print()
    print(f"Tech: {result.tech_flow}")
    print(f"Finance: {result.finance_flow}")
    print(f"Defensive: {result.defensive_flow}")
    print()
    print(f"Favored: {result.favored_sectors}")
    print(f"Avoid: {result.avoid_sectors}")
    print(f"Details: {result.details}")
