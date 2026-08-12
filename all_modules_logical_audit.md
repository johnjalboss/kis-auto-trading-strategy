# 149 Modules Logical Validity Audit

### accumulation.py
**Purpose:** Accumulation/Distribution Pattern Detector ============================================ Detect Wyckoff accumulation/distribution patterns.
**Data Fields Fetched:** Volume, Low, Close, High
**Scoring Logic:** +30, -30, -20, +10, -25, +20, +25

### adaptive_strategy.py
**Purpose:** Adaptive Strategy Selector ============================ Automatically switches strategies based on market regime.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### aggressive_technical_backtest.py
**Purpose:** ULTRA-AGGRESSIVE TECHNICAL STRATEGY ==================================== - 100% invested in uptrends
**Data Fields Fetched:** mom5, low50, trades, sma20, sma5, benchmark_return, cci, macd, stoch_k, mom20, Volume, Low, atr14, r1, ema50
**Scoring Logic:** +20, +10, +15

### ai_judge.py
**Purpose:** AI 매매 판단 모듈 ATR 트레일링 스탑 전략 + 이동평균/거래량 기반 매수 조건
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### all_modules_backtest.py
**Purpose:** ULTIMATE ALL-MODULES BACKTESTER ================================ Imports and uses ALL available modules for maximum intelligence.
**Data Fields Fetched:** annual_return, total_return, 3yr_agg, modules_used, trades, benchmark_return, instance, Close, alpha, Volume, Low, final_capital, max_drawdown, 1yr_agg, High
**Scoring Logic:** None detected

### all_modules_backtest_vs_qqq.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** benchmark_max_dd, total_return, modules_used, trades, benchmark_return, instance, Close, alpha, Volume, Low, final_capital, max_drawdown, High
**Scoring Logic:** None detected

### alpha_generator.py
**Purpose:** Alpha Signal Generator ======================== Generate high-conviction alpha signals.
**Data Fields Fetched:** momentum, quality, Close, Volume, Low, reversal, High
**Scoring Logic:** None detected

### analyze_entry_timing.py
**Purpose:** Analyze past trades to find data-driven thresholds for overextension penalty. Questions: 1. When we bought, what was the stock's % gain from SMA20?
**Data Fields Fetched:** ret5_bin, type, pnl_pct, dist_sma20_pct, Close, price, ret_5d_pct, dist_bin, win
**Scoring Logic:** None detected

### anti_fragility.py
**Purpose:** Anti-Fragility Module ======================= Profit from chaos and extreme events.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** +30, +40, +20, +10

### apply_patch.py
**Purpose:** 서버 상의 3개 파일을 직접 수정하는 패치 스크립트: 1. orchestrator.py - self.risk_manager → self.rm 수정 + auto_tuner → auto_tuner_new 수정 2. strategy.py     - CHOPPY 레짐 진입 차단 추가
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_adapters.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_mappings.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** exchange
**Scoring Logic:** None detected

### audit_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_remote_positions.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_remote_v2.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_script.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### audit_swap.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### auth.py
**Purpose:** AutoAuth - Automatic Token Management for 24/7 Operation Refreshes KIS API tokens every 12 hours
**Data Fields Fetched:** access_token, tr_id, expires_at, token_type
**Scoring Logic:** None detected

### auto_compound.py
**Purpose:** Auto Compound & Profit Reinvestment ===================================== Automatically reinvest profits for compound growth.
**Data Fields Fetched:** reinvested, start_date, initial_capital, milestones_hit, current_capital, withdrawn
**Scoring Logic:** None detected

### auto_tuner.py
**Purpose:** Auto Tuner - 매매 데이터 기반 자동 파라미터 튜닝 v2 ================================================ 매주 일요일 자동 실행 (시장 휴장일).
**Data Fields Fetched:** TAKE_PROFIT_PCT, reasons, side, changes, wins, DAILY_STOP_LOSS_PCT, avg_hold_hours, MAX_POSITION_PCT, losses, ATR_STOP_MULTIPLIER, win_rate, exit_time, analysis, symbol_performance, profit_factor
**Scoring Logic:** None detected

### auto_tuner_new.py
**Purpose:** Ultimate Swing Auto-Tuner AI (Reinforcement Learning) ===================================================== Analyzes the trades.db over the past 14 days and adjusts .env
**Data Fields Fetched:** total_trades, SCREENED_MIN_SCORE, wins, pnl_pct, MAX_POSITION_PCT, avg_hold_days, created_at, TAKE_PROFIT_PCT, entry_time, exit_time, reasons, pnl, losses, changes, profit_factor
**Scoring Logic:** None detected

### backfill_stats.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** net_pnl, losses, wins
**Scoring Logic:** None detected

### backtest_vs_qqq.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** trailingEps, peg, pegRatio, eps, Close, earningsGrowth, sector
**Scoring Logic:** None detected

### backtester.py
**Purpose:** Backtesting Engine ================== Test trading strategies against historical data.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### base_adapters.py
**Purpose:** Universal Adapters for 130+ Modules ==================================== Auto-discovers ALL Python modules in the project, wraps their classes
**Data Fields Fetched:** regime, data, is_squeezing, Close, price, signals, risk_score, df, new_capital, capital, current_price, ticker
**Scoring Logic:** None detected

### base_analyzer.py
**Purpose:** Standard Interface for all Strategy Modules =========================================== This ensures the master `composite_signal.py` can load any of the 70+
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### candlestick.py
**Purpose:** Candlestick Pattern Detector ============================== Detect Japanese candlestick patterns for reversal/continuation signals.
**Data Fields Fetched:** High, Low, Close, Open
**Scoring Logic:** +30, -30, -35, -20, -25, +20, +35, +25

### capture_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### chart_generator.py
**Purpose:** Chart Generator Module ======================= Generates performance charts for Telegram/Discord notifications.
**Data Fields Fetched:** min_date, max_date, left, Close, net_pnl, top, right, bottom
**Scoring Logic:** None detected

### check_actual_balance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_avgo.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_balance_exact.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pdno, ovrs_item_name, rt_cd, output1, ovrs_cblc_qty, msg1
**Scoring Logic:** None detected

### check_cdns.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** price, reason, entry_time, exit_time, side, quantity, id
**Scoring Logic:** None detected

### check_config_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_db.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_errors.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_fix_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_imports.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_kis_pos.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_log.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_macro_score.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_methods.py
**Purpose:** Check all non-discovered modules for their class methods
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_modules.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_mrvl_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** regime, price, reason, entry_time, exit_time, side, quantity, id
**Scoring Logic:** None detected

### check_open.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pnl_pct, price, entry_time, side, quantity, exit_time
**Scoring Logic:** None detected

### check_open_orders.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_paper_balance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** rt_cd, prdt_name, output1, ovrs_cblc_qty, msg1, ovrs_pdno
**Scoring Logic:** None detected

### check_perf.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pnl_pct, entry_price, reason, entry_time, pnl, quantity, exit_time
**Scoring Logic:** None detected

