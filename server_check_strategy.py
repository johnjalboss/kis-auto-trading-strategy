import trader
import config
from composite_signal import get_composite_engine
from strategy import StrategyEngine
import pandas as pd
from loguru import logger

def run_check():
    logger.remove()
    print("=== STRATEGY & UPGRADE DIAGNOSIS ===")
    
    t = trader.get_trader()
    t.start()
    
    engine = get_composite_engine()
    strat = StrategyEngine()
    
    # 1. Check current positions
    positions = t.get_positions()
    print(f"\n[CURRENT POSITIONS: {len(positions)}]")
    
    pos_scores = {}
    for p in positions:
        try:
            sig = engine.analyze(p.symbol)
            pos_scores[p.symbol] = sig.composite_score
            pnl_pct = (p.current_price - p.avg_price) / p.avg_price if p.avg_price > 0 else 0
            print(f" - {p.symbol}: Score={sig.composite_score}, P&L={pnl_pct:+.2%}, Action={sig.action.value}")
            
            # Check exit evaluation
            exit_sig = strat.check_exit(p.symbol, p.current_price)
            print(f"   -> Strategy Exit Check: {exit_sig.action} ({exit_sig.reason})")
        except Exception as e:
            print(f" - {p.symbol}: Failed to analyze ({e})")

    # 2. Check for potential upgrades
    import orchestrator
    orc = orchestrator.Orchestrator()
    # Mocking target universe (usually would be the list of stocks the bot is scanning)
    # Let's check some high-momentum stocks or the fallback universe
    targets = config.FALLBACK_UNIVERSE if hasattr(config, "FALLBACK_UNIVERSE") else ["AAPL", "NVDA", "TSLA", "TQQQ", "MSFT", "GOOGL", "AMZN"]
    
    print(f"\n[POTENTIAL UPGRADES (Scanning {len(targets)} stocks)]")
    best_target = None
    best_score = -100
    
    for symbol in targets:
        if symbol in [p.symbol for p in positions]:
            continue
        try:
            sig = engine.analyze(symbol)
            if sig.composite_score > best_score:
                best_score = sig.composite_score
                best_target = sig
            if sig.composite_score > 40:
                print(f" * {symbol}: Score={sig.composite_score} ({sig.action.value})")
        except:
            pass
            
    if best_target:
        print(f"\nBest Available: {best_target.symbol} at {best_target.composite_score} points")
        
        # Check if any position can be upgraded
        for p_sym, p_score in pos_scores.items():
            gap = best_target.composite_score - p_score
            print(f"   vs {p_sym}: Gap={gap} (Threshold={config.UPGRADE_SCORE_GAP})")
            if gap >= config.UPGRADE_SCORE_GAP:
                 print(f"   >>> QUALIFIES FOR UPGRADE! <<<")

if __name__ == "__main__":
    run_check()
