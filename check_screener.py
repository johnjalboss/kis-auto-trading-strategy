import sys
sys.path.append("/home/ubuntu/kis-auto-trading")
from loguru import logger
logger.remove()
logger.add(sys.stdout, level="DEBUG")

try:
    import screener
    s = screener.DynamicScreener()
    s.MIN_SCORE = 0
    res = s.screen()
    print("Scores:")
    for score in res.scores:
        print(f"{score.symbol}: {score.total_score}")
except Exception as e:
    print(f"Error: {e}")