### check_perf2.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pnl_pct, trades_count, reason, pnl, gross_pnl, exit_time, losses, ending_balance, wins
**Scoring Logic:** None detected

### check_pnl.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_raw_balance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** rt_cd, prdt_name, output1, ovrs_cblc_qty, msg1, ovrs_pdno
**Scoring Logic:** None detected

### check_screener.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_sells.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_sigs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_sqqq.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_state.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pchs_avg_pric, ord_psbl_qty, rt_cd, output1, ovrs_cblc_qty, ovrs_pdno
**Scoring Logic:** None detected

### check_state_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_status_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_trades.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_trades_detail.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_tz.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### check_unfilled.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** price, side, quantity, order_id
**Scoring Logic:** None detected

### check_unfilled_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** orgn_odno, access_token, pdno, output, unfc_qty, rt_cd, sll_buy_dvsn_cd, msg1
**Scoring Logic:** None detected

### check_universe_count.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** count, updated
**Scoring Logic:** None detected

### clean_files.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### clean_files_v2.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### clean_local_garbage.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### clean_stale.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### complete_117_backtest.py
**Purpose:** COMPLETE 117 MODULE INTEGRATION BACKTESTER ============================================ Uses EVERY SINGLE module we created for maximum intelligence.
**Data Fields Fetched:** trades, factor_analysis, risk_manager, liquidity_filter, manipulation_defense, manipulation_risk, signal_generator, divergence, market_internals, oil_impact, mean_reversion, competition_mode, tax_optimizer, indicators, news_analyzer
**Scoring Logic:** None detected

### complete_backtest_vs_qqq.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** trailingEps, peg, pegRatio, eps, Close, Volume, Low, earningsGrowth, sector, High
**Scoring Logic:** +20, +15

### composite_signal.py
**Purpose:** Composite Signal Engine (Master Integrator) ============================================= Combines ALL filters into a single trading decision.
**Data Fields Fetched:** technical, sentiment, risk, Close, signals, macro, Volume, Low, smart_money, High, fundamental
**Scoring Logic:** +30, -30, -20, -15, -25, +20, -10, +25

### comprehensive_backtest.py
**Purpose:** Comprehensive Strategy Backtester ===================================== Backtest across multiple periods and market regimes.
**Data Fields Fetched:** type, pnl_pct, Close, Volume, pnl, Low, High
**Scoring Logic:** None detected

### config.py
**Purpose:** Configuration Module ==================== Centralized settings for the trading bot.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### config_remote.py
**Purpose:** Configuration Module ==================== Centralized settings for the trading bot.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### correlation_matrix.py
**Purpose:** Correlation Matrix & Diversification ======================================= Monitor portfolio correlation for optimal diversification.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### correlation_regime.py
**Purpose:** Correlation Regime Detector ============================== Detect when correlations break down.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### cost_model.py
**Purpose:** Cost Model (Commission & Slippage) ==================================== Model real trading costs.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### count_adapters.py
**Purpose:** Count adapters after rewrite
**Data Fields Fetched:** total, by_category
**Scoring Logic:** None detected

### credit_spreads.py
**Purpose:** Credit Spread Analyzer ======================== Analyze credit market stress for risk-off signals.
**Data Fields Fetched:** Close
**Scoring Logic:** +30, -30, -20, -15, -25, -40, +25, -60

### crypto_sentiment.py
**Purpose:** Crypto Sentiment Indicator ============================= Bitcoin as risk sentiment gauge.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### dashboard.py
**Purpose:** Trading Dashboard ================== Real-time web UI for monitoring trading performance.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### dashboard_app.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** memory_percent, cpu_percent, side, net_pnl, wins, current_regime, losses, Cum_PnL, api_status, win_rate, pnl_pct, unrealized_pnl, positions, current_price, entry_price
**Scoring Logic:** None detected

### dashboard_cli.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** current_regime, pnl_pct, memory_percent, entry_price, header, cpu_percent, net_pnl, positions, losses, win_rate, quantity, api_status, current_price, main, wins
**Scoring Logic:** None detected

### data_proxy.py
**Purpose:** Data Proxy for Monkey Patching yfinance ========================================= This module intercepts calls to `yfinance.download` AND `yfinance.Ticker`
**Data Fields Fetched:** previousClose, averageVolume, marketCap, fiftyTwoWeekHigh, tvol, Volume, regularMarketPrice, revenueGrowth, interval, fiftyTwoWeekLow, last, progress, auto_adjust, base, timeout
**Scoring Logic:** None detected

### database.py
**Purpose:** Database Module - SQLite Trade History ======================================= Persistent storage for trades, daily stats, and performance metrics.
**Data Fields Fetched:** trades, side, net_pnl, wins, reason, total, gross_pnl, avg_pnl_pct, losses, exit_time, pnl_pct, regime, price, max_drawdown, ending_balance
**Scoring Logic:** None detected

### debug_candle_pattern.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### debug_db_server.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### debug_kis_pos.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pchs_avg_pric, rt_cd, output1, ovrs_cblc_qty, msg1, ovrs_pdno
**Scoring Logic:** None detected

### decoded_composite_signal.py
**Purpose:** Composite Signal Engine (Master Integrator) ============================================= Combines ALL filters into a single trading decision.
**Data Fields Fetched:** technical, sentiment, risk, Close, signals, macro, Volume, Low, smart_money, High, fundamental
**Scoring Logic:** +30, -30, -35, -20, -15, -25, +20, -10, -40, +25

### deep_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** avg_pnl, regime, cnt, reason, total, worst, avg_win, total_pnl, best, avg_loss, wins
**Scoring Logic:** None detected

### deep_verify.py
**Purpose:** Deep Functional Verification =================================== Import가 아니라 실제로 함수를 호출해서 데이터가 정상적으로 흘러가는지 확인.
**Data Fields Fetched:** rate, last, TQQQ, Close, signals
**Scoring Logic:** None detected

### deploy_all.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_dashboard.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_data_proxy_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_econ_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_hotfix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_intermarket.py
**Purpose:** Upload intermarket.py to Oracle VPS (no restart - will apply next cycle).
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_kis_data.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_new_modules.py
**Purpose:** Deploy sector_fund_flow.py and verify.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_optimizations.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_patch.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_reliable.py
**Purpose:** Upload files one by one, retrying on timeout, using max 90s per file.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_remote_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_screener.py
**Purpose:** Upload screener.py and restart kis-trading service.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_strategy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_targeted.py
**Purpose:** Targeted deploy: only upload the files that were actually changed/fixed. Much faster than deploy_all.py which uploads ~400 files.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_universe.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_updates.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_v106.py
**Purpose:** v1.0.6 Targeted Hotfix Deployer ================================ Only deploys the specific files changed in v1.0.6 to avoid SCP timeout.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_v117.py
**Purpose:** Deploy v1.1.7 — Core Quant Engine Fixes ========================================= 1. composite_signal.py: Added get_signal() module-level function with 30-min cache
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### deploy_valuation_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### detail_check.py
**Purpose:** 세부 API 검증 스크립트
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_adapters.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_bp.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_correlation_truth.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_db.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_modules.py
**Purpose:** Auto-discovery diagnostic: find which modules fail and why
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_pltd.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** last_price, PLTD
**Scoring Logic:** None detected

