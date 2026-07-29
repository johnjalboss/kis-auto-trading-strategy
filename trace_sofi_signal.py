import sys
import os
import pandas as pd
from loguru import logger

# Add current dir to path
sys.path.append('.')

from composite_signal import get_composite_engine

def trace():
    symbol = 'SOFI'
    logger.info(f"Starting deep trace for {symbol}")
    
    engine = get_composite_engine()
    
    # 1. Fetch data
    df = engine._fetch_data(symbol)
    if df is None:
        print("FAILED: No data for SOFI")
        return
        
    # 2. Category Analysis
    macro = engine._calculate_macro_score(df, symbol)
    tech = engine._calculate_technical_score(df, symbol)
    fund = engine._calculate_fundamental_score(df, symbol)
    smart = engine._calculate_smart_money_score(df, symbol)
    sent = engine._calculate_sentiment_score(df, symbol)
    risk = engine._calculate_risk_score(df, symbol)
    
    # 3. Decision Logic
    composite = (
        macro.score * 0.15 +
        tech.score * 0.25 +
        fund.score * 0.20 +
        smart.score * 0.20 +
        sent.score * 0.10 +
        risk.score * 0.10
    )
    
    print("\n" + "="*50)
    print(f"SYMBOL: {symbol}")
    print("="*50)
    print(f"Macro:       {macro.score:>4} | {macro.signals}")
    print(f"Technical:   {tech.score:>4} | {tech.signals}")
    print(f"Fundamental: {fund.score:>4} | {fund.signals}")
    print(f"Smart Money: {smart.score:>4} | {smart.signals}")
    print(f"Sentiment:   {sent.score:>4} | {sent.signals}")
    print(f"Risk:        {risk.score:>4} | {risk.signals}")
    print("-" * 50)
    print(f"COMPOSITE SCORE (CALC): {composite:.2f}")
    
    # Check Action Mapping
    def get_action(score):
        if score > 50: return "STRONG_BUY"
        if score > 25: return "BUY"
        if score > 10: return "WEAK_BUY"
        if score > -15: return "HOLD"
        return "SELL_DOMAIN"
        
    print(f"MAPPED ACTION: {get_action(composite)}")
    
    # 4. Check for potential overrides
    import universe
    from universe import FALLBACK_SYMBOLS
    
    if symbol in FALLBACK_SYMBOLS:
        print(f"\n[!] {symbol} IS IN FALLBACK_SYMBOLS")
        # In strategy.py: score < 70 -> ActionType.HOLD
        if composite < 70:
            print(f"EXPLANATION: Fallback symbol requires score 70 in strategy.py. Current {composite:.1f} < 70 -> This explains why the bot logs it as HOLD even if the composite score is 42.")

if __name__ == '__main__':
    trace()
