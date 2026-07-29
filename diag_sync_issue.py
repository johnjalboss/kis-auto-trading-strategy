from trader import Trader
from strategy import get_strategy
from loguru import logger
import sys

def main():
    trader = Trader()
    strategy = get_strategy()
    
    logger.info("--- Position Sync Audit ---")
    
    # 1. Get KIS Positions
    try:
        kis_positions = trader.get_positions()
        kis_symbols = {p.symbol for p in kis_positions}
        logger.info(f"KIS Broker Positions ({len(kis_positions)}):")
        for p in kis_positions:
            logger.info(f"  - {p.symbol}: qty={p.quantity}, avg_price=${p.avg_price}")
    except Exception as e:
        logger.error(f"Failed to fetch KIS positions: {e}")
        return

    # 2. Get Strategy Internal Positions
    strat_positions = strategy.get_all_positions()
    logger.info(f"Strategy Internal Positions ({len(strat_positions)}):")
    for sym, pos in strat_positions.items():
        logger.info(f"  - {sym}: qty={pos.quantity}, entry_price=${pos.entry_price}")

    # 3. Analyze Discrepancies
    strat_symbols = set(strat_positions.keys())
    
    only_in_strat = strat_symbols - kis_symbols
    only_in_kis = kis_symbols - strat_symbols
    
    if only_in_strat:
        logger.warning(f"PHANTOM POSITIONS (In Strategy NOT in KIS): {only_in_strat}")
    else:
        logger.info("No phantom positions found in strategy.")
        
    if only_in_kis:
        logger.warning(f"UNTRACKED POSITIONS (In KIS NOT in Strategy): {only_in_kis}")
    else:
        logger.info("No untracked positions found in strategy.")

    # 4. Attempt Manual Sync
    logger.info("Executing manual strategy.sync_positions()...")
    strategy.sync_positions(kis_positions)
    
    # 5. Re-verify
    new_strat_positions = strategy.get_all_positions()
    logger.info(f"Strategy Positions after sync ({len(new_strat_positions)}):")
    for sym, pos in new_strat_positions.items():
        logger.info(f"  - {sym}: qty={pos.quantity}")
        
    final_strat_symbols = set(new_strat_positions.keys())
    if "SQQQ" in final_strat_symbols:
        logger.warning("SQQQ STILL in strategy after sync!")
    else:
        logger.success("SQQQ NOT in strategy after sync.")

if __name__ == "__main__":
    main()