### diag_pltd_final.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** access_token, pdno, last, output, rt_cd, output1, ovrs_cblc_qty
**Scoring Logic:** None detected

### diag_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_screener.py
**Purpose:** 스크리너 근본 문제 진단
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_server.py
**Purpose:** 서버에서 직접 실행해 DB와 로그 상태를 진단하는 스크립트
**Data Fields Fetched:** sells, pnl_pct, entry_price, daily_pnl, entry_date, price, pnl, net_qty, side, report_type, report_date, avg_buy, qty, wins
**Scoring Logic:** None detected

### diag_state.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_sync_issue.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_telegram.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### diag_yfinance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### divergence.py
**Purpose:** Divergence Detector ====================== Detect bullish and bearish divergences between price and indicators.
**Data Fields Fetched:** Volume, Close
**Scoring Logic:** -15, +15, -25, +40, -40, +25

### download_log.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### drawdown_controller.py
**Purpose:** Drawdown Controller ===================== Hard limits on losses to protect capital.
**Data Fields Fetched:** monthly_start, consecutive_green_days, stop_reason, current_capital, daily_start, is_stopped, peak_capital, weekly_start
**Scoring Logic:** None detected

### drawdown_recovery.py
**Purpose:** Drawdown Recovery Mode ======================== Special strategy when in drawdown.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### dynamic_scaling.py
**Purpose:** Dynamic Position Scaling ========================== Scale position sizes as capital grows.
**Data Fields Fetched:** shares, risk_amount, pct_of_capital, risk_pct
**Scoring Logic:** None detected

### dynamic_stop.py
**Purpose:** Dynamic Stop Loss Manager ========================== Volatility-based dynamic stop loss adjustment.
**Data Fields Fetched:** lowest_price, entry_price, Close, entry_time, current_stop, highest_price, Low, High
**Scoring Logic:** None detected

### earnings_analyzer.py
**Purpose:** Earnings Analyzer ================== Track earnings surprises and estimate revisions.
**Data Fields Fetched:** quarter, estimate, revenueActual, year, revenueGrowth, revenueEstimate, surprisePercent, reportDate, period, epsEstimate, revenueSurprisePercent, trailingPE, actual, Close, epsActual
**Scoring Logic:** +30, -30, -20, +10, -15, +15, -25, +20, -10

### earnings_calendar.py
**Purpose:** Earnings Calendar =================== Track and avoid earnings announcements.
**Data Fields Fetched:** Earnings Date
**Scoring Logic:** None detected

### earnings_quality.py
**Purpose:** Earnings Quality Scorer ======================== Measures the quality of reported earnings by comparing:
**Data Fields Fetched:** marketCap, returnOnEquity, debtToEquity, freeCashflow, netIncomeToCommon
**Scoring Logic:** -20, +10, +15, -25, +20, -10, +5

### economic_calendar.py
**Purpose:** Economic Calendar =================== Avoid trading around major economic events.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### economic_surprise.py
**Purpose:** Economic Surprise Index ======================== Tracks economic indicator surprises (actual vs. consensus forecast).
**Data Fields Fetched:** Close
**Scoring Logic:** -8, +8

### emergency_stop.py
**Purpose:** Emergency Stop System ======================= Circuit breaker for extreme market conditions.
**Data Fields Fetched:** is_active, severity, reason
**Scoring Logic:** None detected

### enhanced_backtester.py
**Purpose:** Enhanced Backtester ===================== 3-year historical simulation with detailed metrics.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### estimate_revision.py
**Purpose:** Estimate Revision Momentum Module =================================== Tracks analyst earnings estimate revisions.
**Data Fields Fetched:** revenueGrowth, trailingPE, earningsGrowth, forwardPE, recommendationMean
**Scoring Logic:** +8, -20, +10, -15, +15, +20, -10, +7

### etf_flows.py
**Purpose:** ETF Flow Tracker ================== Track money flows in sector ETFs and broad market.
**Data Fields Fetched:** Close
**Scoring Logic:** +10, -15, +15, -25, -10, +25

### event_calendar.py
**Purpose:** Event Calendar Module ====================== Track market-moving events for timing and risk management.
**Data Fields Fetched:** epsEstimate, type, Ex-Dividend Date, days_until, Earnings Average, is_this_week, is_monthly, Earnings Date, epsActual
**Scoring Logic:** -20, -15, -25, -10, -40

### execution_tracker.py
**Purpose:** Execution Quality Tracker =========================== Track and optimize trade execution quality.
**Data Fields Fetched:** slippage_pct, hour
**Scoring Logic:** None detected

### exit_optimizer.py
**Purpose:** Exit Optimizer ================ Optimize exit timing for maximum profit.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### extract_api.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** 주식잔고조회, 거래량순위, 주식현재가 일자별, 주식일별분봉조회, 주식주문(현금), 주식현재가 시세
**Scoring Logic:** None detected

### extract_json.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_kis_api.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_last.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_logic.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** scoring, purpose, error, data_fields, file
**Scoring Logic:** None detected

### extract_remote_logs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_rlmd.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_rlmd_context.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_tr_id.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### extract_trades.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### factor_analysis.py
**Purpose:** Factor Analysis Engine ======================== Multi-factor quantitative stock analysis.
**Data Fields Fetched:** size, momentum, priceToSalesTrailing12Months, quality, marketCap, returnOnEquity, revenueGrowth, trailingPE, Close, debtToEquity, volatility, profitMargins, priceToBook, sector, forwardPE
**Scoring Logic:** +30, -30, -20, +10, -15, +15, -25, +20, +40, -10, +5, +35, +25

### fed_watch.py
**Purpose:** Fed Watch - Interest Rate Expectations ======================================== Track Federal Reserve policy expectations.
**Data Fields Fetched:** Close
**Scoring Logic:** +30, -20, -15, +15, -25, -40, +25

### fetch_dashboard_data.py
**Purpose:** Fetch dashboard data from KIS API on the server. Run on Oracle server via SSH.
**Data Fields Fetched:** exchange_rate, frcr_ord_psbl_amt1, entry, from_cache, rt_cd, status, errors, output1, net_pnl, avg_daily_pnl_pct, wins, output, ovrs_ord_psbl_amt, losses, ovrs_cblc_qty
**Scoring Logic:** None detected

### fibonacci.py
**Purpose:** Fibonacci Levels Analyzer =========================== Calculate and analyze Fibonacci retracement/extension levels.
**Data Fields Fetched:** Low, Close, High
**Scoring Logic:** -15, +15, -25, +20, +35, +25

### final_verify.py
**Purpose:** Final comprehensive system verification — runs every core module.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_all_trades.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_correlation_usage.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_correlation_usage_lines.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_dataclass_get_bugs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_nonstandard_params.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### find_volume_calls.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### finnhub_client.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** timestamp, token, data
**Scoring Logic:** None detected

