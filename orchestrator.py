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
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, TimeoutError as FuturesTimeoutError
from loguru import logger
from datetime import datetime, timedelta
import sys
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

_orchestrator_instance = None

def get_orchestrator():
    global _orchestrator_instance
    return _orchestrator_instance

class BotOrchestrator:
    def __init__(self, trader: Trader, strategy: StrategyEngine, rm: RiskManager, db: TradeDatabase, is_dry_run: bool = False):
        global _orchestrator_instance
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
        self._recently_sold = {}  # symbol -> datetime of sale
        
        _orchestrator_instance = self
        logger.info("BotOrchestrator Booting... Initializing 130-Module Lifecycle")
        
    def update_and_save_status(self):
        try:
            import os
            import json
            bp = self.trader.get_buying_power()
            positions = self.strategy.get_all_positions()
            total_equity = bp
            for sym, pos in positions.items():
                p_price = self.trader.get_price(sym)
                if p_price > 0:
                    total_equity += p_price * pos.quantity
                else:
                    total_equity += pos.entry_price * pos.quantity
            
            status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_status.json")
            status_data = {
                "total_equity": total_equity,
                "cash": bp,
                "regime": self.state.current_regime,
                "updated_at": datetime.now().isoformat()
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            logger.info("Saved bot status: Equity=${:.2f}, Regime={}", total_equity, self.state.current_regime)
            
            # Update drawdown controller state with latest total equity
            try:
                from drawdown_controller import get_drawdown_controller
                dc = get_drawdown_controller(total_equity)
                dc.update_capital(total_equity)
            except Exception as dc_err:
                logger.error("Failed to update drawdown controller: {}", dc_err)
        except Exception as e:
            logger.error("Failed to save bot status: {}", e)
    
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
            # [Fail-Safe Audit] 리스크에 민감한 핵심 매크로 모듈 에러 시 강제 락다운 트리거
            critical_risk_modules = ["geopolitical", "vix_structure", "hidden_markov_regime", "macro_news_analyzer", "macro"]
            if description in critical_risk_modules:
                logger.error("🚨 CRITICAL RISK MODULE FAILED: {}! Engaging Fail-Safe RISK_OFF Lockdown. Error: {}", description, e)
                self.state.global_risk_level = "RISK_OFF"
                self.state.max_exposure_pct = 0.2
                try:
                    from watchdog import send_tg
                    send_tg(
                        f"🚨 <b>시스템 긴급 리스크 락다운 발동!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"• 장애 모듈: <code>{description}</code>\n"
                        f"• 에러내용: {str(e)[:150]}\n"
                        f"• 결과: 강제 <b>RISK_OFF</b> 봉인 (최대 비중 20% 제한)"
                    )
                except Exception:
                    pass
            else:
                logger.warning("⚠️ Non-critical module failed/skipped: {}. Error: {}", description, e)
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
        # 10. Macro News Sentiment with Quant Feedback Loop (VIX scaling)
        def _news():
            nonlocal penalty
            try:
                from macro_news_analyzer import MacroNewsAnalyzer
                mna = MacroNewsAnalyzer()
                news_result = mna.analyze()
                raw_penalty = news_result.get("penalty", 0)
                
                # [Quant Feedback Loop] 뉴스 영향력을 실제 시장 가격 지표 반응으로 2차 필터링 및 보정
                # 진짜 영향력 있는 뉴스라면 이미 VIX나 SPY 가격 움직임에 반영되었을 것임
                # 상승장(BULL) 레짐일 때는 뉴스 페널티를 최대 15로 제한하여 단독으로 RISK_OFF를 유발하지 못하도록 함
                is_bull_regime = self.state.current_regime in {"BULL_TRENDING", "BULL_VOLATILE"}
                
                vix_factor = 1.0
                try:
                    vix_price = self.trader.get_price("^VIX")
                    if vix_price > 0:
                        # VIX가 20 이상으로 높으면 공포 증폭(페널티 1.3배), 15 이하로 극도로 안정적이면 노이즈 처리(페널티 0.6배)
                        if vix_price > 20.0:
                            vix_factor = 1.3
                        elif vix_price < 15.0:
                            vix_factor = 0.6
                except Exception:
                    pass
                
                adjusted_penalty = int(raw_penalty * vix_factor)
                if is_bull_regime:
                    adjusted_penalty = min(15, adjusted_penalty)
                    logger.info("[MACRO_NEWS] Bull regime detected. Capping news penalty to 15 to prevent false RISK_OFF.")
                    
                logger.info("  -> macro_news_analyzer.py: Level={}, Penalty={}(raw={}), Identified={}",
                            news_result.get("risk_level"), adjusted_penalty, raw_penalty, news_result.get("events_identified"))
                penalty += adjusted_penalty
            except Exception as ne:
                logger.debug("Macro news sentiment analysis failed: {}", ne)
        self._safe_import("macro_news_analyzer", _news)
        
        # 10. Macro Shield (aggregate decision)
        prev_risk_level = self.state.global_risk_level
        if penalty >= 50:
            self.state.global_risk_level = "RISK_OFF"
            self.state.max_exposure_pct *= 0.2
            logger.warning("  -> MACRO SHIELD ENGAGED: RISK_OFF (penalty={})", penalty)
            if prev_risk_level != "RISK_OFF":
                try:
                    spy_price = self.trader.get_price("SPY")
                    self.db.record_macro_decision(
                        risk_level="RISK_OFF",
                        penalty=penalty,
                        reason=f"Orchestrator penalty threshold hit: {penalty}",
                        spy_price=spy_price if spy_price > 0 else None
                    )
                    logger.info("[MACRO_SHIELD] Recorded RISK_OFF decision to DB. SPY: {}", spy_price)
                except Exception as db_err:
                    logger.warning("[MACRO_SHIELD] Failed to record macro decision: {}", db_err)

                try:
                    from watchdog import send_tg
                    send_tg(
                        f"🚨 <b>매크로 리스크 경보 작동 (RISK_OFF)</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"• 뉴스 감지 페널티: {penalty}점\n"
                        f"• 결과: 비중 제한 강제 축소 ({self.state.max_exposure_pct:.0%})\n"
                        f"• 감시 레짐: {self.state.current_regime}"
                    )
                except Exception:
                    pass
        else:
            if prev_risk_level == "RISK_OFF":
                self.state.global_risk_level = "NORMAL"
                try:
                    from watchdog import send_tg
                    send_tg(
                        f"✅ <b>매크로 리스크 경보 해제 (NORMAL)</b>\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"• 뉴스 감지 페널티: {penalty}점\n"
                        f"• 결과: 정상 투자 비중 한도 복구"
                    )
                except Exception:
                    pass
            
        self.state.last_macro_refresh = datetime.now()
        logger.info("Phase 2 Complete. Exposure: {:.0%}, Risk: {}, Regime: {}", 
                    self.state.max_exposure_pct, self.state.global_risk_level, self.state.current_regime)
        self.update_and_save_status()

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
        
        # ---- Dynamic screener result cache ----
        now = datetime.now()
        cache_seconds = getattr(config, 'SCREENER_CACHE_MINUTES', 15) * 60
        if (self.state.last_screen_refresh is not None and
                (now - self.state.last_screen_refresh).total_seconds() < cache_seconds and
                self.state.target_universe):
            logger.info("  -> Screener result cached ({} symbols, cache: {}s). Skipping re-scan.",
                        len(self.state.target_universe), cache_seconds)
            return
        
        try:
            # Reuse screener instance to keep _cache and _multi_source_hits alive
            if not hasattr(self, '_screener_instance') or self._screener_instance is None:
                self._screener_instance = DynamicScreener()
            screener = self._screener_instance
            
            from macro import MarketRegime
            regime = MarketRegime.RISK_OFF if self.state.global_risk_level == "RISK_OFF" else MarketRegime.RISK_ON
            
            # Exclude currently held symbols + recently sold symbols (within 4-hour cooldown)
            current_positions = self.strategy.get_all_positions()
            held_symbols = set(current_positions.keys())
            
            cooldown_period = timedelta(hours=4)
            recently_sold_exclude = {
                sym for sym, sold_time in getattr(self, '_recently_sold', {}).items()
                if datetime.now() - sold_time < cooldown_period
            }
            exclude_symbols = held_symbols | recently_sold_exclude
            if recently_sold_exclude:
                logger.info("Excluding recently sold symbols from screener: {}", recently_sold_exclude)
            
            result = screener.screen(regime=regime, exclude_symbols=exclude_symbols)
            self.state.target_universe = result.tickers if result and result.tickers else []
            
            # [Bear Market Inverse Hedging] 하락장 또는 RISK_OFF 시 인버스 ETF(SQQQ) 강제 진입 유니버스 주입
            is_bear_regime = self.state.current_regime in {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE", "BEAR_PANIC"}
            is_risk_off = self.state.global_risk_level == "RISK_OFF"
            if (is_bear_regime or is_risk_off) and "SQQQ" not in held_symbols:
                if not self.state.target_universe:
                    self.state.target_universe = []
                if "SQQQ" not in self.state.target_universe:
                    self.state.target_universe.append("SQQQ")
                    logger.info("🐻 BEAR MARKET / RISK_OFF detected. Forcing SQQQ into target universe for hedging.")
                    
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
            logger.error("🚨 Screener Failed: {}. Halting new entries to prevent random purchases.", e)
            self.state.target_universe = [] # [Fail-Safe] 스크리너 장애 시 임의 매수 방지를 위해 진입 유니버스 완전 동결
            self.state.screened_symbols = []
            try:
                from watchdog import send_tg
                send_tg(
                    f"🚨 <b>스크리너 작동 장애 (진입 완전 동결)</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"• 에러내용: {str(e)[:150]}\n"
                    f"• 결과: 포트폴리오 보호를 위한 <b>신규 매수 완전 차단</b>"
                )
            except Exception:
                pass
        
        # Fallback: if screener returned 0 stocks, keep it empty to protect portfolio
        if not self.state.target_universe:
            logger.warning("⚠️ Screener returned NO results. Halting new entries for safety.")
            self.state.target_universe = []
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
                        logger.warning("🚨 EXIT TRIGGERED: {} -> {} ({})", sym, exit_sig.action, exit_sig.reason)
                        if exit_sig.action == "SELL_HALF":
                            sell_qty = max(1, pos.quantity // 2)
                            if sell_qty >= pos.quantity:
                                logger.info("Only {} share(s) held for {}. Upgrading SELL_HALF to SELL_ALL.", pos.quantity, sym)
                                self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                                self.strategy.remove_position(sym)
                            else:
                                self.phase_5_execute_trade(sym, "SELL", sell_qty, exit_sig.price, exit_sig.reason)
                                self.strategy.mark_half_sold(sym)
                        else:
                            self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                            self.strategy.remove_position(sym)
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
        
        self.update_and_save_status()
        
        def _get_signal(symbol):
            try:
                # ... check manipulation ...
                is_screened = symbol in getattr(self.state, 'screened_symbols', [])
                return symbol, engine.analyze(symbol, is_screened=is_screened)
            except Exception as e:
                logger.debug("Signal check failed for {}: {}", symbol, e)
                return symbol, None

        signals_to_process = []
        try:
            # PARALLEL processing (max_workers=5, timeout=480s):
            # - 2 CPUs on VPS, analyzers are mostly I/O-bound (network calls to Finnhub/KIS).
            # - 5 symbols × 8 category workers = ~40 threads max, mostly blocking on network.
            # - 10 symbols in 2 batches (5+5) instead of 4 batches (3+3+3+1) = faster overall.
            # - Timeout increased 360→480s: last 2 symbols were consistently hitting 360s limit.
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_symbol = {executor.submit(_get_signal, sym): sym for sym in self.state.target_universe}
                done, not_done = wait(future_to_symbol.keys(), timeout=480.0)
                
                for future in done:
                    try:
                        symbol, signal = future.result()
                        if signal:
                            signals_to_process.append(signal)
                    except Exception as e:
                        logger.error("Error getting signal result for symbol: {}", e)
                        
                if not_done:
                    timed_out_symbols = [future_to_symbol[f] for f in not_done]
                    logger.warning("Phase 4 symbol check timed out for symbols (480s limit): {}", timed_out_symbols)
                    for f in not_done:
                        f.cancel()
        except Exception as e:
            logger.error("Exception in Phase 4 symbol check thread pool: {}", e)
        
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

                    
                    # Check position count limit (Macro Shield bypassed per user request for maximum capital deployment)
                    current_regime = getattr(self.strategy, '_last_regime', '')
                    dynamic_max_positions = config.MAX_POSITIONS
                    
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
                                
                                # Sizing: Equal-weight slot capital allocation based on Total Equity (not temporary cash/BP)
                                # This avoids under-sizing positions due to T+2 settlement delays.
                                _target_capital = total_equity / config.MAX_POSITIONS
                                _slot_qty = int(_target_capital / signal.entry_price) if signal.entry_price > 0 else 1
                                raw_qty = min(_atr_qty, _slot_qty)
                                logger.debug("ATR_SIZING {}: risk=${:.0f} atr={:.2f}  qty={} (slot={} atr={})",
                                             symbol, _risk_amount, _atr, raw_qty, _slot_qty, _atr_qty)
                            else:
                                _target_capital = total_equity / config.MAX_POSITIONS
                                raw_qty = int(_target_capital / signal.entry_price) if signal.entry_price > 0 else 0
                        except Exception as _atr_e:
                            logger.debug("ATR sizing failed: {}", _atr_e)
                            _target_capital = total_equity / config.MAX_POSITIONS
                            raw_qty = int(_target_capital / signal.entry_price) if signal.entry_price > 0 else 0
                        
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
                        
                        # Check profit protection and loss lock-in prevention
                        curr_price = self.trader.get_price(sym)
                        if curr_price > 0:
                            pnl_pct = (curr_price - pos.entry_price) / pos.entry_price
                            if pnl_pct >= config.UPGRADE_PROFIT_PROTECT_PCT:
                                continue  # 2%+ profit protection: don't touch high-performing positions
                            
                            # [BUGFIX] Prevent selling losing positions to upgrade
                            # - We should only upgrade flat or slightly profitable positions.
                            # - If a position is at a loss of more than -1%, let it hit its stop loss; do not lock in losses via upgrade.
                            if pnl_pct < -0.01:
                                continue
                        
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
                            
                            # [LOGICAL BUG FIX] Account for KIS API delay in updating buying power after sell.
                            # Add sell proceeds to current buying power to get the expected buying power.
                            approx_proceeds = worst_pos.quantity * sell_price
                            expected_bp = bp + approx_proceeds * 0.985  # 1.5% margin for slippage/fees
                            
                            if expected_bp > 5 and best_buy_signal.entry_price > 0:
                                # Sizing: Equal-weight slot capital allocation based on Total Equity
                                target_capital = total_equity / config.MAX_POSITIONS

                                # Safety cap: Max 40% of total equity per position
                                max_position_value = total_equity * 0.40
                                if target_capital > max_position_value:
                                    target_capital = max_position_value

                                raw_qty = int(target_capital / best_buy_signal.entry_price)
                                max_by_bp = int(expected_bp / best_buy_signal.entry_price)  # Use expected_bp
                                qty = min(raw_qty, max_by_bp)
                                
                                # Allow minor limit violation (up to 50% over target capital) for 1-share entry
                                if qty == 0 and best_buy_signal.entry_price <= target_capital * 1.5 and best_buy_signal.entry_price <= expected_bp:
                                    qty = 1
                                    logger.info("UPGRADE Sizer override for {}: 1 share allowed via minor limit violation", best_buy_signal.symbol)

                                # Enforce minimum position value of $50 to avoid high transaction friction relative to position size
                                if qty > 0:
                                    position_value = qty * best_buy_signal.entry_price
                                    if position_value < 50.0:
                                        logger.info("UPGRADE SKIP: position value ${:.2f} too small (min $50)", position_value)
                                        qty = 0

                                if qty > 0:
                                    self.phase_5_execute_trade(best_buy_signal.symbol, "BUY", qty,
                                                              best_buy_signal.entry_price,
                                                              f"UPGRADE BUY: {best_buy_signal.composite_score} (replaced {worst_sym})")
                                    self._daily_upgrade_count += 1
                                    
                                    # Notify via Telegram
                                    try:
                                        from notification import get_notifier
                                        get_notifier().send_message(
                                            f"🔄 PORTFOLIO UPGRADE EXECUTED\n"
                                            f"Sold: {worst_sym} ({worst_score})\n"
                                            f"Bought: {best_buy_signal.symbol} ({best_buy_signal.composite_score}) - {qty} shares\n"
                                            f"Improvement: +{best_buy_signal.composite_score - worst_score}"
                                        )
                                    except Exception as ne:
                                        logger.debug("Failed to send upgrade notification: {}", ne)
            except Exception as e:
                logger.debug("Upgrade logic error: {}", e)
                    
        # --- Exit Signals on Positions (Checked again after potential upgrades) ---
        # Note: Primary exit check moved to top, but we keep this as a rapid safety sweep
        # after any buying activity.
        pass

    # ==========================================
    # PHASE 6: QUANT REBALANCING & SCALE-UP
    # ==========================================
    def phase_6_rebalance_underallocated_positions(self):
        """
        T+2 정산 지연으로 인해 매수 당일 1주만 사지고 현금이 남는 현상을 방지합니다.
        예수금이 정산되어 들어오면, 목표 슬롯 비중(20%)보다 현저히 적게 담긴 종목들을 
        남는 Buying Power 범위 내에서 자동으로 추가 매수(Scale-up)하여 슬롯을 가득 채웁니다.
        """
        logger.info("=" * 60)
        logger.info("[PHASE 6] Rebalancing Under-allocated Positions")
        logger.info("=" * 60)
        
        try:
            positions = self.strategy.get_all_positions()
            if not positions:
                logger.info("No held positions to rebalance.")
                return
                
            from composite_signal import get_composite_engine, ActionType
            engine = get_composite_engine()
            
            bp = self.trader.get_buying_power()
            # Calculate total equity
            total_equity = bp
            for sym, pos in positions.items():
                p_price = self.trader.get_price(sym)
                if p_price > 0:
                    total_equity += p_price * pos.quantity
                else:
                    total_equity += pos.entry_price * pos.quantity
            
            # Target capital per slot (e.g. 20% of portfolio for 5 positions)
            target_slot_val = total_equity / config.MAX_POSITIONS
            max_limit_val = total_equity * config.MAX_POSITION_PCT
            target_val = min(target_slot_val, max_limit_val)
            
            logger.info("Target value per slot: ${:.2f} (Portfolio Equity: ${:.2f}, BP: ${:.2f})", 
                        target_val, total_equity, bp)
            
            for symbol, pos in positions.items():
                curr_price = self.trader.get_price(symbol)
                if curr_price <= 0:
                    continue
                    
                current_val = pos.quantity * curr_price
                # If the position holds less than 75% of the target slot value
                if current_val < target_val * 0.75:
                    # Check signal score/action to prevent scaling up weak positions
                    is_screened = symbol in getattr(self.state, 'screened_symbols', [])
                    signal = engine.analyze(symbol, is_screened=is_screened)
                    if signal.action not in [ActionType.STRONG_BUY, ActionType.BUY]:
                        logger.info("SKIP REBALANCE {}: current action is {} (score: {}). No active buy edge.", 
                                    symbol, signal.action.name, signal.composite_score)
                        continue
                        
                    gap_dollars = target_val - current_val
                    # Ensure we don't exceed remaining buying power and leave a $30 buffer
                    allowed_dollars = min(gap_dollars, bp - 30.0)
                    if allowed_dollars >= curr_price:
                        buy_qty = int(allowed_dollars / curr_price)
                        if buy_qty > 0:
                            logger.info("🔍 [REBALANCE] {} under-allocated (${:.2f} < ${:.2f}) with score {} ({}). Scaling up by {} shares.", 
                                        symbol, current_val, target_val, signal.composite_score, signal.action.name, buy_qty)
                            self.phase_5_execute_trade(symbol, "BUY", buy_qty, curr_price, 
                                                       f"REBALANCE_SCALE_UP: Fill slot to target ${target_val:.1f} (score: {signal.composite_score})")
                            # Deduct from bp for subsequent loop items
                            bp -= (buy_qty * curr_price)
        except Exception as e:
            logger.error("Failed to run phase 6 rebalancing: {}", e)

    # ==========================================
    # PHASE 5: EXECUTION & RISK MANAGEMENT
    # ==========================================
    def phase_5_execute_trade(self, symbol: str, action: str, qty: int, price: float, reason: str):
        """Pass through 20+ risk and sizing modules before hitting the smart router"""
        
        # Daily trade limit (exits and upgrade buys always allowed)
        is_upgrade = "UPGRADE" in reason.upper()
        if action == "BUY" and not is_upgrade and self._daily_trade_count >= config.MAX_DAILY_TRADES:
            logger.warning("Daily trade limit exceeded ({}/{}): {}  ",
                          self._daily_trade_count, config.MAX_DAILY_TRADES, symbol)
            return
        
        #   /    BUY ,   
        import os as _os
        _pause_file = "/tmp/kis_trading_paused"
        if action == "BUY" and _os.path.exists(_pause_file):
            logger.warning("PAUSED:  /    {}  ", symbol)
            return

        is_inverse = symbol in getattr(config, 'INVERSE_ETFS', set())
        if self.state.global_risk_level == "RISK_OFF" and action == "BUY" and not is_inverse:
            logger.warning("Trade BLOCKED by Macro Shield (RISK_OFF): {} {}", action, symbol)
            return
        
        # 2. Trade Frequency Control (Exits, Upgrades, and Rebalances always allowed)
        if action == "BUY" and not is_upgrade and not reason.startswith("REBALANCE"):
            window = self._freq_controller.can_trade(is_upgrade=is_upgrade)
            if not window.can_trade:
                logger.info("Trade delayed by frequency: {}", window.reason)
                return

        # 1. Emergency Stop / Circuit Breaker
        if action == "BUY":
            try:
                from emergency_stop import check_circuit_breaker
                if check_circuit_breaker(self.trader, self.rm):
                    logger.warning("CIRCUIT BREAKER ACTIVATED — trade blocked: {} {}", action, symbol)
                    return
            except ImportError:
                pass
            except Exception as cb_err:
                logger.error("Circuit breaker error: {}", cb_err)

        # 3. Drawdown Controller
        try:
            from drawdown_controller import get_drawdown_controller
            bp = self.trader.get_buying_power()
            dc = get_drawdown_controller(bp + sum(p.market_value for p in self.trader.get_positions()))
            if dc.is_halted():
                logger.warning("DRAWDOWN HALT — trade blocked: {} {}", action, symbol)
                return
        except ImportError:
            pass
        except Exception as dc_err:
            logger.error("Drawdown controller error: {}", dc_err)

        # 3.5. RiskManager Gate (Daily/Weekly stops, Cooldowns, Position Slots)
        if action == "BUY":
            try:
                # Pass symbol to allow rebalancing/scale-up on existing positions even if max positions reached
                allowed, rm_reason = self.rm.can_trade(symbol)
                if not allowed:
                    logger.warning("🚨 [QUANT_RISK] Trade BLOCKED by RiskManager: {} {} | Reason: {}", action, symbol, rm_reason)
                    return
            except Exception as rm_err:
                logger.error("[QUANT_RISK] Failed to check RiskManager gate: {}", rm_err)

        # 4. [QUANT FEEDBACK v1.0.8] Advanced Feedback & Regime Position Sizer (Bypassed for rebalancing)
        if action == "BUY" and not reason.startswith("REBALANCE"):
            try:
                from position_sizer import get_position_sizer
                bp = self.trader.get_buying_power()
                live_positions = self.trader.get_positions()
                total_equity = bp + sum(p.market_value for p in live_positions)
                
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
                
                # Small Account Floor Override: Ensure we don't round down to 0 if the original logic approved at least 1 share
                if qty == 0 and old_qty >= 1 and price <= (bp * 0.98) and price <= (total_equity * 0.40):
                    qty = 1
                    logger.info("📐 Small Account Floor Override for {}: 1 share allowed (price: ${:.2f}, sizer target: ${:.2f})", 
                                symbol, price, sizer_result.position_dollars)
                
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
            bp = self.trader.get_buying_power()
            total_equity = bp + sum(p.market_value for p in self.trader.get_positions())
            hm = get_hedge_manager(total_equity)
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
                
                if action == "SELL":
                    self._recently_sold[symbol] = datetime.now()
                
                # Send Trade Notification
                # [v1.1.8 BUG FIX] Only send alert if order confirmed FILLED (not just placed)
                # KIS limit orders: rt_cd=0 means "accepted", not "filled"
                # We wait briefly and check fill status to avoid phantom alerts
                if order.order_type in [OrderType.ADAPTIVE, OrderType.MARKET, OrderType.LIMIT, OrderType.TWAP]:
                    try:
                        pnl_pct = 0.0
                        if action == "SELL" and symbol in self.strategy._positions:
                            pos = self.strategy._positions[symbol]
                            if pos.entry_price > 0:
                                pnl_pct = ((order.avg_fill_price or price) - pos.entry_price) / pos.entry_price
                                
                        from notification import get_notifier
                        notifier = get_notifier()
                        # Check if order was confirmed filled (order.status == FILLED)
                        if order.status == OrderStatus.FILLED:
                            # Gemini Sentiment Judge 결과 추가 (매수 진입 시 텔레그램 연동)
                            if action == "BUY":
                                try:
                                    from news_analyzer import get_news_analyzer
                                    sentiment = get_news_analyzer().analyze(symbol)
                                    if sentiment and sentiment.recommendation:
                                        reason = f"{reason} | [Gemini] {sentiment.recommendation}"
                                except Exception as se:
                                    logger.debug("Failed to append Gemini sentiment to trade alert for {}: {}", symbol, se)
                            notifier.alert_trade(action, symbol, order.avg_fill_price or price, reason, order.filled_quantity, pnl_pct)
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
                
                if order.status == OrderStatus.FILLED:
                    if action == "BUY":
                        atr = self.strategy.get_current_atr(symbol)
                        self.strategy.add_position(symbol, price, qty, atr)
                        try:
                            self.db.record_entry(symbol, qty, price, self.state.current_regime)
                        except Exception as db_err:
                            logger.error("Failed to record entry in DB for {}: {}", symbol, db_err)
                        
                        # [RiskManager Sync] Track new position in RiskManager
                        try:
                            bp = self.trader.get_buying_power()
                            actual_positions = self.trader.get_positions()
                            total_portfolio = bp + sum(p.quantity * p.current_price for p in actual_positions)
                            exposure_pct = (qty * price) / total_portfolio if total_portfolio > 0 else 0
                            self.rm.add_position(symbol, price, qty, exposure_pct)
                            logger.info("[QUANT_RISK] Real-time position added to RiskManager: {} (exp={:.1%})", symbol, exposure_pct)
                        except Exception as rm_err:
                            logger.error("[QUANT_RISK] Failed to sync RiskManager for entry: {}", rm_err)
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
                                try:
                                    self.rm.remove_position(symbol)
                                    logger.info("[QUANT_RISK] Real-time position removed from RiskManager: {}", symbol)
                                except Exception as rm_err:
                                    logger.error("[QUANT_RISK] Failed to remove from RiskManager: {}", rm_err)
                        
                        try:
                            self.db.record_exit(symbol, qty, price, entry_price, reason)
                        except Exception as db_err:
                            logger.error("Failed to record exit in DB for {}: {}", symbol, db_err)
                        
                        # [RiskManager Sync] Record realized trade results in RiskManager Daily & Weekly Stats
                        try:
                            _realized_pnl = (price - entry_price) * qty
                            self.rm.record_trade(_realized_pnl, _realized_pnl >= 0)
                            logger.info("[QUANT_RISK] Realized trade recorded in RiskManager: PnL=${:+.2f}", _realized_pnl)
                        except Exception as rm_err:
                            logger.error("[QUANT_RISK] Failed to record trade in RiskManager: {}", rm_err)
                        # ============================================================
                        #      strategy._consecutive_losses_today 
                        # ============================================================
                        try:
                            _realized_pnl = (price - entry_price) * qty
                            if _realized_pnl < 0:
                                _cur = getattr(self.strategy, '_consecutive_losses_today', 0)
                                self.strategy._consecutive_losses_today = _cur + 1
                                logger.warning("Loss recorded! Consecutive losses today: {}", 
                                               self.strategy._consecutive_losses_today)
                            else:
                                self.strategy._consecutive_losses_today = 0  # Reset
                        except Exception as pnl_err:
                            logger.debug("Failed to update consecutive losses: {}", pnl_err)
                else:
                    logger.warning("⚠️ Trade status for {} is {} (not FILLED). Skipping local database & portfolio updates.", symbol, order.status.value)
                    
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

    def _run_weekly_macro_tuning(self):
        """Runs post-mortem resolution on unresolved macro decisions and auto-tunes news sensitivity multiplier."""
        logger.info("⚙️ Starting Weekly Autonomous Macro Feedback & Self-Tuning...")
        
        # 1. Resolve pending feedbacks
        try:
            unresolved = self.db.get_unresolved_macro_feedbacks()
            logger.info("Found {} unresolved macro feedbacks.", len(unresolved))
        except Exception as e:
            logger.error("Failed to fetch unresolved feedbacks: {}", e)
            return
        
        import yfinance as yf
        resolved_count = 0
        for f in unresolved:
            f_id = f["id"]
            created_at_str = f["created_at"]
            try:
                if isinstance(created_at_str, str):
                    created_at = datetime.strptime(created_at_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    created_at = created_at_str
            except Exception as pe:
                logger.warning("Failed to parse created_at for feedback {}: {}", f_id, pe)
                continue
                
            target_date = created_at + timedelta(days=3)
            spy_exit_price = None
            start_str = target_date.strftime("%Y-%m-%d")
            try:
                end_str = (target_date + timedelta(days=4)).strftime("%Y-%m-%d")
                df = yf.download("SPY", start=start_str, end=end_str, progress=False)
                if not df.empty:
                    if "Close" in df.columns:
                        spy_exit_price = float(df["Close"].iloc[0])
            except Exception as yf_err:
                logger.warning("yfinance fetch failed for date {}: {}", start_str, yf_err)
                
            if spy_exit_price is None:
                logger.warning("Could not retrieve SPY price for date {}. Skipping resolution for feedback {}.", start_str, f_id)
                continue
                
            spy_entry_price = f.get("spy_entry_price")
            if not spy_entry_price or spy_entry_price <= 0:
                accuracy = "UNKNOWN"
                price_change = 0
            else:
                price_change = (spy_exit_price - spy_entry_price) / spy_entry_price
                if price_change <= 0.005:
                    accuracy = "CORRECT"
                else:
                    accuracy = "FALSE_POSITIVE"
                    
            try:
                self.db.resolve_macro_feedback(f_id, spy_exit_price, accuracy)
                logger.info("Resolved feedback {}: Entry={}, Exit={}, Change={:.2%}, Outcome={}",
                            f_id, spy_entry_price, spy_exit_price, price_change, accuracy)
                resolved_count += 1
            except Exception as res_err:
                logger.error("Failed to update feedback resolution in DB: {}", res_err)
                
        logger.info("Resolution complete. Resolved {} cases.", resolved_count)
        
        # 2. Sensitivity Auto-Tuning
        try:
            recent = self.db.get_recent_resolved_feedbacks(days=30)
        except Exception as e:
            logger.error("Failed to get recent resolved feedbacks: {}", e)
            return

        if not recent:
            logger.info("No resolved feedback data within the last 30 days. Skipping sensitivity tuning.")
            return
            
        total = len(recent)
        correct_count = sum(1 for r in recent if r["accuracy"] == "CORRECT")
        fp_count = sum(1 for r in recent if r["accuracy"] == "FALSE_POSITIVE")
        
        correct_rate = correct_count / total
        fp_rate = fp_count / total
        
        import json
        import os
        config_path = os.path.join(os.path.dirname(__file__), "macro_config.json")
        current_multiplier = 1.0
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f_cfg:
                    cfg = json.load(f_cfg)
                    current_multiplier = cfg.get("news_sensitivity_multiplier", 1.0)
            except Exception as cfg_err:
                logger.warning("Failed to read macro_config.json: {}", cfg_err)
                
        new_multiplier = current_multiplier
        if fp_rate > 0.6:
            new_multiplier = current_multiplier * 0.85
        elif correct_rate > 0.8:
            new_multiplier = current_multiplier * 1.15
            
        new_multiplier = max(0.5, min(2.0, new_multiplier))
        
        try:
            with open(config_path, "w", encoding="utf-8") as f_cfg:
                json.dump({"news_sensitivity_multiplier": new_multiplier}, f_cfg, indent=4)
            logger.info("Auto-tuned news sensitivity multiplier: {:.4f} -> {:.4f} (Correct: {:.1%}, FP: {:.1%})",
                        current_multiplier, new_multiplier, correct_rate, fp_rate)
        except Exception as save_err:
            logger.error("Failed to save auto-tuned multiplier to macro_config.json: {}", save_err)
            
        try:
            from watchdog import send_tg
            msg = (
                f"⚙️ <b>매크로 감도 자가 튜닝 리포트</b>\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"• 분석 대상 (최근 30일): {total}건\n"
                f"• 방어 성공 (CORRECT): {correct_count}건 ({correct_rate:.1%})\n"
                f"• 오작동 방어 (FALSE_POSITIVE): {fp_count}건 ({fp_rate:.1%})\n"
                f"• 감도 승수 조정: {current_multiplier:.4f} ➔ <b>{new_multiplier:.4f}</b>"
            )
            send_tg(msg)
        except Exception as tg_err:
            logger.debug("Failed to send tuning TG alert: {}", tg_err)

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
                
                # Check and recover emergency state if active
                try:
                    if hasattr(self, '_emergency') and self._emergency:
                        self._emergency.check_recovery()
                except Exception as erec:
                    logger.debug("Emergency recovery check failed: {}", erec)
                
                # ✦ 24/7 무중단 자동 패치 체크 (4시간 주기 원격 전략 자동 업데이트 동기화 및 자체 재기동)
                try:
                    if not hasattr(self, '_last_update_check') or (now - self._last_update_check).total_seconds() > 14400:
                        self._last_update_check = now
                        import updater
                        if updater.check_and_update():
                            logger.warning("🔄 [24/7 무중단 패치] 최신 전략 패치가 완료되었습니다. 봇을 즉시 자체 재기동합니다!")
                            import sys
                            import os
                            python_exe = sys.executable if sys.executable else "python3"
                            os.execvp(python_exe, ['python', 'main.py'] + sys.argv[1:])
                except Exception as ue:
                    logger.debug("24/7 무중단 업데이트 스킵: {}", ue)
                
                # ✦ 매주 일요일 자율 피드백 루프 및 자가 튜닝 스케줄러 (일요일에 1주 1회 실행)
                if now.weekday() == 6:  # Sunday
                    if not hasattr(self, '_last_weekly_tuning_date') or self._last_weekly_tuning_date != now.date():
                        self._last_weekly_tuning_date = now.date()
                        try:
                            self._run_weekly_tuning()
                        except Exception as te:
                            logger.error("Error during weekly tuning: {}", te)
                
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
                    
                    # Refresh screener every 45 minutes (to double breakout discovery speed safely)
                    if (self.state.last_screen_refresh is None or 
                        (now - self.state.last_screen_refresh) > timedelta(minutes=45)):
                        self.phase_3_run_screener()
                    
                    # PHASE 4: Signal loop iteration
                    # Ensure internal position state is synced with API before processing
                    try:
                        self.strategy.sync_positions(self.trader.get_positions())
                    except Exception as se:
                        logger.error("Periodic position sync failed: {}", se)

                    self._run_phase_4_cycle(engine)
                    
                    # ✦ PHASE 6: Position Rebalancing & Scale-up
                    try:
                        if not hasattr(self, '_last_rebalance_time') or (now - self._last_rebalance_time).total_seconds() > 900:
                            self._last_rebalance_time = now
                            self.phase_6_rebalance_underallocated_positions()
                    except Exception as re_err:
                        logger.error("Periodic rebalancing failed: {}", re_err)
                    
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
                                            if exit_sig.action == "SELL_HALF":
                                                sell_qty = max(1, pos.quantity // 2)
                                                if sell_qty >= pos.quantity:
                                                    logger.info("Only {} share(s) held for {}. Upgrading SELL_HALF to SELL_ALL.", pos.quantity, sym)
                                                    self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                                                    self.strategy.remove_position(sym)
                                                else:
                                                    self.phase_5_execute_trade(sym, "SELL", sell_qty, exit_sig.price, exit_sig.reason)
                                                    self.strategy.mark_half_sold(sym)
                                            else:
                                                self.phase_5_execute_trade(sym, "SELL", pos.quantity, exit_sig.price, exit_sig.reason)
                                                self.strategy.remove_position(sym)
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

    def _run_weekly_tuning(self):
        """매주 일요일 자율 피드백 루프 및 자가 튜닝을 실행합니다."""
        logger.info("⚙️ [Weekly Tuning] 시작합니다...")
        try:
            # 1. 7일간의 거래 성과 분석 및 통계 생성
            from database import get_database
            import pandas as pd
            import numpy as np
            
            db = get_database()
            with db._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT symbol, price, quantity, exit_time, pnl, pnl_pct
                    FROM trades
                    WHERE side = 'SELL' AND exit_time >= datetime('now', '-7 days')
                """)
                rows = [dict(row) for row in cursor.fetchall()]
                
            if not rows:
                logger.info("⚙️ [Weekly Tuning] 최근 7일간 완료된 거래가 없어 튜닝을 스킵합니다.")
                return
                
            df = pd.DataFrame(rows)
            
            # 2. 성과 메트릭 계산
            total_trades = len(df)
            winning_trades = len(df[df['pnl'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_profit_rate = df['pnl_pct'].mean()
            total_profit = df['pnl'].sum()
            
            logger.info("⚙️ [Weekly Tuning] 최근 7일 성과 요약: 거래수={}, 승률={:.1%}, 평균수익률={:.2%}, 총수익={:.0f}원", 
                        total_trades, win_rate, avg_profit_rate, total_profit)
            
            # 3. .env 파일의 파라미터 조정을 위한 의사결정
            from dotenv import load_dotenv
            import os
            
            load_dotenv(override=True)
            current_tp_mult = float(os.getenv('ATR_TP_MULT', '1.5'))
            
            new_tp_mult = current_tp_mult
            reason = ""
            
            if win_rate < 0.40:
                new_tp_mult = max(1.0, current_tp_mult - 0.2)
                reason = f"최근 7일 승률이 저조하여 ({win_rate:.1%}) ATR_TP_MULT를 {current_tp_mult}에서 {new_tp_mult:.1f}로 낮춰 익절 확률을 높립니다."
            elif win_rate > 0.65 and avg_profit_rate < 0.01:
                new_tp_mult = min(2.5, current_tp_mult + 0.2)
                reason = f"최근 7일 승률이 양호하여 ({win_rate:.1%}) ATR_TP_MULT를 {current_tp_mult}에서 {new_tp_mult:.1f}로 높여 수익 극대화를 시도합니다."
            
            if new_tp_mult != current_tp_mult:
                logger.warning("⚙️ [Weekly Tuning] Parameter Tuning Triggered: {}", reason)
                
                env_path = 'config.env' if os.path.exists('config.env') else '.env'
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    updated = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith('ATR_TP_MULT='):
                            lines[i] = f"ATR_TP_MULT={new_tp_mult:.1f}\n"
                            updated = True
                            break
                    
                    if not updated:
                        lines.append(f"\nATR_TP_MULT={new_tp_mult:.1f}\n")
                    
                    with open(env_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                        
                    logger.info("⚙️ [Weekly Tuning] {} 업데이트 완료.", env_path)
                    
                    try:
                        from notifier import get_notifier
                        msg = (
                            f"⚙️ <b>주간 자율 피드백 및 파라미터 자동 튜닝 리포트</b>\n\n"
                            f"• 기간: 최근 7일\n"
                            f"• 총 거래 횟수: {total_trades}회\n"
                            f"• 승률: {win_rate:.1%}\n"
                            f"• 평균 수익률: {avg_profit_rate:.2%}\n"
                            f"• 총 손익: <b>${total_profit:+,.2f}</b>\n\n"
                            f"🔧 <b>조정 내역:</b>\n"
                            f"• ATR_TP_MULT: {current_tp_mult} -> {new_tp_mult:.1f}\n"
                            f"• 사유: {reason}"
                        )
                        get_notifier().send(msg)
                    except Exception as ne:
                        logger.error("Failed to send weekly tuning notification: {}", ne)
                else:
                    logger.error("⚙️ [Weekly Tuning] 환경 설정 파일을 찾을 수 없습니다.")
            else:
                logger.info("⚙️ [Weekly Tuning] 파라미터 조정 조건에 부합하지 않아 기존 설정을 유지합니다.")
                try:
                    from notifier import get_notifier
                    msg = (
                        f"⚙️ <b>주간 자율 피드백 리포트 (유지)</b>\n\n"
                        f"• 기간: 최근 7일\n"
                        f"• 총 거래 횟수: {total_trades}회\n"
                        f"• 승률: {win_rate:.1%}\n"
                        f"• 평균 수익률: {avg_profit_rate:.2%}\n"
                        f"• 총 손익: <b>${total_profit:+,.2f}</b>\n\n"
                        f"🔧 현재 파라미터 설정(ATR_TP_MULT={current_tp_mult})을 유지합니다."
                    )
                    get_notifier().send(msg)
                except Exception as ne:
                    logger.error("Failed to send weekly tuning notification: {}", ne)
                    
        except Exception as e:
            logger.exception("⚙️ [Weekly Tuning] 실행 중 오류 발생")


