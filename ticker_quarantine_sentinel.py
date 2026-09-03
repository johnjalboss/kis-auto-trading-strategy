"""
Ticker Quarantine Cooldown Sentinel (ticker_quarantine_sentinel.py)
===================================================================
Prevents toxic whipsaw revenge re-entries:
- Automatically places any stopped-out / loss-exited symbol into a 14-day quarantine cooldown.
- Prevents premature re-entry while the stock's technical base is broken.
- Allows early release only if the stock prints a clean 20-day high breakout with > 2.5x volume surge.
"""

import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from typing import Tuple, Dict, Any, List, Optional
from loguru import logger

QUARANTINE_FILE = "ticker_quarantine.json"

class TickerQuarantineSentinel:
    """14-Day Anti-Whipsaw Loss Quarantine Sentinel"""

    def __init__(self, state_file: Optional[str] = None, cooldown_days: int = 14):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if state_file and os.path.exists(state_file):
            self.state_file = state_file
        else:
            cand1 = os.path.join(base_dir, QUARANTINE_FILE)
            cand2 = f"/home/ubuntu/kis-auto-trading/{QUARANTINE_FILE}"
            cand3 = rf"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\{QUARANTINE_FILE}"
            if os.path.exists(cand1):
                self.state_file = cand1
            elif os.path.exists(cand2):
                self.state_file = cand2
            elif os.path.exists(cand3):
                self.state_file = cand3
            else:
                self.state_file = cand1

        self.cooldown_days = cooldown_days
        self.registry: Dict[str, Any] = self._load_registry()
        self._sync_with_recent_losses()

    def _load_registry(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("Failed to load ticker quarantine registry: {}", e)
        return {}

    def _save_registry(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed to save ticker quarantine registry: {}", e)

    def _sync_with_recent_losses(self):
        """Scans DB and shadow state for any losses within cooldown period."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "trades.db")
        if not os.path.exists(db_path):
            db_path = "/home/ubuntu/kis-auto-trading/trades.db"

        since_date = (date.today() - timedelta(days=self.cooldown_days)).strftime("%Y-%m-%d")
        
        # 1. Sync from DB
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("""
                    SELECT symbol, pnl, pnl_pct, reason, created_at
                    FROM trades
                    WHERE side = 'SELL' AND pnl < 0 AND date(created_at) >= ?
                """, (since_date,))
                for row in cur.fetchall():
                    sym, pnl, pnl_pct, reason, created_at = row
                    self.quarantine_symbol(sym, float(pnl_pct or 0.0), reason or "STOP_LOSS", created_at, save=False)
                conn.close()
            except Exception as e:
                logger.debug("Quarantine DB sync error: {}", e)

        # 2. Sync from Shadow State
        shadow_path = os.path.join(base_dir, "shadow_state.json")
        if not os.path.exists(shadow_path):
            shadow_path = "/home/ubuntu/kis-auto-trading/shadow_state.json"
        if os.path.exists(shadow_path):
            try:
                with open(shadow_path, 'r', encoding='utf-8') as f:
                    s_data = json.load(f)
                for t in s_data.get("closed_trades", []):
                    if float(t.get("pnl", 0.0)) < 0:
                        exit_t = t.get("exit_time", "")
                        if exit_t and exit_t[:10] >= since_date:
                            self.quarantine_symbol(t.get("symbol"), float(t.get("pnl_pct", 0.0)), t.get("reason", "SHADOW_LOSS"), exit_t, save=False)
            except Exception as e:
                logger.debug("Quarantine shadow sync error: {}", e)

        self._save_registry()

    def quarantine_symbol(self, symbol: str, loss_pct: float, reason: str, timestamp: Optional[str] = None, save: bool = True):
        """Places a symbol in 14-day quarantine cooldown."""
        if not symbol:
            return
        t_str = timestamp or datetime.now().isoformat()
        self.registry[symbol] = {
            "quarantined_at": t_str,
            "loss_pct": round(loss_pct, 2),
            "reason": reason,
            "expiry_date": (datetime.fromisoformat(t_str[:19]) + timedelta(days=self.cooldown_days)).strftime("%Y-%m-%d")
        }
        if save:
            self._save_registry()
            logger.warning("🛡️ [TICKER_QUARANTINE] Placed {} in 14-day quarantine until {} (Reason: {}, Loss: {:.1f}%)",
                           symbol, self.registry[symbol]["expiry_date"], reason, loss_pct)

    def is_quarantined(self, symbol: str, df: Optional[Any] = None) -> Tuple[bool, str]:
        """
        Evaluates whether a symbol is currently barred by quarantine.
        Returns: (is_blocked, details)
        """
        if symbol not in self.registry:
            return False, "CLEAR"

        entry = self.registry[symbol]
        q_time_str = entry.get("quarantined_at", "")
        try:
            q_date = datetime.fromisoformat(q_time_str[:19]).date()
            days_elapsed = (date.today() - q_date).days
            days_left = self.cooldown_days - days_elapsed

            if days_left <= 0:
                del self.registry[symbol]
                self._save_registry()
                return False, "QUARANTINE_EXPIRED"

            # Check for rare exceptional early release breakout (20-day high with 2.5x volume)
            if df is not None and len(df) >= 21 and 'Close' in df.columns and 'Volume' in df.columns:
                c = float(df['Close'].iloc[-1])
                h20 = float(df['High'].iloc[-21:-1].max()) if 'High' in df.columns else float(df['Close'].iloc[-21:-1].max())
                c_vol = float(df['Volume'].iloc[-1])
                avg_vol = float(df['Volume'].iloc[-21:-1].mean()) if len(df) >= 21 else 1.0
                if c > h20 and (c_vol / max(avg_vol, 1.0)) >= 2.5:
                    logger.info("🔓 [TICKER_QUARANTINE] Early Release for {}: Massive 20d breakout (Vol: {:.1f}x)",
                                symbol, c_vol / max(avg_vol, 1.0))
                    del self.registry[symbol]
                    self._save_registry()
                    return False, "EARLY_RELEASE_MASSIVE_BREAKOUT"

            return True, f"QUARANTINED_COOLDOWN (D-{days_left}일 남음, 사유: {entry.get('reason', '손절')})"
        except Exception as e:
            logger.debug("Quarantine check error for {}: {}", symbol, e)
            return False, "CLEAR_ON_ERROR"

    def get_quarantine_summary(self) -> List[Dict[str, Any]]:
        """Returns list of currently quarantined tickers."""
        res = []
        today = date.today()
        to_del = []
        for sym, data in self.registry.items():
            try:
                q_date = datetime.fromisoformat(data["quarantined_at"][:19]).date()
                days_left = self.cooldown_days - (today - q_date).days
                if days_left > 0:
                    res.append({
                        "symbol": sym,
                        "days_left": days_left,
                        "reason": data.get("reason", "손절"),
                        "loss_pct": data.get("loss_pct", 0.0),
                        "expiry": data.get("expiry_date", "")
                    })
                else:
                    to_del.append(sym)
            except Exception:
                pass
        for s in to_del:
            if s in self.registry:
                del self.registry[s]
        if to_del:
            self._save_registry()
        return sorted(res, key=lambda x: x["days_left"])

# Singleton
_sentinel = None
def get_ticker_quarantine_sentinel() -> TickerQuarantineSentinel:
    global _sentinel
    if _sentinel is None:
        _sentinel = TickerQuarantineSentinel()
    return _sentinel