### fix_and_sell_hst.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### fix_botteneck.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### fix_db_pnl.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** id, price, quantity, exit_time
**Scoring Logic:** None detected

### fix_db_sync.py
**Purpose:** DB 싱크 수정 스크립트 - KIS API에서 실제 보유 포지션 확인 - DB에서 실제로 청산된 종목들을 closed 처리
**Data Fields Fetched:** avg_price, pchs_avg_pric, pdno, prpr, hldg_qty, quantity, current_price, ticker
**Scoring Logic:** None detected

### fix_orchestrator.py
**Purpose:** orchestrator.py 의 auto_tuner 섹션을 수동으로 올바르게 수정
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### fix_swap.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### fix_universe.py
**Purpose:** S&P 500 Wikipedia fetch 진단 + 캐시 강제 갱신
**Data Fields Fetched:** count, updated
**Scoring Logic:** None detected

### frequency_controller.py
**Purpose:** Trade Frequency Controller ============================ Control trading frequency: Swing-Day Hybrid Mode
**Data Fields Fetched:** last_trade, entries_today
**Scoring Logic:** None detected

### full_audit.py
**Purpose:** 전체 매매 시스템 완전 감사
**Data Fields Fetched:** 1-3d, 6-24h, created_at, Close, entry_time, 2-6h, pnl, reason, 3d+, Low, <2h, High
**Scoring Logic:** None detected

### full_programmatic_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### full_system_check.py
**Purpose:** 전체 시스템 연결 상태 완전 검증 스크립트 - Phase 1~6 모든 모듈 실제 데이터 반환 여부 - strategy.py 가드 데이터 소스 연결 여부
**Data Fields Fetched:** signals
**Scoring Logic:** None detected

### fundamental_analyzer.py
**Purpose:** Fundamental Analyzer ====================== Analyze company fundamentals (EPS, PE, Revenue, etc.)
**Data Fields Fetched:** priceToSalesTrailing12Months, currentRatio, returnOnEquity, trailingEps, trailingPE, revenueGrowth, pegRatio, debtToEquity, freeCashflow, earningsGrowth, profitMargins, priceToBook, sector, forwardPE
**Scoring Logic:** None detected

### fx_risk.py
**Purpose:** FX Risk Module - USD/KRW Exchange Rate Impact =============================================== Monitors the USD/KRW exchange rate trend to gauge FX headwind/tailwind
**Data Fields Fetched:** Close
**Scoring Logic:** +10, -10, -15, +15

### gap_fill.py
**Purpose:** Gap Fill Analysis =================== Analyze and trade gap fills.
**Data Fields Fetched:** High, Low, Close, Open
**Scoring Logic:** None detected

### gap_scanner.py
**Purpose:** Gap Scanner ============= Pre-market gap analysis for momentum trading.
**Data Fields Fetched:** Open, Close, Volume, Low, High
**Scoring Logic:** +20, +10, +5, +15

### generate_dashboard.py
**Purpose:** Generate HTML dashboard from bot data JSON. Usage: python generate_dashboard.py <input.json> <output.html>
**Data Fields Fetched:** timestamp, log, pnl_pct, buying_power, current, entry, total_value, status, errors, history, positions, avg_daily_pnl_pct, qty, total_pnl
**Scoring Logic:** None detected

### generate_universe_lists.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### geopolitical.py
**Purpose:** Geopolitical Risk Monitor ============================ Track geopolitical events affecting markets.
**Data Fields Fetched:** SPY, Close, USO, ITA, GLD
**Scoring Logic:** +30, +40, +20

### get_logs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### get_mrvl_trades.py
**Error:** invalid non-printable character U+FEFF (<unknown>, line 1)

### get_pltd_mapping.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** rt_cd, access_token, output1, pdno
**Scoring Logic:** None detected

### get_sigs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### global_macro.py
**Purpose:** Global Macro Analyzer ======================== World events impact on US stocks.
**Data Fields Fetched:** signal, Close
**Scoring Logic:** +10, +15, +20, -10, +5, +25

### health_monitor.py
**Purpose:** Health Monitor ================ System health and performance monitoring.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### hedge_manager.py
**Purpose:** Hedge Manager =============== Manage portfolio hedges (VIX, Gold, Bonds).
**Data Fields Fetched:** etf
**Scoring Logic:** None detected

### hidden_markov_regime.py
**Purpose:** Hidden Markov Model - Regime Detector ==================================== Advanced probabilistic detection of market regimes (Bull, Bear, Choppy).
**Data Fields Fetched:** state_probabilities, regime, Close, signals, risk_score, confidence, entropy
**Scoring Logic:** None detected

### high_performance.py
**Purpose:** High Performance Optimizer ============================ Maximum returns while maintaining risk control.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### indicators.py
**Purpose:** Advanced Technical Indicators ============================== Comprehensive indicator library for entry/exit signals.
**Data Fields Fetched:** Volume, Low, Close, High
**Scoring Logic:** +20, +10, +5, +15

### insider_tracker.py
**Purpose:** Insider & Institutional Tracker ================================= Track insider buying/selling and institutional ownership.
**Data Fields Fetched:** position, shortRatio, marketCap, Start Date, transactionDate, transactionPrice, Insider, Position, Shares, change, shortPercentOfFloat, heldPercentInstitutions, Transaction
**Scoring Logic:** +10, -15, +15, +20, -10, +5, +35, +25

### inspect_db_local.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### inspect_db_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### inspect_remote_db.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### integration_test.py
**Purpose:** Integration Test - All 111+ Modules ===================================== Verify all modules work together.
**Data Fields Fetched:** failed, passed, errors
**Scoring Logic:** None detected

### intermarket.py
**Purpose:** Intermarket Analysis ====================== Analyze relationships between markets.
**Data Fields Fetched:** BONDS, SPY, Close, GOLD, DXY, VIX, OIL
**Scoring Logic:** None detected

### keepalive.py
**Purpose:** Keep-Alive Module - Oracle Cloud Free Tier Anti-Idle ===================================================== Prevents Oracle Cloud from reclaiming idle instances.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### kelly_criterion.py
**Purpose:** Kelly Criterion Position Sizing ================================= Mathematically optimal position sizing.
**Data Fields Fetched:** pnl_pct
**Scoring Logic:** None detected

### kis_client.py
**Purpose:** KISClient - Korea Investment & Securities API Client ===================================================== Handles authentication, token management, and trading operations.
**Data Fields Fetched:** evlu_pfls_rt, frcr_ord_psbl_amt1, created_at, max_qty, rt_cd, tot_evlu_pfls_amt, output1, tr_crcy_cd, ord_dt, expires_at, frcr_pchs_amt1, ovrs_item_name, available_usd, output, purchase_amount
**Scoring Logic:** None detected

### kis_data.py
**Purpose:** KIS Data Provider ================== 한국투자증권 API를 통한 해외주식 데이터 조회 모듈.
**Data Fields Fetched:** pvol, rate, tvol, sctr_cd, xymd, change_pct, rt_cd, output1, high, seln_str, ordy, diff, clos, output, upjn_nm
**Scoring Logic:** None detected

