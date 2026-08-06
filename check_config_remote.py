import sys
sys.path.insert(0, "/home/ubuntu/kis-auto-trading")
from dotenv import load_dotenv
load_dotenv("/home/ubuntu/kis-auto-trading/.env")
import config
print("MAX_POSITIONS:", config.MAX_POSITIONS)
print("UPGRADE_SCORE_GAP:", config.UPGRADE_SCORE_GAP)
print("UPGRADE_MIN_HOLD_MINUTES:", config.UPGRADE_MIN_HOLD_MINUTES)
print("UPGRADE_PROFIT_PROTECT_PCT:", config.UPGRADE_PROFIT_PROTECT_PCT)
print("UPGRADE_MAX_PER_DAY:", config.UPGRADE_MAX_PER_DAY)
