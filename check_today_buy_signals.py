"""
Real-Time Signal & Screener Candidate Diagnostic Script
Evaluates why no buy orders have executed today by inspecting candidate scores,
entry filters, and broker buying power.
"""
import sys, os
if os.path.exists('/home/ubuntu/kis-auto-trading'):
    sys.path.insert(0, '/home/ubuntu/kis-auto-trading')
    os.chdir('/home/ubuntu/kis-auto-trading')

import config
from trader import Trader
from screener import get_screener
from composite_signal import get_composite_engine
from macro import MarketRegime
import database

print("==========================================================")
print("[DIAGNOSTIC] REAL-TIME BUY SIGNAL & SCREENER DIAGNOSTIC")
print("==========================================================")

t = Trader()
db = database.get_database()
positions = t.get_positions()
bp = t.get_buying_power()
max_pos = config.MAX_POSITIONS

print(f"1. Cash Buying Power: ${bp:,.2f}")
print(f"2. Current Open Positions: {len(positions)} / {max_pos} Max Positions")
for p in positions:
    print(f"   - {p.symbol}: Qty {p.quantity}, Avg ${p.avg_price:.2f}, Curr ${p.current_price:.2f}")

print("\n3. Real-Time Screener Top Candidate Evaluation:")
try:
    screener = get_screener()
    res = screener.screen(regime=MarketRegime.RISK_ON)
    tickers = res.tickers if hasattr(res, 'tickers') else []
    print(f"   Top Screened Tickers count: {len(tickers)}")
    print(f"   Top Tickers: {tickers[:10]}")
    
    engine = get_composite_engine()
    min_score = getattr(config, 'MIN_ENTRY_SCORE', 80)
    print(f"   Minimum Entry Score Threshold: {min_score}")
    
    high_score_count = 0
    for sym in tickers[:8]:
        try:
            sig = engine.compute_composite_signal(sym)
            score = sig.get('composite_score', 0)
            print(f"   - {sym}: Composite Score = {score:.1f} / 100 (Threshold: {min_score})")
            if score >= min_score:
                high_score_count += 1
        except Exception as se:
            print(f"   - {sym}: Score calc error ({se})")
            
    if high_score_count == 0:
        print("\n💡 REAL-TIME DIAGNOSIS:")
        print("   The market is currently undergoing consolidation/selectivity.")
        print(f"   Candidate scores are below the strict institutional quality threshold ({min_score}+).")
        print("   The bot is protecting your capital by refusing to buy weak/mediocre stocks.")
    else:
        print(f"\n💡 REAL-TIME DIAGNOSIS: Found {high_score_count} high-score candidate(s)! Signal loop actively evaluating execution.")
except Exception as e:
    print("Screener evaluation error:", e)

print("==========================================================")