### kis_integration.py
**Purpose:** KIS API Integration ===================== 한국투자증권 해외주식 실제 매매 연동
**Data Fields Fetched:** pchs_avg_pric, pdno, last, ovrs_now_pric1, output, rt_cd, output1, hldg_qty, ODNO, msg1
**Scoring Logic:** None detected

### liquidity_analyzer.py
**Purpose:** Liquidity Analyzer =================== Analyze market liquidity to avoid slippage and detect traps.
**Data Fields Fetched:** Close, sharesOutstanding, Volume, Low, floatShares, High
**Scoring Logic:** +30, +10, +15, +20, +5, +25

### liquidity_filter.py
**Purpose:** Liquidity Filter ================== Avoid illiquid stocks that are hard to exit.
**Data Fields Fetched:** Volume, ask, Close, bid
**Scoring Logic:** None detected

### local_audit.py
**Purpose:** Comprehensive local source code audit for the KIS auto-trading bot. Checks all Python module files for common bugs WITHOUT needing SSH.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### local_composite_signal.py
**Purpose:** Composite Signal Engine (Master Integrator) ============================================= Combines ALL filters into a single trading decision.
**Data Fields Fetched:** technical, sentiment, risk, Close, signals, macro, Volume, Low, smart_money, High, fundamental
**Scoring Logic:** +30, -30, -35, -20, -80, -15, -25, +20, -10, -40, +25, -60

### local_macro.py
**Purpose:** Enhanced Macro Analyzer ======================== Multi-factor macro regime detection for optimal position sizing.
**Data Fields Fetched:** gold, spy, hyg, hyg_lqd, put_call, Close, lqd, breadth, tnx, dxy, gld, vix
**Scoring Logic:** None detected

### local_momentum_ranking.py
**Purpose:** Cross-Sectional Momentum Ranking ================================== Rank stocks by momentum for relative strength trading.
**Data Fields Fetched:** momentum, ret_3m, ret_1m, percentile, ret_12m, ret_6m, Close, tier
**Scoring Logic:** None detected

### local_screener.py
**Purpose:** Enhanced Dynamic Screener (KIS API Native) ============================================ Multi-factor stock screening using KIS API data.
**Data Fields Fetched:** short_float, averageVolume, rate, tvol, Volume, Low, regularMarketPrice, regularMarketChangePercent, shortPercentOfFloat, Semis, High, rel_volume, Nasdaq, last, implied_vol
**Scoring Logic:** +8, +10, +15, +3, +5, +6, +7, +4, +12

### long_term_backtest_vs_qqq.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** trailingEps, peg, pegRatio, eps, Close, Volume, Low, earningsGrowth, sector, High
**Scoring Logic:** +20, +15

### macro.py
**Purpose:** Enhanced Macro Analyzer ======================== Multi-factor macro regime detection for optimal position sizing.
**Data Fields Fetched:** gold, spy, hyg, hyg_lqd, put_call, Close, lqd, breadth, tnx, dxy, gld, vix
**Scoring Logic:** None detected

### macro_shield.py
**Purpose:** Macro-Defense Shield: Multi-Dimensional Macro Risk Management System ===================================================================== Institutional-grade risk filter system for algorithmic trading.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### main.py
**Purpose:** KIS Auto-Trading Bot - Master Entrypoint ======================================== Delegates the entire execution lifecycle (130+ Modules) to the BotOrchestrator.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### main_autonomous.py
**Purpose:** Autonomous Trading Main Loop =============================== 24/7 autonomous trading with all filters.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### main_remote.py
**Purpose:** KIS Auto-Trading Bot - Master Entrypoint ======================================== Delegates the entire execution lifecycle (130+ Modules) to the BotOrchestrator.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### manipulation_defense.py
**Purpose:** Manipulation Defense System ============================== Detect and defend against institutional manipulation.
**Data Fields Fetched:** Open, Close, Volume, Low, High
**Scoring Logic:** None detected

### manual_analyze.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### manual_sell_pltd.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### manual_sell_robust.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### market_beating_backtest.py
**Purpose:** MARKET-BEATING BACKTEST ======================== Strategy: Always invested, filters adjust position size and stop levels
**Data Fields Fetched:** trades, benchmark_return, geopolitical, seasonality, Volume, Low, alpha, High, global_macro, total_return, psychology, 3yr, 1yr, crypto, final_capital
**Scoring Logic:** None detected

### market_breadth.py
**Purpose:** Market Breadth Analyzer ========================= Analyze market-wide participation and internal strength.
**Data Fields Fetched:** Low, Close, High
**Scoring Logic:** -30, +10, -25, +20, -10, +25

### market_internals.py
**Purpose:** Market Internals Analyzer =========================== Analyze market-wide breadth and internals.
**Data Fields Fetched:** Volume, Close
**Scoring Logic:** +10, -15, -25, +20, -10, +25

### market_psychology.py
**Purpose:** Market Psychology Analyzer ============================ Analyze crowd psychology and sentiment.
**Data Fields Fetched:** ad, Close, hl, level
**Scoring Logic:** None detected

### mean_reversion.py
**Purpose:** Mean Reversion Detector ========================= Detect overextended moves likely to reverse.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### ml_predictor.py
**Purpose:** ML Predictor ============== Machine learning price predictions.
**Data Fields Fetched:** ret_5d, rsi, target, ret_1d, sma5_ratio, Close, vol_ratio, Volume, volatility, bb_pct, Low, sma50_ratio, ret_10d, sma20_ratio, High
**Scoring Logic:** None detected

### momentum_ranking.py
**Purpose:** Cross-Sectional Momentum Ranking ================================== Rank stocks by momentum for relative strength trading.
**Data Fields Fetched:** momentum, ret_3m, ret_1m, percentile, ret_12m, ret_6m, Close, tier
**Scoring Logic:** None detected

### monte_carlo.py
**Purpose:** Monte Carlo Trade Simulator ============================== Simulate trade outcomes for risk assessment.
**Data Fields Fetched:** avg_loss, avg_win, win_rate
**Scoring Logic:** None detected

### multi_stock_backtest.py
**Purpose:** MULTI-STOCK PORTFOLIO BACKTESTER ================================= - Full stock screening across multiple universes
**Data Fields Fetched:** annual_return, total_return, total_trades, benchmark_return, rebalances, Close, alpha, Volume, final_holdings, 1yr_top50, 3yr_top50, 1yr_momentum, final_capital, max_drawdown
**Scoring Logic:** None detected

### multi_timeframe.py
**Purpose:** Multi-Timeframe Confluence ============================ Confirm signals across multiple timeframes.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### news_analyzer.py
**Purpose:** News Sentiment Analyzer ======================== Real-time news analysis for trading signals.
**Data Fields Fetched:** providerPublishTime, content, title, headline, publisher, yfinance._original, source, datetime
**Scoring Logic:** None detected

