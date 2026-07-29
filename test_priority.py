import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

try:
    from strategy import StrategyEngine, FALLBACK_SYMBOLS
    from loguru import logger
    
    # Setup logger to see our messages
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    
    engine = StrategyEngine()
    
    symbol = "SOFI"
    print(f"\n--- Testing {symbol} (In Fallback: {symbol in FALLBACK_SYMBOLS}) ---")
    
    # Test Case 1: NOT Screened
    print("\n[Test 1] NOT Screened (Expected: Needs 70)")
    # We use a macro_score that won't trigger macro filter
    res1 = engine.check_entry(symbol, macro_score=50, is_screened=False)
    print(f"Result: {res1.action}, Reason: {res1.reason}, Confidence: {res1.confidence}")
    
    # Test Case 2: IS Screened
    print("\n[Test 2] IS Screened (Expected: Needs Phase Config Score, e.g., 60-70)")
    res2 = engine.check_entry(symbol, macro_score=50, is_screened=True)
    print(f"Result: {res2.action}, Reason: {res2.reason}, Confidence: {res2.confidence}")
    
    if res1.confidence < 70 and "Needs 70 for Fallback" in res1.reason:
        print("\nSUCCESS: Test 1 confirmed fallback penalty is active for non-screened stocks.")
    
    if res2.confidence >= 40 and "Priority: Screened" in res2.reason:
         print("SUCCESS: Test 2 confirmed priority logic for screened stocks.")
    elif res2.confidence >= 40 and "Low confidence" in res2.reason and "Fallback" not in res2.reason:
         print("SUCCESS: Test 2 confirmed fallback penalty was BYPASSED for screened stock.")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
