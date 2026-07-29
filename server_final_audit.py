from composite_signal import get_composite_engine
import pprint
import sys
from loguru import logger

def audit_final_score(symbol="HST"):
    logger.remove()
    print(f"\n{'='*60}")
    print(f"### DEFINITIVE SCORE AUDIT: {symbol} ###")
    print(f"{'='*60}")
    
    engine = get_composite_engine()
    result = engine.analyze(symbol)
    
    print(f"\nFINAL COMPOSITE SCORE: {result.composite_score}")
    print(f"FINAL CONFIDENCE: {result.confidence}%")
    print(f"ACTION: {result.action.value}")
    
    print("\nCATEGORY BREAKDOWN (Raw Scores vs Weighted Impact):")
    categories = [
        ('Macro', result.macro_score),
        ('Technical', result.technical_score),
        ('Fundamental', result.fundamental_score),
        ('Smart Money', result.smart_money_score),
        ('Sentiment', result.sentiment_score),
        ('Risk', result.risk_score)
    ]
    
    for name, cat in categories:
        weighted = cat.score * cat.weight
        print(f"  [{name:12}]: Raw={cat.score:+4d} | Weight={cat.weight:.2f} | Impact={weighted:+5.1f}")
        # print(f"    Signals: {cat.signals[:5]}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "HST"
    audit_final_score(sym)