### notification.py
**Purpose:** Notification System ===================== Send alerts via Telegram, Discord, etc.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### notifier.py
**Purpose:** Notifier Module - Telegram Alerts ================================== Real-time notifications for trades, alerts, and daily reports.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### oil_impact.py
**Purpose:** Oil Price Impact Analyzer ============================ Oil price impact on stocks and economy.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### options_flow.py
**Purpose:** Options Flow Analyzer ====================== Institutional-grade options market intelligence for the trading bot.
**Data Fields Fetched:** strike, openInterest, dist
**Scoring Logic:** -4, -8, +2, -3, +5, +6, +4, -5

### options_metrics.py
**Purpose:** Options Metrics Module ====================== Max Pain, GEX (Gamma Exposure), Put/Call Ratio, and other options-based signals.
**Data Fields Fetched:** volume, aggregate_gex, Close, strike, gamma, regularMarketPrice, market_signal, openInterest, currentPrice
**Scoring Logic:** +8, +10, +15, -10, +5, -5

### orchestrator.py
**Purpose:** Grand Orchestrator v2 ===================== Controls the 6-Phase Lifecycle of the complete 130-module trading bot.
**Data Fields Fetched:** config, regime, summary, Close, risk_score, Low, High
**Scoring Logic:** None detected

### orchestrator_remote.py
**Purpose:** Grand Orchestrator v2 ===================== Controls the 6-Phase Lifecycle of the complete 130-module trading bot.
**Data Fields Fetched:** config, summary, risk_score, regime
**Scoring Logic:** None detected

### order_flow.py
**Purpose:** Order Flow Analyzer ==================== Analyze buy/sell pressure and order flow imbalance.
**Data Fields Fetched:** Volume, Low, Close, High
**Scoring Logic:** +30, -30, -20, -25, +20, +25

### parse_logs.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### parse_results.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** FAIL, NO_ANALYZE, PASS
**Scoring Logic:** None detected

### patch_strategy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### performance_attribution.py
**Purpose:** Performance Attribution ========================= Track which strategies and signals work best.
**Data Fields Fetched:** pnl, strategy, best_strategy, trades
**Scoring Logic:** None detected

### performance_diagnosis.py
**Purpose:** Performance Diagnosis System =============================== Analyze why returns are low and recommend fixes.
**Data Fields Fetched:** timestamp, strategy, pnl_pct, max_trades_per_day, regime, trades, use_trailing_stop, total, avg, min_composite_score, profit_target_multiplier, win_rate, count
**Scoring Logic:** None detected

### portfolio.py
**Purpose:** Portfolio Optimizer ==================== Optimize position sizing and correlation management.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

### position_sizer.py
**Purpose:** Optimal Position Sizer (v1.0.8) ================================ Calculate optimal position sizes using advanced quantitative methods:
**Data Fields Fetched:** pnl_pct, Close, confidence
**Scoring Logic:** None detected

### premarket.py
**Purpose:** Pre-market Analysis Module =========================== Monitors pre-market activity for gap-up stocks and volume surges.
**Data Fields Fetched:** pvol, last, tvol, base, t_xprc
**Scoring Logic:** None detected

### price_debug.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### print_report.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### purge_strategy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### query_db.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### query_pltd.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### query_trades.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### quick_deploy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### quick_verify_institutional.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** Volume, signals
**Scoring Logic:** None detected

### read_api_excel.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### read_excel.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### read_info.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### read_kis_api.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### read_params.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### realistic_backtest.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** risk, Open, PnL, price, Close, surge, Volume, Equity, Low, macro_score, ticker, High
**Scoring Logic:** None detected

### realtime_monitor.py
**Purpose:** Real-Time News & Price Alert System ===================================== Detect breaking news and sudden price moves instantly.
**Data Fields Fetched:** Volume, providerPublishTime, Close, title
**Scoring Logic:** None detected

### refresh_universe.py
**Purpose:** 캐시 삭제 후 유니버스 강제 갱신 & 결과 확인
**Data Fields Fetched:** count, updated
**Scoring Logic:** None detected

### regime_detector.py
**Purpose:** Market Regime Detector ======================== Detect current market regime using multiple signals.
**Data Fields Fetched:** Low, Close, High
**Scoring Logic:** +10, -20

### release_valuation_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_base_adapters.py
**Error:** 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte

### remote_check_pos.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_data_proxy.py
**Purpose:** Data Proxy for Monkey Patching yfinance ========================================= This module intercepts calls to `yfinance.download` AND `yfinance.Ticker`
**Data Fields Fetched:** previousClose, averageVolume, marketCap, fiftyTwoWeekHigh, tvol, Volume, regularMarketPrice, revenueGrowth, interval, fiftyTwoWeekLow, last, progress, auto_adjust, base, institutionPercentHeld
**Scoring Logic:** None detected

### remote_diag.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_env_updater.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_kis_data.py
**Purpose:** KIS Data Provider ================== 한국투자증권 API를 통한 해외주식 데이터 조회 모듈.
**Data Fields Fetched:** pvol, rate, tvol, sctr_cd, xymd, change_pct, rt_cd, output1, high, seln_str, ordy, diff, clos, output, upjn_nm
**Scoring Logic:** None detected

### remote_main.py
**Purpose:** KIS Auto-Trading Bot - Master Entrypoint ======================================== Delegates the entire execution lifecycle (130+ Modules) to the BotOrchestrator.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_module_test.py
**Purpose:** DEFINITIVE Full Module Audit Checks: 1. ALL BaseAnalyzer subclasses (what composite_signal actually loads)
**Data Fields Fetched:** note, status, category
**Scoring Logic:** None detected

### remote_query.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_query2.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### remote_watchdog.py
**Purpose:** Watchdog - Auto-restart + Telegram crash alerts Oracle Cloud 24/7 unattended operation
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### repair_imports.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### reporter.py
**Purpose:** Reporter Module - Daily/Weekly Performance Reports ================================================== Generates performance reports and sends via Telegram.
**Data Fields Fetched:** exchange_rate, pnl_pct, buying_power, current, trades, entry, total_value, net_pnl, positions, avg_pnl_pct, avg_daily_pnl_pct, qty, win_rate, total_pnl
**Scoring Logic:** None detected

### reporter_remote.py
**Purpose:** Reporter Module - Daily/Weekly Performance Reports ================================================== Generates performance reports and sends via Telegram.
**Data Fields Fetched:** pnl_pct, buying_power, current, trades, entry, total_value, net_pnl, positions, avg_pnl_pct, avg_daily_pnl_pct, qty, win_rate, total_pnl
**Scoring Logic:** None detected

