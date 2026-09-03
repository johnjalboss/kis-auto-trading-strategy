
import sys
from loguru import logger
from composite_signal import get_composite_engine

logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="DEBUG")

engine = get_composite_engine()
symbol = "PLTR"
print(f"Testing CompositeSignalEngine for {symbol}...")
result = engine.analyze(symbol)

print("\n--- RESULTS ---")
print(f"Symbol: {result.symbol}")
print(f"Action: {result.action}")
print(f"Score:  {result.composite_score}")
print(f"Conf:   {result.confidence}%")
print(f"Summary: {result.summary}")

print("\n--- CATEGORY BREAKDOWN ---")
print(f"Macro:       {result.macro_score.score} (Signals: {result.macro_score.signals})")
print(f"Technical:   {result.technical_score.score} (Signals: {result.technical_score.signals})")
print(f"Fundamental: {result.fundamental_score.score} (Signals: {result.fundamental_score.signals})")
print(f"Smart Money: {result.smart_money_score.score} (Signals: {result.smart_money_score.signals})")
print(f"Sentiment:   {result.sentiment_score.score} (Signals: {result.sentiment_score.signals})")
print(f"Risk:        {result.risk_score.score} (Signals: {result.risk_score.signals})")
