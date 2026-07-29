"""
KIS Auto-Trading Bot - Master Entrypoint
========================================
Delegates the entire execution lifecycle (130+ Modules) to the BotOrchestrator.
"""

import argparse
import sys
import os

# GLOBAL API OVERRIDE: 
# Force all 130+ modules to silently use KIS API instead of yfinance
import data_proxy  

from loguru import logger
from dotenv import load_dotenv

# Import Core Infra
from trader import Trader
from strategy import StrategyEngine
from risk_manager import RiskManager
from database import get_database

from orchestrator import BotOrchestrator

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    logger.add("logs/trading_bot.log", rotation="10 MB", retention="10 days", level="DEBUG")

def main():
    parser = argparse.ArgumentParser(description="KIS Algo Trading Bot (130-Module Lifecycle)")
    parser.add_argument("--dry-run", action="store_true", help="Run without real money execution")
    args = parser.parse_args()

    load_dotenv()
    setup_logging()
    
    # 🌟 무인 원격 자동 업데이트 체크 (부팅 시 깃허브 최신 전략 파일 자동 패치)
    try:
        from updater import check_and_update
        check_and_update()
    except Exception as _up_err:
        logger.debug("Auto-update check skipped/bypassed: {}", _up_err)
    
    logger.info("="*60)
    logger.info("🚀 KIS AUTO-TRADING BOT INITIALIZING (DRY RUN: {})", args.dry_run)
    logger.info("="*60)

    try:
        trader = Trader()
        strategy = StrategyEngine()
        
        # Load Risk & DB Systems
        rm = RiskManager()
        db = get_database()
        
        # Sync open live positions from broker into strategy state
        try:
            live_positions = trader.get_positions()
            strategy.sync_positions(live_positions)
            
            # RiskManager Sync: Ensure RM knows about existing positions to enforce MAX_POSITIONS
            buying_power = trader.get_buying_power()
            total_market_value = sum(p.quantity * p.current_price for p in live_positions)
            total_portfolio = buying_power + total_market_value
            
            rm.start_day(total_portfolio)
            for p in live_positions:
                exposure_pct = (p.quantity * p.current_price) / total_portfolio if total_portfolio > 0 else 0
                rm.add_position(p.symbol, p.avg_price, p.quantity, exposure_pct)
                
            logger.info("Synchronized {} live positions into Strategy and RiskManager (Portfolio: ${:,.2f})", 
                       len(live_positions), total_portfolio)
        except Exception as e:
            logger.error(f"Failed to sync positions from broker: {e}")
        
        # Hand off execution to the Orchestrator
        orchestrator = BotOrchestrator(
            trader=trader, 
            strategy=strategy, 
            rm=rm, 
            db=db, 
            is_dry_run=args.dry_run
        )
        
        # Launch the 6-Phase Lifecycle
        orchestrator.run_lifecycle()
        
    except KeyboardInterrupt:
        logger.info("Bot manually terminated by user.")
    except Exception as e:
        logger.exception(f"FATAL ERROR IN MAIN THREAD: {e}")

if __name__ == "__main__":
    main()