### research_discovery.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### reset_server_bot.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### risk_manager.py
**Purpose:** Risk Manager - Daily Stop Loss & Position Limits ================================================= Manages trading risk with daily limits, consecutive loss detection,
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### run_remote_test.py
**Purpose:** Upload and run the definitive 3-section module audit.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### run_verify.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### scan_overseas_apis.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### scheduler.py
**Purpose:** Scheduler & Market Hours ========================== Handle trading hours and scheduled tasks.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### schema_check.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### screener.py
**Purpose:** Enhanced Dynamic Screener (KIS API Native) ============================================ Multi-factor stock screening using KIS API data.
**Data Fields Fetched:** short_float, averageVolume, rate, surprise_pct, is_squeezing, direction, Volume, regularMarketPrice, days_since_earnings, shortPercentOfFloat, High, rel_volume, last, bandwidth_pct, eps_surprise_pct
**Scoring Logic:** +10, -15, +3, +15, +20, +40, -10, +5, +7

### seasonality.py
**Purpose:** Seasonality Analyzer ====================== Monthly and weekly trading patterns.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sector_fund_flow.py
**Purpose:** Sector Fund Flow Monitor ========================= Tracks real-time capital rotation between market sectors using ETF price
**Data Fields Fetched:** Close, sector
**Scoring Logic:** None detected

### sector_rotation.py
**Purpose:** Sector Rotation Analyzer ========================= Track money flow between market sectors.
**Data Fields Fetched:** Volume, sector, Close
**Scoring Logic:** None detected

### sector_rotator.py
**Purpose:** Sector Rotator ================ Automatic sector rotation based on momentum.
**Data Fields Fetched:** SPY, Close, Sector, sector, RS
**Scoring Logic:** None detected

### sector_verify.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sell_hst_bounded.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sell_hst_exact.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** last, rt_cd, output, tvar
**Scoring Logic:** None detected

### sell_hst_final.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** last, output
**Scoring Logic:** None detected

### sell_hst_native.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sell_hst_only.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sell_hst_portfolio_price.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sell_pltd_final.py
**Purpose:** Final PLTD sell script - uses Trader internals for auth, tries all exchange codes.
**Data Fields Fetched:** rt_cd, ODNO, msg1, output
**Scoring Logic:** None detected

### sell_sqqq_manual.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### sentiment.py
**Purpose:** Sentiment Analysis Module ========================== Analyze market sentiment from multiple sources.
**Data Fields Fetched:** value_classification, Close, pchg, Volume, data
**Scoring Logic:** +30, -30, +10, -15, +15, -10, -5

### server_balance_check.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_base_adapters.py
**Error:** 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte

### server_base_adapters_utf8.py
**Purpose:** Universal Adapters for 130+ Modules ==================================== Auto-discovers ALL Python modules in the project, wraps their classes
**Data Fields Fetched:** regime, data, is_squeezing, Close, price, signals, risk_score, df, new_capital, capital, current_price, ticker
**Scoring Logic:** None detected

### server_check_db_v2.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_check_strategy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_composite_signal.py
**Error:** 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte

### server_composite_signal_utf8.py
**Purpose:** Composite Signal Engine (Master Integrator) ============================================= Combines ALL filters into a single trading decision.
**Data Fields Fetched:** technical, sentiment, risk, Close, signals, macro, Volume, Low, smart_money, High, fundamental
**Scoring Logic:** +30, -30, -35, -20, -15, -25, +20, -10, -40, +25

### server_diag.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_diag_final.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_diag_v3.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_final_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_hard_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** signals
**Scoring Logic:** None detected

### server_lite_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_module_check.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** total, by_category
**Scoring Logic:** None detected

### server_print_balance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** pchs_avg_pric, now_pric2, output1, ovrs_cblc_qty, ovrs_pdno
**Scoring Logic:** None detected

### server_raw_balance.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** OVRS_EXCG_CD
**Scoring Logic:** None detected

### server_read_db.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_risk_manager_live.py
**Error:** 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte

### server_signal_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_ticker_audit.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_verify_fix.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### server_verify_simple.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### setup_logrotate.py
**Purpose:** setup_logrotate.py 서버에서 실행하면 logrotate 설정을 자동으로 구성합니다. - 매일 자정 로그 회전
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### setup_watchdog.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### short_squeeze.py
**Purpose:** Short Squeeze Monitor ====================== Detects potential short squeeze setups:
**Data Fields Fetched:** shortPercentOfFloat, Close, shortRatio
**Scoring Logic:** +10, +15, -10, +5, +35, +25

### signal_aggregator.py
**Purpose:** Signal Aggregator - Advanced Signal Integration Engine ====================================================== Performs 6 advanced analyses to calculate a bonus score for trading signals.
**Data Fields Fetched:** Open, Close, signals, Volume, Low, High
**Scoring Logic:** +8, -8, -4, -6, +5, +6, +4, -5

### simple_audit.py
**Purpose:** Simple Import + Basic Function Audit — saves results to audit_output.txt
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### smart_money.py
**Purpose:** Smart Money Tracking Module ============================ Track institutional activity through dark pool prints,
**Data Fields Fetched:** Volume, Close, Open
**Scoring Logic:** +30, -30, +10, +15, -25, +25

### smart_order.py
**Purpose:** Smart Order Execution ====================== Minimize slippage and optimize order execution.
**Data Fields Fetched:** odno, order_id, fill_price
**Scoring Logic:** None detected

### social_sentiment.py
**Purpose:** Social Sentiment Analyzer =========================== Analyze sentiment from social media and web sources.
**Data Fields Fetched:** Volume, Close
**Scoring Logic:** +30, -30, -20, +10, -15, +15

### squeeze_detector.py
**Purpose:** Squeeze Detector ================= Detect short squeeze and gamma squeeze potential.
**Data Fields Fetched:** Close, sharesOutstanding, Volume, floatShares, sharesShort
**Scoring Logic:** +30, +10, +15, +20, +40, +5, +25

### stat_arb.py
**Purpose:** Statistical Arbitrage Engine ============================== Detect mean-reversion and relative value opportunities.
**Data Fields Fetched:** market, stock, Close
**Scoring Logic:** -30, +10, +15, +40, +25

### statistical_arbitrage.py
**Purpose:** Statistical Arbitrage & Cointegration Engine =========================================== Identifies temporary pricing spreads between historically correlated assets.
**Data Fields Fetched:** Close, signals
**Scoring Logic:** None detected

### strategy.py
**Purpose:** Enhanced Strategy Engine with Advanced Indicators ================================================== Multi-factor entry/exit strategy with time-based adaptation.
**Data Fields Fetched:** High, Open, eps_surprise_pct, failed, Close, beat_surprise, entry_time, days_since_earnings, Volume, passed
**Scoring Logic:** +8, +10, +15, -3, +5, +6, +4, -5, +12

### strategy_full_test.py
**Purpose:** 전략 로직 완전 기능 검증 스크립트 ===================================== 각 가드/전략이 실제로 올바른 결과를 내는지 end-to-end 검증
**Data Fields Fetched:** total_trades, Open, Close, Low, total_pnl, profit_factor, win_rate, High
**Scoring Logic:** None detected

### stress_test.py
**Purpose:** Portfolio Stress Test ======================== Test portfolio under extreme scenarios.
**Data Fields Fetched:** corr, vol_mult, desc, recovery, drop
**Scoring Logic:** None detected

