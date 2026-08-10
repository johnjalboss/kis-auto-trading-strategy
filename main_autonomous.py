"""
Autonomous Trading Main Loop
===============================
24/7 autonomous trading with all filters.
Run on Oracle Free Tier Ampere.
"""

import time
import sys
from datetime import datetime
from loguru import logger

import os
import fcntl

# Single-Instance Mutex Lock File Mechanism (Prevents duplicate bot execution)
LOCK_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kis_bot_daemon.lock")
try:
    _lock_fp = open(LOCK_FILE_PATH, "w")
    fcntl.flock(_lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    _lock_fp.write(str(os.getpid()))
    _lock_fp.flush()
except IOError:
    print(f"🚨 [SINGLE_INSTANCE_GUARD] Another main_autonomous.py process (PID active) is already running! Terminating this duplicate process immediately.")
    sys.exit(0)

# Import all modules
from scheduler import get_scheduler
from health_monitor import get_health_monitor
from emergency_stop import get_emergency_stop
from drawdown_controller import get_drawdown_controller
from adaptive_strategy import get_adaptive_selector
from notification import get_notifier
from trade_journal import get_trade_journal


class AutonomousTrader:
    """Main 24/7 trading loop"""
    
    def __init__(self, initial_capital: float = 100000):
        self.capital = initial_capital
        
        # Initialize all systems
        self.scheduler = get_scheduler()
        self.health = get_health_monitor()
        self.emergency = get_emergency_stop()
        self.drawdown = get_drawdown_controller(initial_capital)
        self.strategy = get_adaptive_selector()
        self.notifier = get_notifier()
        self.journal = get_trade_journal()
        
        self.running = True
        self.cycle_count = 0
        
        logger.info(f"🚀 Autonomous Trader initialized (${initial_capital:,.0f})")
    
    def run(self):
        """Main loop - runs forever"""
        logger.info("Starting autonomous trading loop...")
        self.notifier.alert_status("Started", "Autonomous trader online")
        
        while self.running:
            try:
                self.cycle_count += 1
                self._run_cycle()
                
            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                self.running = False
                
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                self.health.record_error(str(e))
                self.emergency.report_error(str(e))
                time.sleep(60)
        
        self._shutdown()
    
    def _run_cycle(self):
        """Single trading cycle"""
        # 1. Check market hours
        can_trade, reason = self.scheduler.should_trade()
        session = self.scheduler.get_session()
        
        if session == "CLOSED":
            # Sleep longer when market closed
            logger.debug(f"Market closed: {reason}")
            time.sleep(300)  # 5 min
            return
        
        # 2. Check emergency
        emergency_state = self.emergency.check_recovery()
        if emergency_state and emergency_state.is_active:
            logger.warning(f"Emergency active: {emergency_state.severity}")
            time.sleep(60)
            return
        
        # 3. Check drawdown
        dd_state = self.drawdown._calculate_state()
        if not dd_state.trading_allowed:
            logger.warning(f"Trading stopped: {dd_state.reason}")
            time.sleep(300)
            return
        
        # 4. Check health
        health = self.health.check_health()
        if not health.is_healthy:
            logger.warning(f"Health issues: {health.warnings}")
        
        # 5. Get adaptive strategy
        if can_trade:
            adaptive = self.strategy.analyze()
            alloc = adaptive.allocation
            
            logger.info(f"Regime: {adaptive.current_regime.value}")
            logger.info(f"Strategy: {alloc.primary_strategy.value}")
            logger.info(f"Equity: {alloc.equity_allocation:.0%}")
            
            # Here you would call your actual trading logic
            # For now, just log
            self._execute_strategy(adaptive, dd_state)
            
            self.health.update_data_time()
        
        # 6. Sleep before next cycle
        sleep_time = 60 if can_trade else 300
        time.sleep(sleep_time)
    
    def _execute_strategy(self, adaptive, dd_state):
        """Execute trading strategy (placeholder)"""
        # This is where you integrate with KIS API
        # and your composite signal generator
        
        alloc = adaptive.allocation
        size_mult = dd_state.position_size_multiplier
        
        # Adjusted position size
        max_size = alloc.max_position_size * size_mult
        
        logger.debug(f"Max position: {max_size:.1%} (base {alloc.max_position_size:.0%} x {size_mult:.1f})")
        
        # TODO: Integrate with screener and composite signal
        # For each candidate:
        #   1. Get composite score
        #   2. Check min score threshold
        #   3. Execute if passes all filters
    
    def _shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down...")
        stats = self.journal.get_stats()
        self.notifier.alert_status("Shutdown", f"Stats: {stats}")
        logger.info("Goodbye!")


def main():
    """Entry point"""
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    logger.add("trading.log", rotation="1 day", retention="30 days")
    
    # Get capital from env or default
    import os
    capital = float(os.getenv("INITIAL_CAPITAL", "100000"))
    
    trader = AutonomousTrader(initial_capital=capital)
    trader.run()


if __name__ == "__main__":
    main()
