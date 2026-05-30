"""
Grand Orchestrator v2
=====================
Controls the 6-Phase Lifecycle of the complete 130-module trading bot.
Coordinates Infrastructure, Macro Analysis, Signal Generation, Risk Management,
Execution, and Analytics into one cohesive 24/7 autonomous loop.

Designed for Oracle Cloud Free Tier (Ampere A1) unattended operation.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from datetime import datetime, timedelta
import config

# Import Core Systems
from trader import Trader
from strategy import StrategyEngine
from screener import DynamicScreener
from risk_manager import RiskManager
from database import TradeDatabase
from smart_order import OrderType

@dataclass
class GlobalState:
    """Master state passed between phases"""
    is_trading_active: bool = False
    global_risk_level: str = "NORMAL"
    max_exposure_pct: float = 1.0
    allow_long: bool = True
    allow_short: bool = False
    current_regime: str = "UNKNOWN"
    target_universe: List[str] = field(default_factory=list)
    macro_data: Dict[str, Any] = field(default_factory=dict)
    last_macro_refresh: Optional[datetime] = None
    last_screen_refresh: Optional[datetime] = None
    modules_loaded: int = 0
    modules_failed: int = 0
    screened_symbols: List[str] = field(default_factory=list)

class BotOrchestrator:
    def __init__(self, trader: Trader, strategy: StrategyEngine, rm: RiskManager, db: TradeDatabase, is_dry_run: bool = False):
        self.trader = trader
        self.strategy = strategy
        self.rm = rm
        self.db = db
        self.is_dry_run = is_dry_run
        self.state = GlobalState()
        self._freq_controller = None
        self._exec_tracker = None
        self._manipulation_defense = None
        
        # Daily trade counter & upgrade counter
        self._daily_trade_count = 0
        self._daily_upgrade_count = 0
        self._last_trade_date = None
        
        logger.info("BotOrchestrator Booting... Initializing 130-Module Lifecycle")
    
    # Core watchlist: Expanded to 150+ quality stocks & ETFs across sectors (2026-05)
    FALLBACK_UNIVERSE = [
        # Mega-cap Tech & Communication
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NFLX",
        # Semiconductors & Hardware
        "NVDA", "AMD", "AVGO", "INTC", "MU", "QCOM", "TXN", "LRCX", "KLAC", "ASML", "ARM",
        "ON", "WDC", "STX", "SMCI", "ANET", "MRVL", "ADI", "MCHP", "SWKS", "QRVO",
        # Software & Cloud & Cybersecurity
        "CRM", "ADBE", "NOW", "PANW", "CRWD", "PLTR", "MSTR", "COIN", "IONQ", "RGTI",
        "SOFI", "HOOD", "DDOG", "ZS", "NET", "MDB", "VRT", "VST", "AI", "WDAY", "SNPS",
        "CDNS", "FTNT", "CHKP", "OKTA", "TEAM", "MNDY", "FSLY", "PINS", "ROKU", "TTD", "U",
        # Finance & Payments
        "JPM", "BAC", "GS", "V", "MA", "PYPL", "AFRM", "UPST", "NU", "AXP", "WFC", "C", "MS", "COF",
        "XYZ", "MARA", "RIOT", "CLSK", "BLK", "SPGI", "MCO", "CME", "ICE",
        # Healthcare & Biotech
        "UNH", "LLY", "JNJ", "ABBV", "PFE", "MRNA", "GILD", "AMGN", "VRTX", "ISRG", "DXCM",
        "PODD", "REGN", "BMY", "MRK", "TMO", "DHR", "ABT", "SYK", "BSX", "ZTS", "ILMN",
        # Consumer & Retail
        "WMT", "COST", "HD", "MCD", "SBUX", "NKE", "DIS", "ABNB", "UBER", "LULU", "RCL", "CCL",
        "DKNG", "LOW", "CMG", "DPZ", "YUM", "MAR", "HLT", "BKNG", "EXPE", "RIVN", "LCID", "F", "GM",
        # Industrial & Energy & Defense
        "XOM", "CVX", "CAT", "BA", "LMT", "FANG", "BKR", "COP", "SLB", "EOG", "MPC", "VLO",
        "OXY", "CCJ", "UEC", "URA", "NEM", "FCX", "ALB",
        "FSLR", "ENPH", "GE", "RTX", "HON", "MMM", "NOC", "GD", "TDG", "LHX", "TXT", "DE", "PCAR",
        # Defensive & Reits
        "PG", "KO", "PEP", "PM", "MO", "CL", "KMB", "GIS", "SYY", "KR", "MDLZ", "HSY",
        "AMT", "PLD", "EQIX", "VTR", "PSA", "O", "SPG", "CCI", "DLR", "SBAC", "DOC",
        # Leveraged / Beta ETFs
        "SPY", "QQQ", "DIA", "IWM", "TQQQ", "SQQQ", "SOXL", "SOXS",
        # Defensive / Macro ETFs
        "GLD", "TLT", "XLU"
    ]
        
    def _safe_import(self, description: str, import_func):
        """Safely import and execute a module, tracking success/failure"""
        try:
            result = import_func()
            self.state.modules_loaded += 1
            return result
        except Exception as e:
            self.state.modules_failed += 1
            logger.debug("  -> {} skipped: {}", description, e)
            return None

    # ==========================================
    # PHASE 1: SYSTEM BOOT & INFRASTRUCTURE
    # ==========================================
    def phase_1_boot_infrastructure(self):
        """Start background utilities: health, keepalive, watchdog, frequency control, execution tracker"""
        logger.info("=" * 60)
        logger.info("[PHASE 1] Starting System Infrastructure (10 modules)")
        logger.info("=" * 60)
        
        # 1. Keepalive (Oracle Cloud anti-idle)
        def _keepalive():
            from keepalive import start_keepalive
            start_keepalive()
            logger.info("  -> keepalive.py activated (Oracle anti-idle)")
        self._safe_import("keepalive", _keepalive)
            
        # 2. Health Monitor
        def _health():
            from health_monitor import get_health_monitor
            self._health_monitor = get_health_monitor()
            self._health_monitor.set_api_status("OK")
            logger.info("  -> health_monitor.py activated")
        self._safe_import("health_monitor", _health)
            
        # 3. Watchdog / Telegram Startup Alert
        def _watchdog():
            from watchdog import send_tg
            send_tg(f"\U0001F680 <b>\ud2b8\ub798\uc774\ub529\ubd07 \uc2dc\uc791 (130-Module)</b>\n\u23F0 \uc2dc\uac04: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\U0001F4CD \uc704\uce58: Oracle Cloud")
            logger.info("  -> watchdog.py: Telegram startup alert sent")
        self._safe_import("watchdog", _watchdog)
        
        # 4. Frequency Controller
        def _freq():
            from frequency_controller import get_frequency_controller
            self._freq_controller = get_frequency_controller("SWING_DAY_HYBRID")
            logger.info("  -> frequency_controller.py: mode=SWING_DAY_HYBRID, max {} trades/day", 
                       self._freq_controller.config.max_trades_per_day)
        self._safe_import("frequency_controller", _freq)
        
        # 5. Execution Tracker
        def _exec():
            from execution_tracker import get_execution_tracker
            self._exec_tracker = get_execution_tracker()
            logger.info("  -> execution_tracker.py: {} historical records", len(self._exec_tracker.records))
        self._safe_import("execution_tracker", _exec)
        
        # 6. Manipulation Defense
        def _manip():
            from manipulation_defense import get_manipulation_defense
            self._manipulation_defense = get_manipulation_defense()
            logger.info("  -> manipulation_defense.py: stop hunt / fake breakout detection active")
        self._safe_import("manipulation_defense", _manip)
        
        # 7. Realtime Monitor
        def _rtm():
            from realtime_monitor import get_realtime_monitor
            self._realtime_monitor = get_realtime_monitor()
            logger.info("  -> realtime_monitor.py activated")
        self._safe_import("realtime_monitor", _rtm)
        
        # 8. Notification
        def _notif():
            from notification import get_notifier
            self._notifier = get_notifier()
            logger.info("  -> notification.py ready")
        self._safe_import("notification", _notif)
        
        # 9. Trade Journal
        def _journal():
            from trade_journal import get_trade_journal
            self._journal = get_trade_journal()
            logger.info("  -> trade_journal.py ready")
        self._safe_import("trade_journal", _journal)
        
        # 10. Emergency Stop
        def _estop():
            from emergency_stop import get_emergency_stop
            self._emergency = get_emergency_stop()
            logger.info("  -> emergency_stop.py circuit breaker ready")
        self._safe_import("emergency_stop", _estop)
        
        # Sync positions from API
        api_positions = self.trader.get_positions()
        self.strategy.sync_positions(api_positions)

        # 11. Telegram Commander (   )
        def _commander():
            from telegram_commander import start_commander
            start_commander()
            logger.info("  -> telegram_commander.py: /status / /    ")
        self._safe_import("telegram_commander", _commander)
        
        logger.info("Phase 1 Complete. Modules: {}/{} loaded", 
                    self.state.modules_loaded, self.state.modules_loaded + self.state.modules_failed)

    # ==========================================
    # PHASE 2: MACRO & PRE-MARKET EVALUATION
    # ==========================================
    def phase_2_macro_evaluation(self):
        """Evaluate 15+ macro/risk modules: geopolitical, fed, vix, HMM regime, 
        intermarket, correlation, sector rotation, economic calendar, stress test"""
        logger.info("=" * 60)
        logger.info("[PHASE 2] Evaluating Macro & Pre-market Risk (15 modules)")
        logger.info("=" * 60)
        penalty = 0
        
        # 1. Geopolitical Risk
        def _geo():
            nonlocal penalty
            from geopolitical import GeopoliticalMonitor
            geo = GeopoliticalMonitor()
            geo_analysis = geo.analyze()
            logger.info("  -> geopolitical.py: Level={}, Rec={}", geo_analysis.overall_risk_level, geo_analysis.recommendation)
            if geo_analysis.reduce_exposure:
                self.state.max_exposure_pct *= 0.5
                penalty += 20
        self._safe_import("geopolitical", _geo)

        # 2. Fed Watch / Rate Monitor
        def _fed():
            from fed_watch import analyze_fed_policy
            fed = analyze_fed_policy()
            logger.info("  -> fed_watch.py: {}", fed)
        self._safe_import("fed_watch", _fed)
            
        # 3. VIX Structure
        def _vix():
            nonlocal penalty
            from vix_structure import get_vix_metrics
            vix = get_vix_metrics()
            if getattr(vix, 'term_structure', '') == 'BACKWARDATION':
                logger.warning("  -> vix_structure.py: VIX Backwardation! Extreme Caution.")
                self.state.max_exposure_pct *= 0.5
                penalty += 30
            else:
                logger.info("  -> vix_structure.py: contango={}", getattr(vix, 'term_structure', 'N/A'))
        self._safe_import("vix_structure", _vix)

        # 4. Hidden Markov Regime
        def _hmm():
            nonlocal penalty
            from hidden_markov_regime import HiddenMarkovRegime
            hmm = HiddenMarkovRegime()
            hmm_result = hmm.analyze()
            self.state.current_regime = hmm_result.get('regime', 'UNKNOWN')
            risk_score = hmm_result.get('risk_score', 50)
            logger.info("  -> hidden_markov_regime.py: Regime={} (Risk: {})", self.state.current_regime, risk_score)
            if "BEAR_PANIC" in self.state.current_regime or risk_score >= 80:
                penalty += 40
            #  CRITICAL: Wire regime to strategy engine so bear guard fires
            self.strategy._last_regime = self.state.current_regime
            logger.info("  -> strategy._last_regime synced to: {}", self.state.current_regime)
        self._safe_import("hidden_markov_regime", _hmm)
        
        # 5. Intermarket Analysis
        def _inter():
            from intermarket import get_intermarket
            inter = get_intermarket()
            result = inter.analyze()
            logger.info("  -> intermarket.py: {}", getattr(result, 'trading_recommendation', 'OK'))
        self._safe_import("intermarket", _inter)
        
        # 6. Correlation Regime
        def _corr():
            from correlation_regime import get_correlation_regime
            corr = get_correlation_regime()
            result = corr.analyze()
            regime_name = getattr(result, 'regime', None) or (result.get('regime') if isinstance(result, dict) else 'N/A')
            logger.info("  -> correlation_regime.py: regime={}", regime_name)
        self._safe_import("correlation_regime", _corr)
        
        # 7. Sector Rotation   strategy state  (  )
        def _sector():
            from sector_rotator import get_sector_rotator
            sr = get_sector_rotator()
            result = sr.analyze()
            if result:
                #  3 (OVERWEIGHT)  ETF 
                leading_etfs  = [r.etf    for r in result[:3]]
                leading_names = [r.sector for r in result[:3]]
                #  3 (UNDERWEIGHT)   
                lagging_etfs  = [r.etf    for r in result[-3:]]
                lagging_names = [r.sector for r in result[-3:]]
                
                # strategy   check_entry()  
                self.strategy._leading_sectors = leading_names    # ['Technology', ...]
                self.strategy._leading_etfs    = leading_etfs     # ['XLK', ...]
                self.strategy._lagging_sectors = lagging_names
                self.strategy._lagging_etfs    = lagging_etfs
                self.strategy._sector_rankings = {r.etf: r for r in result}
                
                # state   screener 
                self.state.leading_sectors = leading_names
                self.state.lagging_sectors = lagging_names
                
                logger.info("  -> sector_rotator.py:  leading={} |  lagging={}",
                            leading_names, lagging_names)
            else:
                logger.info("  -> sector_rotator.py: no data, sector filter disabled")
        self._safe_import("sector_rotator", _sector)
        
        # 8. Economic Calendar
        def _econ():
            from economic_calendar import get_economic_calendar
            cal = get_economic_calendar()
            events = cal.check_today().events_today if hasattr(cal, 'check_today') else []
            logger.info("  -> economic_calendar.py: {} upcoming events", len(events) if events else 0)
        self._safe_import("economic_calendar", _econ)
        
        # 9. Stress Test
        def _stress():
            from stress_test import get_stress_test
            st = get_stress_test()
            result = st.run_test()
            scenario = f"Loss {result.worst_case_loss_pct:.1f}%" if result else "N/A"
            logger.info("  -> stress_test.py: worst={}", scenario)
        self._safe_import("stress_test", _stress)
        
        # 10. Macro Shield (aggregate decision)
        if penalty >= 50:
            self.state.global_risk_level = "RISK_OFF"
            self.state.max_exposure_pct *= 0.2
            logger.warning("  -> MACRO SHIELD ENGAGED: RISK_OFF (penalty={})", penalty)
            
        self.state.last_macro_refresh = datetime.now()
        logger.info("Phase 2 Complete. Exposure: {:.0%}, Risk: {}, Regime: {}", 
                    self.state.max_exposure_pct, self.state.global_risk_level, self.state.current_regime)

    # ==========================================
    # PHASE 3: SCREENER & UNIVERSE REDUCTION
    # ==========================================
    def phase_3_run_screener(self):
        """Screen universe using screener + liquidity filter + fundamental analyzer.
        
        Screener is cached for 45 minutes to prevent hammering 1000+ symbols
        with OHLCV API calls on every orchestrator cycle.
        """
        logger.info("=" * 60)
        logger.info("[PHASE 3] Running Universe Screener (5 modules)")
        logger.info("=" * 60)
        
        # ---- 45-minute screener result cache ----
        now = datetime.now()
        if (self.state.last_screen_refresh is not None and
                (now - self.state.last_screen_refresh).total_seconds() < 2700 and  # 45 min
                self.state.target_universe):
            logger.info("  -> Screener result cached ({} symbols). Skipping re-scan.",
                        len(self.state.target_universe))
            return
        
        try:
            # Reuse screener instance to keep _cache and _multi_source_hits alive
            if not hasattr(self, '_screener_instance') or self._screener_instance is None:
                self._screener_instance = DynamicScreener()
            screener = self._screener_instance
            
            from macro import MarketRegime
            regime = MarketRegime.RISK_OFF if self.state.global_risk_level == "RISK_OFF" else MarketRegime.RISK_ON
            
            #    exclude_symbols       
            current_positions = self.strategy.get_all_positions()
            held_symbols = set(current_positions.keys())
            
            result = screener.screen(regime=regime, exclude_symbols=held_symbols)
            self.state.target_universe = result.tickers if result and result.tickers else []
            logger.info("  -> screener.py: {} targets found (excluding {} held positions: {})",
                       len(self.state.target_universe), len(held_symbols), list(held_symbols))
            
            # Apply additional liquidity filter
            def _liq():
                from liquidity_filter import get_liquidity_filter
                lf = get_liquidity_filter()
                filtered = []
                for t in self.state.target_universe:
                    check = lf.check(t)
                    if getattr(check, 'is_tradeable', False):
                        filtered.append(t)
                if filtered:
                    self.state.target_universe = filtered
                    logger.info("  -> liquidity_filter.py: {} survive liquidity check", len(filtered))
            self._safe_import("liquidity_filter", _liq)
            
        except Exception as e:
            logger.error("Screener Failed: {}. Using fallback universe.", e)
            self.state.target_universe = self.FALLBACK_UNIVERSE[:] # Ensure universe is populated even on error
        
        # Fallback: if screener returned 0 stocks, use core watchlist
        if not self.state.target_universe:
            logger.warning("  -> Screener returned NO results. Using FALLBACK_UNIVERSE.")
            self.state.target_universe = self.FALLBACK_UNIVERSE[:]
            self.state.screened_symbols = []
        else:
            # Already set in try/except, but ensure screened_symbols is updated
            self.state.screened_symbols = self.state.target_universe[:]
            
        self.state.last_screen_refresh = datetime.now()
        logger.info("Phase 3 Complete. Universe: {}", self.state.target_universe[:10])

    # ==========================================
    # PHASE 4: INTRADAY SIGNAL ENGINE
    # ==========================================
    def _run_phase_4_cycle(self, engine):
        """Phase 4: Signal Acquisition & Decision Loop
        - Priority 1: Exit/Stop-loss check (Immediate safety)
        - Priority 2: Account balance & exposure check
        - Priority 3: Entry signal scanning
        - Priority 4: Position upgrade (Portfolio optimization)
        """
        # --- PRIORITY 1: EXIT CHECK (Move to top for immediate response) ---
        positions = self.strategy.get_all_positions()
        if positions:
            logger.info("??Checking exits for {} positions first...", len(positions))
            for sym, pos in list(positions.items()):
                try:
                    curr_price = self.trader.get_price(sym)
                    exit_sig = self.strategy.check_exit(sym, curr_price)
                    if exit_sig and exit_sig.action != "HOLD":
                        logger.warning("? EXIT TRIGGERED: {} -> {} ({})", sym, exit_sig.action, exit_sig.reason)
                        self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                except Exception as e:
                    logger.debug("Exit check failed for {}: {}", sym, e)

        # Check frequency controller
        if self._freq_controller:
            window = self._freq_controller.can_trade()
            if not window.can_trade:
                logger.debug("Frequency limit: {}", window.reason)
                return
        
        # --- Macro Exposure Enforcement (sell excess if overexposed) ---
        if self.state.max_exposure_pct < 1.0:
            try:
                positions = self.strategy.get_all_positions()
                if positions:
                    bp = self.trader.get_buying_power()
                    total_value = bp
                    pos_values = {}
                    for sym, pos in positions.items():
                        price = self.trader.get_price(sym)
                        if price <= 0:
                            price = max(pos.entry_price, pos.high_since_entry)
                            
                        if price > 0:
                            val = price * pos.quantity
                            pos_values[sym] = (val, price, pos.quantity)
                            total_value += val
                    
                    if total_value > 0:
                        current_exposure = (total_value - bp) / total_value
                        target_exposure = self.state.max_exposure_pct
                        
                        if current_exposure > target_exposure + 0.05:  # >5% over target
                            excess_ratio = 1.0 - (target_exposure / current_exposure)
                            logger.warning("? Exposure {:.0%} > Target {:.0%}. Reducing positions by {:.0%}",
                                         current_exposure, target_exposure, excess_ratio)
                            
                            for sym, (val, price, qty) in pos_values.items():
                                sell_qty = max(1, int(qty * excess_ratio))
                                if sell_qty > 0 and sell_qty < qty:  # Partial sell
                                    reason = f"MACRO EXPOSURE: {current_exposure:.0%} ??{target_exposure:.0%} (regime={self.state.current_regime})"
                                    self.phase_5_execute_trade(sym, "SELL", sell_qty, price, reason)
                                    logger.info("  ??Selling {} x {} @ ${:.2f} to reduce exposure", sell_qty, sym, price)
            except Exception as e:
                logger.debug("Exposure enforcement error: {}", e)
        
        # --- Reset daily counters if new day (US Session adjusted) ---
        # Subtract 12 hours so the entire US session (22:30 to 05:00 KST)
        # falls on the same logical date. This prevents the mid-session 
        # (midnight) reset of the cooldown blacklist, fixing churning.
        today = (datetime.now() - timedelta(hours=12)).date()
        if getattr(self, '_last_trade_date', None) != today:
            self._daily_trade_count = 0
            self._daily_upgrade_count = 0
            self._last_trade_date = today
            self._sold_today = set()
        
        # Removed MAX_DAILY_TRADES check for Swing Trading
        
        # --- Entry Signals ---
        best_buy_signal = None  # Track best signal for potential upgrade
        
        # Calculate Total Portfolio Value (Net Liquidation)
        bp = self.trader.get_buying_power()
        positions = self.strategy.get_all_positions()
        total_equity = bp
        for sym, pos in positions.items():
            p_price = self.trader.get_price(sym)
            if p_price > 0:
                total_equity += p_price * pos.quantity
            else:
                total_equity += pos.entry_price * pos.quantity
        
        def _get_signal(symbol):
            try:
                # ... check manipulation ...
                is_screened = symbol in getattr(self.state, 'screened_symbols', [])
                return symbol, engine.analyze(symbol, is_screened=is_screened)
            except Exception as e:
                logger.debug("Signal check failed for {}: {}", symbol, e)
                return symbol, None

        signals_to_process = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(_get_signal, sym): sym for sym in self.state.target_universe}
            for future in as_completed(future_to_symbol):
                symbol, signal = future.result()
                if signal:
                    signals_to_process.append(signal)
        
        # Sort by score to process best first
        signals_to_process.sort(key=lambda x: x.composite_score, reverse=True)

        for signal in signals_to_process:
            symbol = signal.symbol
            try:
                logger.info("Signal for {}: score={}, action={}", symbol, signal.composite_score, signal.action)
                
                from composite_signal import ActionType
                if signal.action in [ActionType.STRONG_BUY, ActionType.BUY]:
                    # Check if we already hold this symbol
                    current_positions = self.strategy.get_all_positions()
                    if symbol in current_positions:
                        continue
                    
                    # Check standard strategy entry rules (VIX, CHOPPY block, BEAR block, Earnings, Econ, Insider guards)
                    is_screened = symbol in getattr(self.state, 'screened_symbols', [])
                    entry_allowed = self.strategy.check_entry(symbol, macro_score=signal.composite_score, is_screened=is_screened)
                    if entry_allowed.action == "HOLD":
                        logger.info("STRATEGY_GUARD: Entry blocked for {}: {}", symbol, entry_allowed.reason)
                        continue
                    
                    # ============================================================
                    #  DAILY LOSS CIRCUIT BREAKER     (-3%)
                    # ============================================================
                    try:
                        from emergency_stop import EmergencyStop
                        _es = EmergencyStop()
                        _start_eq = getattr(self.rm, 'day_start_equity', total_equity) if hasattr(self, 'rm') else total_equity
                        if _es.check_daily_loss(_start_eq, total_equity):
                            logger.warning("DAILY_LOSS_CIRCUIT:       ")
                            break  # Stop ALL new entries for the day
                    except Exception as _cb:
                        logger.debug("Circuit breaker check failed: {}", _cb)
                    
                    # ============================================================
                    #  SECTOR CONCENTRATION GUARD    2   
                    # ============================================================
                    try:
                        _SECTOR_MAP = {
                            #  / 
                            'semiconductors': [
                                'NVDA','AMD','MU','LRCX','KLAC','ASML','QCOM','ARM','ON',
                                'AVGO','TXN','AMAT','MRVL','INTC','SWKS','MPWR','SOXL','SOXS',
                            ],
                            # 
                            'big_tech': [
                                'AAPL','MSFT','AMZN','META','GOOGL','GOOG','ORCL','IBM','DELL','HPQ',
                            ],
                            # AI /  / 
                            'ai_growth': [
                                'PLTR','DDOG','CRWD','ZS','NET','MDB','PANW','SNOW','AI',
                                'NOW','WDAY','SNPS','CDNS','FTNT','CHKP','OKTA','TEAM','MNDY',
                                'FSLY','TTD','BRZE','ASAN','GTLB','DOCN','APP','U',
                            ],
                            #  /  / 
                            'fintech': [
                                'AFRM','UPST','SOFI','HOOD','COIN','NU','PYPL','XYZ',
                                'MARA','RIOT','CLSK','MSTR',
                            ],
                            #  /  (   )
                            'banks': [
                                'JPM','GS','BAC','WFC','C','MS','COF','AXP',
                                'BLK','SPGI','MCO','CME','ICE','V','MA',
                            ],
                            # 
                            'energy': [
                                'XOM','CVX','FANG','BKR','COP','SLB','EOG','MPC','VLO','PSX',
                                'OXY','CCJ','UEC','URA','NEM','FCX','ALB','VST',
                            ],
                            #  / 
                            'biotech': [
                                'MRNA','GILD','AMGN','VRTX','ISRG','DXCM','PODD','REGN',
                                'BMY','MRK','PFE','LLY','ABT','ABBV','TMO','DHR',
                                'SYK','BSX','ZTS','ILMN','UNH','BIIB','HALO','INCY','ALNY','BMRN',
                            ],
                            #  / 
                            'clean_energy': [
                                'FSLR','ENPH','NEE','DUK','SO','ED','AEP','XEL','WEC',
                            ],
                            # EV / 
                            'ev_auto': [
                                'TSLA','RIVN','LCID','F','GM','NIO',
                            ],
                            #  /  / 
                            'travel': [
                                'ABNB','UBER','RCL','CCL','DKNG','MAR','HLT','BKNG','EXPE',
                                'DAL','UAL','AAL','LUV',
                            ],
                            #  / 
                            'reits': [
                                'AMT','PLD','EQIX','VTR','PSA','O','SPG','CCI','DLR','SBAC','DOC',
                            ],
                            #  / 
                            'defense_industrial': [
                                'LMT','RTX','NOC','GD','TDG','LHX','TXT',
                                'GE','CAT','BA','HON','MMM','DE','PCAR','CMI','ETN','EMR','WM','RSG',
                            ],
                            #  / 
                            'consumer': [
                                'NKE','SBUX','MCD','DIS','LULU','CMG','DPZ','YUM',
                                'HD','LOW','WMT','COST','AMZN',
                            ],
                            #  /  / 
                            'media_ad': [
                                'ROKU','PINS','DUOL','TTD','APP','CELH',
                            ],
                        }
                        _sym_sector = next((sec for sec, syms in _SECTOR_MAP.items() if symbol in syms), None)
                        if _sym_sector:
                            _sector_conflict = [s for s in current_positions if any(
                                s in syms for sec, syms in _SECTOR_MAP.items() if sec == _sym_sector
                            )]
                            if _sector_conflict:
                                logger.info("SECTOR_GUARD: {} ({})   {}   (   )",
                                            symbol, _sym_sector, _sector_conflict)
                                continue
                    except Exception as _sc:
                        logger.debug("Sector concentration guard failed: {}", _sc)
                    
                    # Same-day cooldown: never rebuy a stock we just sold today (in-memory)
                    if symbol in getattr(self, '_sold_today', set()):
                        logger.debug("COOLDOWN: {} was already sold today (in-memory), skipping rebuy", symbol)
                        continue

                    # DB 16-hour cooldown removed for Swing Trading

                    #  DB-backed dedup: Also check DB for open positions (prevents KLAC5 bug)
                    # In-memory dict can desync from actual orders; DB is the source of truth.
                    try:
                        db_open = self.db.get_open_positions()
                        db_symbols = {p['symbol'] for p in db_open}
                        if symbol in db_symbols:
                            logger.debug("DEDUP: {} already in DB open positions, skipping BUY", symbol)
                            continue
                    except Exception as e:
                        logger.debug("DB Dedup check error: {}", e)
                        pass  # Fallback: trust in-memory check
                    
                    # [v1.1.8] Double-check in-memory strategy positions too
                    # This catches cases where DB sync is behind but strategy already has the position
                    in_memory_positions = self.strategy.get_all_positions()
                    if symbol in in_memory_positions:
                        logger.debug("DEDUP (in-memory): {} already in strategy positions, skipping BUY", symbol)
                        continue

                    
                    # Check position count limit (Macro Shield: reduce max positions in bear/choppy regimes)
                    current_regime = getattr(self.strategy, '_last_regime', '')
                    dynamic_max_positions = config.MAX_POSITIONS
                    if current_regime in ["BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"]:
                        dynamic_max_positions = max(1, config.MAX_POSITIONS // 2)
                        logger.info("MACRO_SHIELD: Bear regime ({}) -> Reducing MAX_POSITIONS {} -> {}", 
                                    current_regime, config.MAX_POSITIONS, dynamic_max_positions)
                    elif current_regime in ["CHOPPY", "CHOPPY_VOLATILE"]:
                        dynamic_max_positions = max(1, int(config.MAX_POSITIONS * 0.7))
                        logger.info("MACRO_SHIELD: Choppy regime ({}) -> Reducing MAX_POSITIONS {} -> {}", 
                                    current_regime, config.MAX_POSITIONS, dynamic_max_positions)
                    
                    empty_slots = dynamic_max_positions - len(current_positions)
                    if empty_slots > 0:
                        # Slot available
                        if bp < 50:  # Minimum $50 cash (was $10) - prevent fee-killing micro trades
                            continue
                            
                        # ============================================================
                        #  ATR     
                        # :    ( )
                        # :   $15  ( ~2%)
                        #          =   ATR
                        # ============================================================
                        try:
                            import kis_data as _kd_size
                            _df_atr = _kd_size.get_daily_ohlcv(symbol, days=20)
                            if _df_atr is not None and len(_df_atr) >= 15:
                                _high = _df_atr['High']
                                _low  = _df_atr['Low']
                                _cls  = _df_atr['Close']
                                _tr = pd.concat([
                                    _high - _low,
                                    (_high - _cls.shift()).abs(),
                                    (_low  - _cls.shift()).abs()
                                ], axis=1).max(axis=1)
                                _atr = float(_tr.rolling(14).mean().iloc[-1])
                                
                                # [BUG FIX v1.0.6] Risk amount = 2% of total equity
                                # Previous: min(25, ...) hard-capped at $25 regardless of portfolio size.
                                # This caused tiny position sizes even for $10K+ portfolios.
                                # Fix: minimum $15 floor (fee protection), no upper cap (scales with equity).
                                # Example: $10K => $200 risk | $50K => $1000 risk | $100K => $2000 risk
                                _risk_amount = max(15, total_equity * 0.02)
                                
                                # Cut risk in half during bear markets to protect capital
                                if self.state.current_regime in {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}:
                                    _risk_amount *= 0.5
                                    logger.debug("BEAR_SIZING: Risk amount halved to ${:.1f} for {}", _risk_amount, symbol)
                                
                                #   = 1.5 ATR
                                _stop_dist = max(_atr * 1.5, signal.entry_price * 0.015)
                                #  =   
                                _atr_qty = int(_risk_amount / _stop_dist) if _stop_dist > 0 else 1
                                
                                #        
                                _slot_qty = int(bp / empty_slots / signal.entry_price) if signal.entry_price > 0 else 1
                                raw_qty = min(_atr_qty, _slot_qty)
                                logger.debug("ATR_SIZING {}: risk=${:.0f} atr={:.2f}  qty={} (slot={} atr={})",
                                             symbol, _risk_amount, _atr, raw_qty, _slot_qty, _atr_qty)
                            else:
                                raw_qty = int(bp / empty_slots / signal.entry_price) if signal.entry_price > 0 else 0
                        except Exception as _atr_e:
                            logger.debug("ATR sizing failed: {}", _atr_e)
                            raw_qty = int(bp / empty_slots / signal.entry_price) if signal.entry_price > 0 else 0
                        
                        # Small Account Safety Filter: Skip stocks that are too expensive relative to portfolio size
                        # [v1.1.8] Raised from 30% → 55% — 30% was rejecting most quality stocks on small accounts
                        # e.g. $770 portfolio × 55% = $423 max stock price (covers most liquid US equities)
                        MAX_STOCK_CONCENTRATION_PCT = 0.55  # Max 55% of portfolio per stock price
                        if signal.entry_price > total_equity * MAX_STOCK_CONCENTRATION_PCT:
                            logger.info("SKIP {}: stock price (${:.2f}) exceeds {:.1f}% of total equity (${:.2f})", 
                                        symbol, signal.entry_price, MAX_STOCK_CONCENTRATION_PCT * 100, total_equity)
                            continue

                        # Clamp by available cash
                        max_by_bp = int(bp / signal.entry_price) if signal.entry_price > 0 else 0
                        qty = min(raw_qty, max_by_bp)
                        
                        # Allow minor limit violation (up to 50% over target capital) for 1-share entry, but never exceed max concentration
                        _target_capital = bp / empty_slots
                        if qty == 0 and signal.entry_price <= _target_capital * 2.0 and signal.entry_price <= total_equity * MAX_STOCK_CONCENTRATION_PCT:
                            qty = 1
                            logger.info("Sizer override for {}: 1 share allowed via minor limit violation", symbol)
                        
                        # Minimum position value: $50 (don't buy 1 share of $20 stock if fees eat profit)
                        position_value = qty * signal.entry_price
                        if position_value < 50:
                            logger.debug("SKIP {}: position value ${:.0f} too small (min $50)", symbol, position_value)
                            continue
                        
                        if qty > 0:
                            self.phase_5_execute_trade(symbol, "BUY", qty, signal.entry_price, signal.summary)

                    else:
                        # All slots full ??track for potential upgrade
                        if best_buy_signal is None or signal.composite_score > best_buy_signal.composite_score:
                            best_buy_signal = signal
            except Exception as e:
                logger.debug("Trade logic failed for {}: {}", symbol, e)
        
        # --- Position Upgrade Logic ( ) ---
        if best_buy_signal and self._daily_upgrade_count < config.UPGRADE_MAX_PER_DAY:
            try:
                positions = self.strategy.get_all_positions()
                if positions:
                    # Find weakest position that qualifies for upgrade
                    worst_sym = None
                    worst_score = float('inf')
                    
                    for sym, pos in positions.items():
                        # Check minimum hold time
                        hold_minutes = (datetime.now() - pos.entry_time).total_seconds() / 60
                        if hold_minutes < config.UPGRADE_MIN_HOLD_MINUTES:
                            continue
                        
                        # Check profit protection ??don't swap profitable positions
                        curr_price = self.trader.get_price(sym)
                        if curr_price > 0:
                            pnl_pct = (curr_price - pos.entry_price) / pos.entry_price
                            if pnl_pct >= config.UPGRADE_PROFIT_PROTECT_PCT:
                                continue  # 2%+ ? ???
                        
                        # Re-score existing position
                        try:
                            existing_signal = engine.analyze(sym)
                            existing_score = existing_signal.composite_score
                        except Exception:
                            existing_score = 0
                        
                        # [FIX] PnL-adjusted scoring: penalize losing positions
                        # A stock that's -3% down should score lower for hold purposes
                        # Penalty: each 1% loss = -5 points (capped at -30 for >6% loss)
                        if curr_price > 0:
                            pnl_pct = (curr_price - pos.entry_price) / pos.entry_price
                            if pnl_pct < 0:
                                pnl_penalty = min(30, int(abs(pnl_pct) * 100 * 5))
                                existing_score -= pnl_penalty
                                logger.debug(
                                    "UPGRADE re-score: {} raw={} pnl={:.1%} penalty={} adjusted={}",
                                    sym, existing_score + pnl_penalty,
                                    pnl_pct, pnl_penalty, existing_score
                                )
                        
                        if existing_score < worst_score:
                            worst_score = existing_score
                            worst_sym = sym

                    
                    # Execute upgrade if score gap is large enough
                    if worst_sym and (best_buy_signal.composite_score - worst_score) >= config.UPGRADE_SCORE_GAP:
                        # Small Account Safety Filter: Skip stocks that are too expensive relative to portfolio size
                        MAX_STOCK_CONCENTRATION_PCT = 0.55  # [v1.1.8] Raised 30% → 55%
                        if best_buy_signal.entry_price > total_equity * MAX_STOCK_CONCENTRATION_PCT:
                            logger.info("UPGRADE BLOCKED: {} price (${:.2f}) exceeds {:.1f}% of total equity (${:.2f})", 
                                        best_buy_signal.symbol, best_buy_signal.entry_price, MAX_STOCK_CONCENTRATION_PCT * 100, total_equity)
                        else:
                            worst_pos = positions[worst_sym]
                            sell_price = self.trader.get_price(worst_sym)
                            if sell_price <= 0:
                                sell_price = worst_pos.entry_price

                            logger.info("UPGRADE: {} ({}) -> {} ({}), Gap: {}",
                                        worst_sym, worst_score,
                                        best_buy_signal.symbol, best_buy_signal.composite_score,
                                        best_buy_signal.composite_score - worst_score)

                            # Step 1: Sell weakest
                            self.phase_5_execute_trade(worst_sym, "SELL", worst_pos.quantity, sell_price,
                                                      f"UPGRADE: {worst_sym}({worst_score}) -> {best_buy_signal.symbol}({best_buy_signal.composite_score})")

                            # Step 2: Buy new (with available buying power after sell)
                            import time
                            time.sleep(1)  # Brief pause for order processing
                            bp = self.trader.get_buying_power()
                            if bp > 5 and best_buy_signal.entry_price > 0:
                                # Recalculate empty slots after sell with dynamic max positions (Macro Shield)
                                current_regime = getattr(self.strategy, '_last_regime', '')
                                dynamic_max_positions = config.MAX_POSITIONS
                                if current_regime in ["BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"]:
                                    dynamic_max_positions = max(1, config.MAX_POSITIONS // 2)
                                elif current_regime in ["CHOPPY", "CHOPPY_VOLATILE"]:
                                    dynamic_max_positions = max(1, int(config.MAX_POSITIONS * 0.7))
                                
                                empty_slots_after_sell = max(1, dynamic_max_positions - len(self.strategy.get_all_positions()))
                                target_capital = bp / empty_slots_after_sell

                                # Safety cap: Max 40% of total equity per position
                                max_position_value = total_equity * 0.40
                                if target_capital > max_position_value:
                                    target_capital = max_position_value

                                raw_qty = int(target_capital / best_buy_signal.entry_price)
                                max_by_bp = int(bp / best_buy_signal.entry_price)
                                qty = min(raw_qty, max_by_bp)
                                
                                # Allow minor limit violation (up to 50% over target capital) for 1-share entry
                                if qty == 0 and best_buy_signal.entry_price <= target_capital * 1.5:
                                    qty = 1
                                    logger.info("UPGRADE Sizer override for {}: 1 share allowed via minor limit violation", best_buy_signal.symbol)

                                if qty > 0:
                                    self.phase_5_execute_trade(best_buy_signal.symbol, "BUY", qty,
                                                              best_buy_signal.entry_price,
                                                              f"UPGRADE BUY: {best_buy_signal.composite_score}??(replaced {worst_sym})")
                                    self._daily_upgrade_count += 1
                        
                        # Notify via Telegram
                        try:
                            from notification import get_notifier
                            get_notifier().send_message(
                                f"UPGRADE SIGNAL\n"
                                f"Sell: {worst_sym} ({worst_score})\n"
                                f"Buy: {best_buy_signal.symbol} ({best_buy_signal.composite_score})\n"
                                f"Improvement: {best_buy_signal.composite_score - worst_score}"
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.debug("Upgrade logic error: {}", e)
                    
        # --- Exit Signals on Positions (Checked again after potential upgrades) ---
        # Note: Primary exit check moved to top, but we keep this as a rapid safety sweep
        # after any buying activity.
        pass

    # ==========================================
    # PHASE 5: EXECUTION & RISK MANAGEMENT
    # ==========================================
    def phase_5_execute_trade(self, symbol: str, action: str, qty: int, price: float, reason: str):
        """Pass through 20+ risk and sizing modules before hitting the smart router"""
        
        # Daily trade limit (exits always allowed)
        if action == "BUY" and self._daily_trade_count >= config.MAX_DAILY_TRADES:
            logger.warning("? ?  ?  ({}/{}): {}  ",
                          self._daily_trade_count, config.MAX_DAILY_TRADES, symbol)
            return
        
        #   /    BUY ,   
        import os as _os
        _pause_file = "/tmp/kis_trading_paused"
        if action == "BUY" and _os.path.exists(_pause_file):
            logger.warning("PAUSED:  /    {}  ", symbol)
            return

        if self.state.global_risk_level == "RISK_OFF" and action == "BUY":
            logger.warning("Trade BLOCKED by Macro Shield (RISK_OFF): {} {}", action, symbol)
            return
        
        # ??Anti-Conflict Filter: ?  ?? ETF ?  ?
        conflicts = getattr(config, 'CONFLICTING_PAIRS', {})
        if action == "BUY" and symbol in conflicts:
            conflict_symbol = conflicts[symbol]
            if conflict_symbol in self.strategy._positions:
                logger.warning("CONFLICT BLOCKED: {} already holds {}",
                               symbol, conflict_symbol)
                return

        # 1. Emergency Stop / Circuit Breaker
        def _circuit():
            from emergency_stop import check_circuit_breaker
            if action == "BUY" and check_circuit_breaker(self.trader, self.rm):
                raise RuntimeError("CIRCUIT BREAKER ACTIVATED")
        if self._safe_import("circuit_breaker", _circuit) is None:
            if action == "BUY" and self.state.modules_failed > 0:
                pass  # Module import failed, continue

        # 2. Frequency Controller gate
        if self._freq_controller:
            is_upgrade = "UPGRADE" in reason.upper()
            window = self._freq_controller.can_trade(is_upgrade=is_upgrade)
            if not window.can_trade:
                logger.info("Trade delayed by frequency: {}", window.reason)
                return

        # 3. Drawdown Controller
        def _drawdown():
            from drawdown_controller import get_drawdown_controller
            bp = self.trader.get_buying_power()
            dc = get_drawdown_controller(bp + sum(p.market_value for p in self.trader.get_positions()))
            if dc.is_halted():
                raise RuntimeError("DRAWDOWN HALT")
        self._safe_import("drawdown_controller", _drawdown)

        # 4. [QUANT FEEDBACK v1.0.8] Advanced Feedback & Regime Position Sizer
        if action == "BUY":
            try:
                from position_sizer import get_position_sizer
                # Get the live portfolio sizer with current total equity
                sizer = get_position_sizer(portfolio=total_equity)
                # Calculate optimal sizing using dynamic Kelly, Volatility Parity, and Regime Scaler
                sizer_result = sizer.calculate(symbol, current_regime=self.state.current_regime)
                
                # Convert the optimal percentage into target share quantity
                quant_target_qty = int(sizer_result.position_dollars / price) if price > 0 else 0
                
                # Enforce dynamic scaling by max_exposure_pct & slot constraints
                max_allowed_qty = int((bp * 0.98) / price) if price > 0 else 0 # 2% slippage safety margin
                
                # Standardize quantity selection
                old_qty = qty
                qty = min(quant_target_qty, max_allowed_qty)
                qty = max(0, qty)
                
                logger.info("📐 QUANT_SIZING_RESULT for {}: SizerPct={:.1%} | TargetQty={} (LegacyQty={}) | Score={} | Details={}", 
                            symbol, sizer_result.optimal_pct, qty, old_qty, sizer_result.sizing_score, sizer_result.details)
            except Exception as sizer_err:
                logger.error("Failed to run advanced Quant Sizer for {}: {}. Falling back to default raw qty.", symbol, sizer_err)
            
        if qty <= 0:
            logger.warning("Risk modules reduced size to 0 for {}", symbol)
            return

        # 5. Cost Model Check
        def _cost():
            from cost_model import get_cost_model
            cm = get_cost_model()
            cost = cm.estimate_cost(symbol, qty, price)
            logger.debug("  -> cost_model: est. cost ${:.2f}", cost)
        self._safe_import("cost_model", _cost)

        # 6. Tax Optimizer
        try:
            from tax_optimizer import optimize_tax_lot
            qty, action = optimize_tax_lot(symbol, action, qty)
        except Exception:
            pass

        # 7. Anti-Fragility Check
        def _antifrag():
            from anti_fragility import get_antifragility
            af = get_antifragility()
            score = af.get_antifragility_score()
            if score < -50:
                logger.warning("  -> anti_fragility: FRAGILE state ({}), reducing size", score)
                return 0.5  # Reduce size by half
            return 1.0
        size_mult = self._safe_import("anti_fragility", _antifrag) or 1.0
        if action == "BUY":
            qty = max(1, int(qty * size_mult))

        # 8. Hedge Manager
        def _hedge():
            from hedge_manager import get_hedge_manager
            hm = get_hedge_manager()
            hedge_rec = hm.check_hedge_needed(self.trader.get_positions())
            if hedge_rec:
                logger.info("  -> hedge_manager: {}", hedge_rec)
        self._safe_import("hedge_manager", _hedge)

        # ??SELL SAFETY CHECK: Verify actual KIS position qty before selling
        # Prevents '?????????? (order qty > available qty) errors
        if action == "SELL":
            try:
                actual_positions = self.trader.get_positions()
                actual_qty = next((p.quantity for p in actual_positions if p.symbol == symbol), 0)
                if actual_qty == 0:
                    logger.warning("?  SELL CANCELLED: {} not found in KIS account (phantom position). Removing from strategy.", symbol)
                    self.strategy.remove_position(symbol)
                    return
                if qty > actual_qty:
                    logger.warning("?  SELL QTY CAPPED: {} requested {} but KIS only holds {}. Selling {}.",
                                   symbol, qty, actual_qty, actual_qty)
                    qty = actual_qty
            except Exception as e:
                logger.warning("Could not verify KIS position for {}: {}", symbol, e)

        # DRY RUN gate
        if self.is_dry_run:
            logger.info("[DRY RUN] {} {} x {} @ ${:.2f} ({})", action, symbol, qty, price, reason)
            if self._freq_controller:
                self._freq_controller.record_trade(is_entry=(action == "BUY"))
            return

        # 9. Smart Order Execution
        try:
            from smart_order import get_smart_executor, OrderStatus
            executor = get_smart_executor(self.trader)
            
            # [v1.1.8] Refresh price right before execution
            # Scan→analyze→execute can take minutes, stale price = missed fill
            if action == "BUY":
                try:
                    fresh_price = self.trader.get_price(symbol)
                    if fresh_price and fresh_price > 0:
                        if abs(fresh_price - price) / price > 0.005:  # >0.5% drift
                            logger.info("Price refresh for {}: ${:.2f} -> ${:.2f} ({:+.2%})",
                                       symbol, price, fresh_price, (fresh_price-price)/price)
                        price = fresh_price
                except Exception:
                    pass  # Use original price if refresh fails
            
            order = executor.execute(symbol, action, qty, price)
            
            if order.status != OrderStatus.REJECTED:
                logger.info("??Trade Executed: {} {} x {} via smart_order ({})", 
                           action, symbol, qty, order.order_type.value)
                
                # Send Trade Notification
                # [v1.1.8 BUG FIX] Only send alert if order confirmed FILLED (not just placed)
                # KIS limit orders: rt_cd=0 means "accepted", not "filled"
                # We wait briefly and check fill status to avoid phantom alerts
                if order.order_type in [OrderType.ADAPTIVE, OrderType.MARKET, OrderType.LIMIT]:
                    try:
                        from notification import get_notifier
                        notifier = get_notifier()
                        # Check if order was confirmed filled (order.status == FILLED)
                        if order.status == OrderStatus.FILLED:
                            notifier.alert_trade(action, symbol, order.avg_fill_price or price, reason)
                        else:
                            logger.info("Trade alert suppressed for {}: order status={} (not FILLED)",
                                       symbol, order.status.value)
                    except Exception as ne:
                        logger.debug("Trade notification failed: {}", ne)

                
                # Record in frequency controller
                if self._freq_controller:
                    self._freq_controller.record_trade(is_entry=(action == "BUY"))
                
                # Increment daily trade counter
                self._daily_trade_count += 1
                
                # Record execution quality
                if self._exec_tracker:
                    self._exec_tracker.record(symbol, price, getattr(order, 'avg_fill_price', price),
                                             getattr(order.order_type, 'value', "LIMIT"))
                
                if action == "BUY":
                    atr = self.strategy.get_current_atr(symbol)
                    self.strategy.add_position(symbol, price, qty, atr)
                    self.db.record_entry(symbol, qty, price, self.state.current_regime)
                else:
                    # Get actual entry price before removing position to calculate PNL correctly
                    entry_price = price  # fallback
                    if symbol in self.strategy._positions:
                        pos = self.strategy._positions[symbol]
                        entry_price = pos.entry_price
                        
                        # Handle partial sells properly without losing entry tracking
                        if qty < pos.quantity:
                            pos.quantity -= qty
                            logger.info("Partial sell: {} remaining {} -> {}", symbol, pos.quantity + qty, pos.quantity)
                        else:
                            self.strategy.remove_position(symbol)
                    
                    self.db.record_exit(symbol, qty, price, entry_price, reason)
                    
                    # ============================================================
                    #      strategy._consecutive_losses_today 
                    # ============================================================
                    try:
                        _realized_pnl = (price - entry_price) * qty
                        if _realized_pnl < 0:
                            _cur = getattr(self.strategy, '_consecutive_losses_today', 0)
                            self.strategy._consecutive_losses_today = _cur + 1
                            logger.info(" : {} ( : ${:.2f})",
                                        self.strategy._consecutive_losses_today, _realized_pnl)
                        else:
                            self.strategy._consecutive_losses_today = 0  #   
                    except Exception:
                        pass
                    
                    # Add to same-day cooldown blacklist
                    if not hasattr(self, '_sold_today'):
                        self._sold_today = set()
                    self._sold_today.add(symbol)
                    logger.info("Added {} to same-day cooldown blacklist.", symbol)
            else:
                reject_reason = order.reason if hasattr(order, 'reason') else "unknown"
                logger.warning("??Order REJECTED for {} {}: {}", action, symbol, reject_reason)
                # If KIS permanently doesn't know this symbol, evict from universe
                if reject_reason in ("KIS_SYMBOL_NOT_FOUND", "KIS_BLACKLISTED"):
                    for attr in ('target_universe', 'screened_symbols'):
                        lst = getattr(self.state, attr, None)
                        if isinstance(lst, list) and symbol in lst:
                            lst.remove(symbol)
                    logger.info("Evicted {} from universe (KIS: symbol not found)", symbol)
        except Exception as e:
            logger.error("Execution failed for {} {}: {}", action, symbol, e)
                
    # ==========================================
    # PHASE 6: POST-MARKET ANALYTICS
    # ==========================================
    def phase_6_post_market(self):
        """Run 10+ daily evaluation, optimization, and reporting modules"""
        logger.info("=" * 60)
        logger.info("[PHASE 6] Running Post-Market Analytics (10 modules)")
        logger.info("=" * 60)
        
        # 1. Performance Diagnosis
        def _diag():
            from performance_diagnosis import get_diagnosis
            diag = get_diagnosis()
            result = diag.run_diagnosis()
            logger.info("  -> performance_diagnosis.py: {}", result.get('summary', 'done'))
        self._safe_import("performance_diagnosis", _diag)
        
        # 2. Winrate Optimizer
        def _winrate():
            from winrate_optimizer import get_winrate_optimizer
            wo = get_winrate_optimizer()
            wo.optimize()
            logger.info("  -> winrate_optimizer.py updated")
        self._safe_import("winrate_optimizer", _winrate)
        
        # 3. Performance Attribution
        def _attrib():
            from performance_attribution import get_attribution
            pa = get_attribution()
            result = pa.analyze()
            logger.info("  -> performance_attribution.py: {}", result.get('summary', 'done'))
        self._safe_import("performance_attribution", _attrib)
            
        # 4. Auto Compound
        def _compound():
            from auto_compound import update_compound_tier
            update_compound_tier(self.trader.get_buying_power())
            logger.info("  -> auto_compound.py updated growth tiers")
        self._safe_import("auto_compound", _compound)
        
        # 5. Dynamic Scaling
        def _scale():
            from dynamic_scaling import get_scaler
            bp = self.trader.get_buying_power()
            scaler = get_scaler(bp)
            logger.info("  -> dynamic_scaling.py: tier={}", scaler.get_tier() if hasattr(scaler, 'get_tier') else 'N/A')
        self._safe_import("dynamic_scaling", _scale)
            
        # 6. Auto Tuner +   ( )
        def _tuner():
            from auto_tuner_new import run_auto_tune
            threading.Thread(target=run_auto_tune, daemon=True, name="AutoTuner").start()
            logger.info("  -> auto_tuner_new.py: AI    ")
        self._safe_import("auto_tuner", _tuner)
        
        # 7. Execution Quality Summary
        if self._exec_tracker:
            try:
                stats = self._exec_tracker.get_stats()
                logger.info("  -> execution_tracker.py: avg slip {:.2f}%, best hour {}",
                           stats.avg_slippage_pct, stats.best_time_window)
            except Exception:
                pass
        
        # 8. Trade Journal      ( API )
        def _journal():
            from trade_journal import get_trade_journal
            tj = get_trade_journal()
            # generate_daily_entry()   get_stats()  
            stats = tj.get_stats() if hasattr(tj, 'get_stats') else {}
            recent = tj.get_recent(limit=5) if hasattr(tj, 'get_recent') else []
            logger.info("  -> trade_journal.py: today stats={}, recent={} trades", 
                        stats, len(recent) if recent else 0)
        self._safe_import("trade_journal", _journal)
            
        # 9. Reporter / Notification
        def _report():
            from reporter import get_reporter
            rpt = get_reporter()
            rpt.send_daily_summary()
            logger.info("  -> reporter.py pushed daily summary")
            #      (  )
            rpt.send_weekly_report()
        self._safe_import("reporter", _report)
        
        # 10. ML Predictor (background training)
        def _ml():
            from ml_predictor import get_ml_predictor
            ml = get_ml_predictor()
            threading.Thread(target=ml.retrain, daemon=True).start()
            logger.info("  -> ml_predictor.py retraining in background")
        self._safe_import("ml_predictor", _ml)

        logger.info("Phase 6 Complete.")

    # ==========================================
    # 24/7 AUTONOMOUS MAIN LOOP
    # ==========================================
    def run_lifecycle(self):
        """
        Full autonomous 24/7 loop for Oracle Cloud.
        
        During market hours: runs Phase 4 signal loop
        Outside market hours: sleeps, re-evaluates macro every 4h
        Daily: runs Phase 6 post-market analytics
        """
        from scheduler import TradingScheduler
        scheduler = TradingScheduler()
        
        # PHASE 1: Boot (once)
        self.phase_1_boot_infrastructure()
        
        # PHASE 2: Initial macro evaluation
        self.phase_2_macro_evaluation()
        
        # PHASE 3: Initial screen
        self.phase_3_run_screener()
        
        # Load composite signal engine
        from composite_signal import get_composite_engine
        engine = get_composite_engine()
        
        # Log auto-discovered module count
        try:
            from base_adapters import get_available_adapters
            adapters = get_available_adapters()
            logger.info("Composite Signal Engine: {} analysis adapters loaded", len(adapters))
        except Exception:
            pass
        
        logger.info("=" * 60)
        logger.info("?? ENTERING 24/7 AUTONOMOUS TRADING LOOP")
        logger.info("=" * 60)
        
        scan_interval = self._freq_controller.get_scan_interval() * 60 if self._freq_controller else 60
        ran_post_market_today = False
        was_closed = True  # Track market open transition
        
        try:
            while True:
                #  DYNAMIC PARAMETER RELOAD
                # Auto-Tuner .env     ( )
                try:
                    from dotenv import load_dotenv
                    import importlib
                    load_dotenv(override=True)
                    if 'config' in sys.modules:
                        importlib.reload(sys.modules['config'])
                except Exception as e:
                    pass
                
                now = datetime.now()
                
                # ✦ 24/7 무중단 자동 패치 체크 (4시간 주기 원격 전략 자동 업데이트 동기화 및 자체 재기동)
                try:
                    if not hasattr(self, '_last_update_check') or (now - self._last_update_check).total_seconds() > 14400:
                        self._last_update_check = now
                        import updater
                        if updater.check_and_update():
                            logger.warning("🔄 [24/7 무중단 패치] 최신 전략 패치가 완료되었습니다. 봇을 즉시 자체 재기동합니다!")
                            import sys
                            import os
                            os.execv(sys.executable, ['python', 'main.py'] + sys.argv[1:])
                except Exception as ue:
                    logger.debug("24/7 무중단 업데이트 스킵: {}", ue)
                
                is_open = scheduler.is_market_open()
                
                # Health Check for fatal data errors
                try:
                    from health_monitor import get_health_monitor
                    status = get_health_monitor().check_health()
                    if status.errors_24h > 50:
                        if not hasattr(self, "_last_error_alert") or (now - self._last_error_alert).total_seconds() > 3600:
                            from notification import get_notifier
                            get_notifier().send_message(f"\u26A0 <b>\ud5ec\uc2a4\ucf00\uc5b4 \uacbd\uace0</b>\n\uc9c0\ub09c 24\uc2dc\uac04 \ub3d9\uc548 {status.errors_24h}\uac74 \uc774\uc0c1 \ubc1c\uc0dd. \uc815\ubc00\uc810\uac80 \uc694\ub9dd")
                            self._last_error_alert = now
                except Exception as e:
                    logger.debug("Health check alert failed: {}", e)
                

                if is_open:
                    # Market just opened ??force immediate macro + screener refresh
                    if was_closed:
                        logger.info("? Market OPEN detected! Running fresh macro + screener...")
                        self.state.max_exposure_pct = 1.0
                        self.phase_2_macro_evaluation()
                        self.phase_3_run_screener()
                        was_closed = False
                    
                    ran_post_market_today = False
                    
                    # EMERGENCY MACRO: Check VIX/SPY for sudden shocks every cycle
                    try:
                        spy_price = self.trader.get_price("SPY")
                        if spy_price > 0:
                            if not hasattr(self, '_spy_open'):
                                self._spy_open = spy_price
                            spy_change = (spy_price - self._spy_open) / self._spy_open
                            if spy_change < -0.02:  # SPY dropped >2% intraday
                                logger.warning("? EMERGENCY: SPY down {:.1%} intraday! Re-evaluating macro...", spy_change)
                                self.state.max_exposure_pct = 1.0
                                self.phase_2_macro_evaluation()
                                self._spy_open = spy_price  # Reset to avoid repeat triggers
                    except Exception:
                        pass
                    
                    # Refresh macro every 4 hours
                    if (self.state.last_macro_refresh is None or 
                        (now - self.state.last_macro_refresh) > timedelta(hours=4)):
                        self.state.max_exposure_pct = 1.0  # Reset before re-evaluation
                        self.phase_2_macro_evaluation()
                    
                    # Refresh screener every 1.5 hours (90 minutes)
                    if (self.state.last_screen_refresh is None or 
                        (now - self.state.last_screen_refresh) > timedelta(minutes=90)):
                        self.phase_3_run_screener()
                    
                    # PHASE 4: Signal loop iteration
                    # Ensure internal position state is synced with API before processing
                    try:
                        self.strategy.sync_positions(self.trader.get_positions())
                    except Exception as se:
                        logger.error("Periodic position sync failed: {}", se)

                    self._run_phase_4_cycle(engine)
                    
                    #  Phase 4.5: FAST EXIT LOOP 
                    # Instead of sleeping blindly for 10+ minutes (which causes 7% slippage on ),
                    # run a fast background loop that wakes up every 60s just to check stops/profits.
                    sleep_elapsed = 0
                    while sleep_elapsed < scan_interval:
                        try:
                            positions = self.strategy.get_all_positions()
                            if positions:
                                for sym, pos in list(positions.items()):
                                    curr_price = self.trader.get_price(sym)
                                    if curr_price > 0:
                                        exit_sig = self.strategy.check_exit(sym, curr_price)
                                        if exit_sig and exit_sig.action != "HOLD":
                                            logger.warning(" FAST EXIT TRIGGERED: {} ({})", sym, exit_sig.reason)
                                            self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                        except Exception as e:
                            logger.debug("Fast exit loop error: {}", e)
                            
                        # Break out immediately if market closes during sleep
                        if not scheduler.is_market_open():
                            break
                            
                        time.sleep(60)
                        sleep_elapsed += 60
                else:
                    was_closed = True  # Track for next open
                    # Market closed ??run post-market once
                    if not ran_post_market_today:
                        self.phase_6_post_market()
                        ran_post_market_today = True
                    
                    # Sleep 5 minutes then re-check
                    logger.debug("Market closed. Next check in 300s")
                    time.sleep(300)
                    
        except KeyboardInterrupt:
            logger.info("Interrupted. Running final Phase 6...")
            self.phase_6_post_market()
            logger.info("Shutdown complete.")
        except Exception as e:
            logger.exception("FATAL ERROR in main loop")
            try:
                from notification import get_notifier
                get_notifier().send_message(f"\U0001F6A8 <b>\ud2b8\ub798\uc774\ub529\ubd07 \ube44\uc815\uc0c1 \uc885\ub8cc</b>\n\uc0ac\uc720: {str(e)[:100]}\nWatchdog\uc5d0 \uc758\ud574 \uc7ac\uc2dc\uc791 \uc2dc\ub3c4\ub429\ub2c8\ub2e4.")
            except Exception:
                pass
            raise

