from composite_signal import get_composite_engine
from loguru import logger
import sys
import json

def audit_ticker(symbol):
    print(f"\n{'='*50}")
    print(f"AUDITING SIGNAL FOR: {symbol}")
    print(f"{'='*50}")
    
    engine = get_composite_engine()
    # Force fresh analysis (skip cache)
    result = engine.analyze(symbol)
    
    print(f"\nACTION: {result.action.value} (Score: {result.composite_score}, Confidence: {result.confidence}%)")
    
    print("\n[CATEGORY BREAKDOWN]")
    categories = [
        ("Macro", result.macro_score),
        ("Technical", result.technical_score),
        ("Fundamental", result.fundamental_score),
        ("Smart Money", result.smart_money_score),
        ("Sentiment", result.sentiment_score),
        ("Risk", result.risk_score)
    ]
    
    for name, cat in categories:
        print(f"{name:12}: {cat.score:+4} | Signals: {cat.signals}")

    print("\n[BULLISH SIGNALS]")
    for s in result.bullish_signals:
        print(f" + {s}")
        
    print("\n[BEARISH SIGNALS]")
    for s in result.bearish_signals:
        print(f" - {s}")
        
    print("\n[WARNINGS]")
    for w in result.warnings:
        print(f" ! {w}")

    print(f"\nFINAL POSITION SIZE: {result.position_size_pct:.1%}")

if __name__ == "__main__":
    logger.remove()
    tickers = ["HST", "XOM", "NVDA", "TQQQ"]
    for t in tickers:
        try:
            audit_ticker(t)
        except Exception as e:
            print(f"Failed to audit {t}: {e}")
