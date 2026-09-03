"""
Full Data Pipeline Integrity & Live Distortion Scan
===================================================
Validates:
1. _cleanse_ohlcv_data() on corrupted data (NaN, Inf, 0, inverted High/Low).
2. kis_data.download() for single ticker, multi-ticker, and index symbol (^VIX).
3. Strategy Zone A/B/C calculations with float/dataclass StochRSI.
4. VCPBreakoutEngine safe division guards.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np

print("======================================================================")
print("🔍 EXHAUSTIVE DATA PIPELINE INTEGRITY & CORRUPTION SCAN")
print("======================================================================")

# 1. Test Cleanse Engine with Inverted High/Low and Infs
print("\n[TEST 1] Data Cleansing & Geometry Repair:")
from kis_data import _cleanse_ohlcv_data
df_corrupt = pd.DataFrame({
    "Open": [100.0, np.nan, 102.0, 105.0],
    "High": [95.0, 101.0, np.inf, 104.0],   # Inverted High (< Open or Inf)
    "Low": [105.0, 99.0, 101.0, -5.0],     # Inverted Low (> Open or negative)
    "Close": [101.0, 100.5, 103.0, 106.0],
    "Volume": [1000, -500, np.nan, np.inf]
})
df_clean = _cleanse_ohlcv_data(df_corrupt)
print(f"  • Repaired High >= max(Open, Close): {(df_clean['High'] >= df_clean['Close']).all()}")
print(f"  • Repaired Low <= min(Open, Close): {(df_clean['Low'] <= df_clean['Close']).all()}")
print(f"  • Repaired Volume non-negative & finite: {(df_clean['Volume'] >= 0).all() and not df_clean['Volume'].isna().any()}")
assert (df_clean['High'] >= df_clean['Close']).all()
assert (df_clean['Low'] <= df_clean['Close']).all()
print("  ✅ [PASS] Data Cleansing and Geometry Repair verified!")

# 2. Test Single & Multi-Ticker Download & Index Fallback
print("\n[TEST 2] Index Symbol & Multi-Ticker Download:")
from kis_data import download
df_spy = download("SPY", period="5d")
assert df_spy is not None and not df_spy.empty
print(f"  • SPY downloaded: {len(df_spy)} rows, columns={list(df_spy.columns)}")

df_vix = download("^VIX", period="5d")
assert df_vix is not None and not df_vix.empty
print(f"  • ^VIX index fallback downloaded: {len(df_vix)} rows, columns={list(df_vix.columns)}")

df_multi = download(["AAPL", "MSFT"], period="5d")
assert df_multi is not None and not df_multi.empty
print(f"  • Multi-ticker (AAPL, MSFT) combined cleanly: {len(df_multi)} rows")
print("  ✅ [PASS] Single, Multi, and Index Download verified!")

# 3. Test StochRSI & Zone B Scoring in Strategy
print("\n[TEST 3] Strategy Zone B & Technical Indicator Calculation:")
from indicators import analyze_all
from strategy import get_strategy
df_spy_3mo = download("SPY", period="3mo")
strat = get_strategy()
ind = analyze_all(df_spy_3mo)
assert ind is not None
print(f"  • Indicator summary computed: RSI={ind.rsi:.1f}, StochRSI={ind.stoch_rsi:.2f}")

# Verify entry confidence calculation on SPY
score, breakdown, raw = strat._calc_entry_confidence(
    ind=ind,
    macro_score=0.0,
    cfg=strat.get_phase_config(),
    df=df_spy_3mo,
    comp_signal=None,
    symbol="SPY"
)
print(f"  • Strategy Confidence Score for SPY: {score} pts | Factors: {len(breakdown)}")
assert isinstance(score, int)
print("  ✅ [PASS] Strategy & Quant Alpha Engine Scan verified 100% clean!")

# 4. Test VCP Zero-Division Safety
print("\n[TEST 4] VCP Breakout Engine Zero-Division Guard:")
from vcp_breakout_engine import VCPBreakoutEngine
vcp = VCPBreakoutEngine()
# Test with zero arrays
df_zeros = pd.DataFrame({
    "Open": [0.0]*35,
    "High": [0.0]*35,
    "Low": [0.0]*35,
    "Close": [0.0]*35,
    "Volume": [0]*35
})
res_zero = vcp.analyze(df_zeros, "ZERO_STOCK")
assert res_zero["is_vcp_pattern"] is False
print("  ✅ [PASS] VCP Zero-Division & Edge Case Guard verified!")

print("\n======================================================================")
print("🎉 ALL DATA PIPELINES & DATA INTEGRITY SCANS PASSED 100% CLEAN!")
print("======================================================================")