### support_resistance.py
**Purpose:** Support/Resistance Analyzer ============================ Identify key price levels for entry/exit optimization.
**Data Fields Fetched:** Volume, Low, Close, High
**Scoring Logic:** None detected

### sync_db_manual_sell.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### tail_risk.py
**Purpose:** Tail Risk & Black Swan Protection ==================================== Detect and protect against extreme market events.
**Data Fields Fetched:** Close
**Scoring Logic:** -20, -15, -50, -25

### targeted_verify.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### tax_optimizer.py
**Purpose:** Tax Optimizer (Tax-Loss Harvesting) ===================================== Optimize taxes through strategic selling.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### technical_analyzer.py
**Purpose:** Technical Analyzer ==================== Comprehensive technical analysis.
**Data Fields Fetched:** Volume, Low, Close, High
**Scoring Logic:** -20, +10, -15, +15, -25, +20, -10, +25, -5

### telegram_commander.py
**Purpose:** telegram_commander.py ====================== 텔레그램에서 명령어를 입력하면 봇이 실시간으로 응답합니다.
**Data Fields Fetched:** update_id, text, reply_markup, chat, callback_query, message, result, data, id
**Scoring Logic:** None detected

### test_adapters.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_api.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** ovrs_cblc_qty, access_token, output1, ovrs_pdno
**Scoring Logic:** None detected

### test_critical.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_exposure.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_fetch.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_finnhub.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_get_price.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_kis_api.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** output1, msg1, prpr, symb
**Scoring Logic:** None detected

### test_kis_api_exact.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_pltd_price.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** rt_cd, msg1, output, last
**Scoring Logic:** None detected

### test_pltd_prices_final.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_priority.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_screener.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_signal_remote.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### test_ticker_shim.py
**Purpose:** Test all yf.Ticker modules — safe version that catches any return type
**Data Fields Fetched:** regularMarketPrice
**Scoring Logic:** None detected

### test_valuation_scoring.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### trace.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** system_setup
**Scoring Logic:** None detected

### trace_sofi_signal.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### trade.py
**Purpose:** Trade Manager for KIS API Handles order execution, position management, and account queries
**Data Fields Fetched:** tvol, xymd, rt_cd, output1, frcr_dncl_amt_2, high, clos, output, ODNO, ovrs_cblc_qty, output2, pchs_avg_pric, last, tr_id, msg1
**Scoring Logic:** None detected

### trade_journal.py
**Purpose:** Trade Journal & Logging ========================= Log all trades for analysis and review.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### trader.py
**Purpose:** Trader Module - Execution & Money Management ============================================= Handles KIS API integration with exchange mapping,
**Data Fields Fetched:** OVRS_EXCG_CD, bvol, frcr_ord_psbl_amt1, rt_cd, output1, side, ovrs_pdno, expires_at, order_id, pbid1, output, pask1, ovrs_ord_psbl_amt, ODNO, ovrs_cblc_qty
**Scoring Logic:** None detected

### trailing_stop.py
**Purpose:** Advanced Trailing Stop ======================== Protect profits with dynamic trailing stops.
**Data Fields Fetched:** highest_price, stop_pct, entry_price
**Scoring Logic:** None detected

### trigger_reports_server.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### troubleshoot_hang.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### truly_ultimate_backtest.py
**Purpose:** TRULY ULTIMATE BACKTESTER - ALL 100+ MODULES ============================================== Integrates EVERY single module for maximum intelligence.
**Data Fields Fetched:** oil, breakout, trades, benchmark_return, geopolitical, seasonality, Volume, Low, 1yr_agg, trend, type, alpha, reason, win_rate, High
**Scoring Logic:** +10, -10

### try_sell_variations.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** rt_cd, ODNO, msg1, output
**Scoring Logic:** None detected

### ultimate_94_backtest.py
**Purpose:** Ultimate 130-Module Backtester ============================== Simulates the real CompositeSignalEngine logic over historical data.
**Data Fields Fetched:** entry_price, Close, shares, pnl, sl, tp, entry_date
**Scoring Logic:** None detected

### ultimate_backtest.py
**Purpose:** ULTIMATE INTEGRATED BACKTESTER ================================= Uses ALL 100+ filters for maximum intelligence.
**Data Fields Fetched:** trades, benchmark_return, Volume, Low, type, alpha, crypto_sentiment, psychology_score, geopolitical_risk, win_rate, High, total_return, macro_score, final_capital, max_drawdown
**Scoring Logic:** +10, -10

### ultimate_module_check.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** signals
**Scoring Logic:** None detected

### ultra_aggressive_backtest.py
**Purpose:** ULTRA-AGGRESSIVE MARKET-BEATING BACKTESTER ============================================ Goal: BEAT S&P500 by a significant margin
**Data Fields Fetched:** global_macro, annual_return, total_return, momentum, ml, leverage, modules_used, trades, benchmark_return, instance, Close, alpha, Volume, Low, final_capital
**Scoring Logic:** None detected

### universe.py
**Purpose:** Russell 1000 유니버스 (동적 + 캐시) ==================================== 1000대 미국 대형주에서 스크리닝합니다.
**Data Fields Fetched:** symbols, count, updated
**Scoring Logic:** None detected

### updater.py
**Purpose:** AI 스윙 트레이딩 봇 - 지능형 자동 업데이트 엔진 (updater.py) ====================================================== 사용자가 깃허브(GitHub) 등에 최신 전략 코드를 올려두면,
**Data Fields Fetched:** files, version
**Scoring Logic:** None detected

### utils.py
**Purpose:** Utility functions for KIS Trading Bot
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### verify_fixes.py
**Purpose:** 수정사항 검증 스크립트 ====================== 실제 API 호출로 주요 버그 수정을 확인합니다.
**Data Fields Fetched:** errors, pass, fail
**Scoring Logic:** None detected

### verify_guards.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### verify_strategy.py
**Purpose:** No docstring provided.
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### vix_structure.py
**Purpose:** VIX Structure Analyzer ======================== Analyze VIX term structure for volatility regime insights.
**Data Fields Fetched:** Close
**Scoring Logic:** +30, -20, -25, +20, -10

### volume_profile.py
**Purpose:** Volume Profile Analyzer ========================= Analyze volume distribution at price levels.
**Data Fields Fetched:** volume, Close, price, Volume, Low, High
**Scoring Logic:** +30, -15, +15, +20, -10

### watchdog.py
**Purpose:** Watchdog - Auto-restart + Telegram crash alerts Oracle Cloud 24/7 unattended operation
**Data Fields Fetched:** None directly parsed
**Scoring Logic:** None detected

### winrate_optimizer.py
**Purpose:** Win Rate Optimizer ==================== Maximize win rate through signal quality filters.
**Data Fields Fetched:** trend, momentum, volume, regime, risk_reward, timing
**Scoring Logic:** None detected

### yen_carry.py
**Purpose:** Yen Carry Trade Monitor ========================== Monitor yen carry trade unwinding risk.
**Data Fields Fetched:** Close
**Scoring Logic:** None detected

