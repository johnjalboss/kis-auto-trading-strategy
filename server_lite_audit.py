import os
import sys
sys.path.append(os.getcwd())

from short_squeeze import ShortSqueezeMonitor
from earnings_quality import EarningsQualityScorer
from estimate_revision import EstimateRevisionAnalyzer
from fx_risk import FXRiskAnalyzer
from economic_surprise import EconomicSurpriseAnalyzer
import pandas as pd
import yfinance as yf

def audit_lite(symbol="HST"):
    print(f"\n{'='*60}")
    print(f"### LITE WEIGHTING AUDIT: {symbol} ###")
    print(f"{'='*60}")
    
    # 1. Mock Legacy Technical Score (what the user saw yesterday)
    legacy_tech_score = 32
    print(f"\nLegacy Technical Part (Yesterday's Baseline): {legacy_tech_score}")
    
    # 2. Run New Institutional Modules
    df = yf.download(symbol, period="1mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    inst_mods = [
        ("FX Risk (Macro)", FXRiskAnalyzer(), 0.10),
        ("Economic (Macro)", EconomicSurpriseAnalyzer(), 0.10),
        ("Earnings (Fundamental)", EarningsQualityScorer(), 0.10),
        ("Estimate (Fundamental)", EstimateRevisionAnalyzer(), 0.10),
        ("Short Squeeze (Smart Money)", ShortSqueezeMonitor(), 0.25)
    ]
    
    total_inst_weighted = 0
    print("\nDetailed Institutional Breakdown:")
    for name, mod, weight in inst_mods:
        res = mod.analyze(df, symbol=symbol)
        raw = res.get('score', 0)
        weighted = raw * weight
        total_inst_weighted += weighted
        print(f"  {name:30} : Raw={raw:+3d} | Weight={weight:.2f} | Impact={weighted:+5.1f}")
        
    # 3. Final Calculation Simulation
    # Technical Category (Legacy) Impact: 32 * 0.35 (assuming 0.35 weight from technical)
    tech_impact = 32 * 0.35
    
    print(f"\nFINAL WEIGHTED DECISION CALCULATION:")
    print(f"  Technical Weighted Impact (35%): {tech_impact:+5.1f}")
    print(f"  Institutional Weighted Total:      {total_inst_weighted:+5.1f}")
    
    final_composite = tech_impact + total_inst_weighted
    print(f"  --------------------------------------------")
    print(f"  SIMULATED COMPOSITE SCORE:         {final_composite:.1f}")
    
    print(f"\nCONCLUSION: The '65 points' were raw points.")
    print(f"In the final decision, they contribute approx {total_inst_weighted:.1f} points.")
    print("="*60 + "\n")

if __name__ == "__main__":
    audit_lite("HST")
