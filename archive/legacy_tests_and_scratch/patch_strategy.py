import re

def rewrite_strategy():
    with open('strategy.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove fetch_intraday_data method
    content = re.sub(r'    def fetch_intraday_data\(self.*?    # ==============================================.*?    # Entry Logic', 
                     r'    # ==============================================\n    # Entry Logic', 
                     content, flags=re.DOTALL)
    
    # 2. Rewrite check_entry
    new_check_entry = '''    def check_entry(self, symbol: str, macro_score: float = 0, is_screened: bool = False) -> EntrySignal:
        """
        PURE SWING TRADING ENTRY LOGIC
        """
        if symbol in self._positions:
            return EntrySignal("HOLD", 0, "Already in position", 0)
        
        if macro_score < -20:
            return EntrySignal("HOLD", 0, f"Macro too risky: {macro_score:.0f}", 0)
        
        try:
            vix_snap = get_vix_snapshot()
            if vix_snap.regime == "EXTREME":
                return EntrySignal("HOLD", 0, f"VIX extreme ({vix_snap.vix:.1f}) — market crash mode", 0)
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        _bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        current_regime = getattr(self, '_last_regime', '')
        if current_regime in _bear_regimes:
            _allowed_in_bear = getattr(config, 'INVERSE_ETFS', set()) | getattr(config, 'DEFENSIVE_UNIVERSE_SET', set())
            if symbol not in _allowed_in_bear:
                return EntrySignal("HOLD", 0, f"BEAR_REGIME_BLOCK: {current_regime} — only inverse/defensive allowed", 0)

        # 🛡️ EARNINGS GUARD
        try:
            from earnings_calendar import get_earnings_calendar
            ec = get_earnings_calendar()
            e_info = ec.check(symbol)
            if e_info.recommendation == "AVOID":
                return EntrySignal("HOLD", 0, f"EARNINGS_GUARD: {symbol} 실적 {e_info.days_until}일 후 — 진입 차단", 0)
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        # 📅 ECON GUARD
        try:
            from economic_calendar import get_economic_calendar
            econ_cal = get_economic_calendar()
            today_events = econ_cal.get_todays_events() if hasattr(econ_cal, 'get_todays_events') else []
            high_impact = [e for e in today_events if getattr(e, 'impact', '') == 'HIGH']
            if high_impact:
                return EntrySignal("HOLD", 0, f"ECON_EVENT_GUARD: 고임팩트 경제지표 발표일 — 변동성 위험", 0)
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        # 👔 INSIDER GUARD
        try:
            from insider_tracker import get_insider_tracker
            insider = get_insider_tracker()
            ins_result = insider.analyze(symbol)
            if ins_result.insider_net_value < -5_000_000 and ins_result.insider_sentiment == "SELLING":
                return EntrySignal("HOLD", 0, f"INSIDER_GUARD: 내부자 대규모 매도 — 진입 차단", 0)
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        # 📊 BREADTH GUARD
        try:
            import kis_data as _kd
            _spy_df = _kd.get_daily_ohlcv("SPY", days=25)
            if _spy_df is not None and len(_spy_df) >= 22:
                _spy_close = _spy_df['Close']
                _spy_sma20 = float(_spy_close.rolling(20).mean().iloc[-1])
                _spy_current = float(_spy_close.iloc[-1])
                if _spy_current < _spy_sma20 * 0.995:
                    if symbol not in getattr(config, 'INVERSE_ETFS', set()):
                        return EntrySignal("HOLD", 0, f"BREADTH_GUARD: SPY ${_spy_current:.1f} < SMA20 ${_spy_sma20:.1f}", 0)
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        df_daily = self.fetch_data(symbol)
        if df_daily is None or len(df_daily) < 50:
            return EntrySignal("HOLD", 0, "Insufficient daily data for Swing", 0)

        current_price = float(df_daily['Close'].iloc[-1])
        sma20 = df_daily['Close'].rolling(20).mean().iloc[-1]
        sma50 = df_daily['Close'].rolling(50).mean().iloc[-1]
        structural_uptrend = sma20 > sma50

        from indicators import calculate_rsi, calculate_macd
        rsi_val = float(calculate_rsi(df_daily).iloc[-1])
        
        confidence = 60
        reason = "SWING_BASE"

        # VCP / Breakout Check
        _52w_high = float(df_daily['High'].tail(252).max()) if len(df_daily) >= 252 else float(df_daily['High'].max())
        _pct_from_high = (current_price - _52w_high) / _52w_high
        
        is_breakout = _pct_from_high >= -0.02
        is_pullback = structural_uptrend and (40 <= rsi_val <= 65) and (current_price > sma50)
        
        if is_breakout:
            confidence += 25
            reason = "SWING_BREAKOUT: 52W High Proximity"
        elif is_pullback:
            confidence += 15
            reason = f"SWING_PULLBACK: RSI {rsi_val:.1f}, Trend UP"
        else:
            return EntrySignal("HOLD", 0, "No Swing Setup (Not a Breakout or Pullback)", current_price)

        # Volume confirmation
        vol_recent = float(df_daily['Volume'].iloc[-1])
        vol_avg = float(df_daily['Volume'].iloc[:-1].mean())
        if vol_avg > 0 and vol_recent > vol_avg * 1.5:
            confidence += 10
            
        # PEAD Bonus
        try:
            from earnings_analyzer import get_earnings_analyzer
            _ea = get_earnings_analyzer()
            _earn_result = _ea.analyze(symbol)
            _beat = (_earn_result.get('beat_surprise', 0) or _earn_result.get('eps_surprise_pct', 0)) if isinstance(_earn_result, dict) else 0
            _days = _earn_result.get('days_since_earnings', 99) if isinstance(_earn_result, dict) else 99
            if _beat > 5 and _days <= 30:
                confidence += 15
                reason += f" | PEAD (+{_beat:.0f}%)"
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        confidence = min(100, max(0, confidence))
        cfg = self.get_phase_config()
        min_required = config.SCREENED_MIN_SCORE if is_screened else cfg.min_entry_score
        
        if confidence < min_required:
            return EntrySignal("HOLD", confidence, f"Low confidence: {confidence} (needs {min_required})", current_price)

        return EntrySignal("BUY", confidence, reason, current_price)
'''
    # We will replace from "def check_entry(" up to "def _detect_day_type("
    content = re.sub(r'    def check_entry\(self, symbol: str, macro_score.*?    def _detect_day_type\(self\) -> str:',
                     new_check_entry + '\n\n    def _detect_day_type(self) -> str:',
                     content, flags=re.DOTALL)
                     
    # 3. Rewrite check_exit
    new_check_exit = '''    def check_exit(self, symbol: str, current_price: float) -> ExitSignal:
        """
        PURE SWING TRADING EXIT LOGIC
        """
        if symbol not in self._positions:
            return ExitSignal("HOLD", "No position")
            
        pos = self._positions[symbol]
        
        # Update high water mark
        if current_price > pos.high_since_entry:
            pos.high_since_entry = current_price

        days_held = (datetime.now() - pos.entry_time).days

        # 1. TIME STOP (7 days no profit)
        if days_held >= 7 and current_price < pos.entry_price * 1.03:
            return ExitSignal("SELL", f"TIME_STOP: 7일간 수익 3% 미만 (기회비용 보존)")

        # 2. DYNAMIC TRAILING STOP
        profit_pct = (current_price - pos.entry_price) / pos.entry_price
        if profit_pct > config.TRAILING_TRIGGER_PCT:
            trail_price = pos.high_since_entry * (1.0 - config.TRAILING_STOP_PCT)
            if current_price <= trail_price:
                return ExitSignal("SELL", f"TRAILING_STOP: 고점 대비 {config.TRAILING_STOP_PCT*100:.1f}% 하락 (수익 {profit_pct*100:.1f}%)")

        # 3. HARD STOP LOSS (ATR Based)
        sl_price = pos.entry_price - (pos.atr_at_entry * config.ATR_STOP_MULTIPLIER)
        if current_price <= sl_price:
            return ExitSignal("SELL", f"STOP_LOSS: ATR 기반 손절선 도달 (${sl_price:.2f})")

        # 4. TAKE PROFIT
        tp_price = pos.entry_price * (1.0 + config.TAKE_PROFIT_PCT)
        if current_price >= tp_price:
            return ExitSignal("SELL", f"TAKE_PROFIT: 목표 수익 달성 ({config.TAKE_PROFIT_PCT*100:.1f}%)")

        # 5. STRUCTURAL BREAKDOWN
        try:
            df_daily = self.fetch_data(symbol)
            if df_daily is not None and len(df_daily) >= 50:
                sma50 = float(df_daily['Close'].rolling(50).mean().iloc[-1])
                if current_price < sma50 * 0.98:
                    return ExitSignal("SELL", f"TREND_BROKEN: 50일선 이탈 (${sma50:.2f})")
        except Exception as err:
            print("⚠️ [patch_strategy.py] Fallback triggered:", err)

        return ExitSignal("HOLD", "Holding Swing Position")
'''
    # We will replace from "def check_exit(" up to "def _check_intraday_reversal("
    content = re.sub(r'    def check_exit\(self, symbol: str, current_price: float\) -> ExitSignal:.*?    def _check_intraday_reversal',
                     new_check_exit + '\n\n    def _check_intraday_reversal',
                     content, flags=re.DOTALL)

    # 4. Remove leftover intraday helpers: _detect_day_type, _get_orb_range, _check_intraday_reversal, _calc_intraday_confirmation
    content = re.sub(r'    def _detect_day_type\(self\) -> str:.*?    def _check_entry_filters',
                     r'    def _check_entry_filters',
                     content, flags=re.DOTALL)
                     
    content = re.sub(r'    def _check_intraday_reversal.*?    def _check_stop_loss',
                     r'    def _check_stop_loss',
                     content, flags=re.DOTALL)
                     
    content = re.sub(r'    def _calc_intraday_confirmation.*?    def check_exit',
                     r'    def check_exit',
                     content, flags=re.DOTALL)
                     
    with open('strategy.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    rewrite_strategy()
    print("Done")
