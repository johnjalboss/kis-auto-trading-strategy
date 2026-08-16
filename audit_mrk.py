import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from screener import Screener
from composite_signal import CompositeSignalGenerator
from strategy import StrategyEngine
from kis_data import download

print("=== DEEP AUDIT OF MRK (MERCK & CO.) ===")

# 1. Check MRK data & indicators
df = download("MRK", period="6mo")
if df is not None and not df.empty:
    print(f"MRK data points: {len(df)}")
    print(f"Latest Price: ${float(df['Close'].iloc[-1]):.2f}")
    
    # 2. Run Screener on MRK
    screener = Screener()
    score_data = screener.score_stock("MRK")
    print("\n--- SCREENER METRICS FOR MRK ---")
    for k, v in (score_data or {}).items():
        print(f"  {k}: {v}")

    # 3. Run Composite Signal Generator
    csg = CompositeSignalGenerator()
    comp_score, comp_details = csg.evaluate("MRK", df)
    print(f"\n--- COMPOSITE SIGNAL FOR MRK ---")
    print(f"  Total Composite Score: {comp_score:.2f} / 100")
    for k, v in comp_details.items():
        print(f"  {k}: {v}")

# 4. Check Top 15 ranked stocks across universe
print("\n--- UNIVERSE SCREENING TOP 15 RANKING ---")
try:
    candidates = screener.get_candidates(top_n=15)
    for i, c in enumerate(candidates, 1):
        sym = c.get('symbol')
        score = c.get('score', 0)
        sector = c.get('sector', 'N/A')
        print(f"  #{i:02d} {sym:6s} | Score: {score:.2f} | Sector: {sector}")
except Exception as e:
    print("Screener candidates error:", e)
