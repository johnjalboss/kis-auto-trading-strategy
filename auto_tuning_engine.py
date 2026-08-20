"""
World-Class Institutional Quant Auto-Tuning Engine (auto_tuning_engine.py)
========================================================================
Continuously analyzes real closed trade executions, win rate, profit factor,
loss attribution root causes, and market regime to autonomously optimize:
  - MIN_ENTRY_SCORE (Entry strictness: 75 ~ 88)
  - STOP_LOSS_PCT (Safety stop floor: 3.5% ~ 5.5%)
  - TAKE_PROFIT_PCT (Trailing profit target: 8.0% ~ 15.0%)
  - MAX_POSITION_PCT (Capital allocation per slot: 15% ~ 30%)
  - RVOL_MIN (Relative volume surge filter: 1.3x ~ 2.5x)
  - MAX_RSI_ENTRY (Anti-climax cap: 65 ~ 75)
"""

import os
import sqlite3
import math
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from loguru import logger
import config

CONFIG_OVERRIDE_FILE = "autotune_config.json"

def load_autotune_overrides():
    """Dynamically applies autotuned parameters into in-memory config."""
    if os.path.exists(CONFIG_OVERRIDE_FILE):
        try:
            with open(CONFIG_OVERRIDE_FILE, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            for k, v in overrides.items():
                if hasattr(config, k):
                    setattr(config, k, v)
            return overrides
        except Exception as e:
            logger.debug("Failed loading autotune overrides: {}", e)
    return {}

class AutoTuningEngine:
    """Institutional-Grade Self-Optimizing Quant Parameter Tuner"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
        self.config_override_file = CONFIG_OVERRIDE_FILE
        
    def _get_db_connection(self):
        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        return None

    def analyze_loss_root_causes(self, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Deep Root Cause Attribution for all losing trades:
        1. FALSE_BREAKOUT: Volume died immediately after entry
        2. OVERBOUGHT_CLIMAX: Entered at extreme high / overbought RSI
        3. MARKET_SHOCK: Market regime was Risk-Off / Bearish
        4. WHIPSAW_STOP: Premature exit on minor noise before rebound
        """
        conn = self._get_db_connection()
        if not conn:
            return {"loss_count": 0, "root_causes": {}}

        cur = conn.cursor()
        RESET_DATE = "2026-08-14"
        since_date = max(RESET_DATE, (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d"))

        cur.execute("""
            SELECT symbol, quantity, price, pnl, pnl_pct, setup_reason as reason, regime, created_at 
            FROM trade_details 
            WHERE side = 'SELL' AND pnl < 0 AND date(created_at) >= ?
            UNION ALL
            SELECT symbol, quantity, price, pnl, pnl_pct, reason, regime, created_at 
            FROM trades 
            WHERE side = 'SELL' AND pnl < 0 AND date(created_at) >= ?
            ORDER BY created_at ASC
        """, (since_date, since_date))
        losses = cur.fetchall()
        conn.close()

        causes = {
            "FALSE_BREAKOUT": 0,
            "OVERBOUGHT_CLIMAX": 0,
            "MARKET_SHOCK": 0,
            "WHIPSAW_STOP": 0,
            "DEAD_MONEY": 0,
            "OTHER": 0
        }

        for l in losses:
            reason = (l['reason'] or "").upper()
            regime = (l['regime'] or "").upper()
            pnl_pct = l['pnl_pct'] or 0.0

            if "BEAR" in regime or "RISK_OFF" in regime or "PANIC" in reason:
                causes["MARKET_SHOCK"] += 1
            elif "DEAD_MONEY" in reason or "STAGNANT" in reason:
                causes["DEAD_MONEY"] += 1
            elif "STOP" in reason and abs(pnl_pct) <= 0.035:
                causes["WHIPSAW_STOP"] += 1
            elif "OVERBOUGHT" in reason or "RSI" in reason:
                causes["OVERBOUGHT_CLIMAX"] += 1
            elif "BREAKOUT" in reason or "MOMENTUM" in reason or "FAILED" in reason:
                causes["FALSE_BREAKOUT"] += 1
            else:
                causes["OTHER"] += 1

        return {
            "loss_count": len(losses),
            "root_causes": causes
        }

    def analyze_performance(self, lookback_days: int = 30) -> dict:
        """Calculate deep quant performance metrics from real trades"""
        conn = self._get_db_connection()
        if not conn:
            return {}
            
        cur = conn.cursor()
        RESET_DATE = "2026-08-14"
        since_date = max(RESET_DATE, (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d"))
        
        cur.execute("""
            SELECT symbol, side, quantity, price, pnl, pnl_pct, setup_reason as reason, regime, created_at 
            FROM trade_details 
            WHERE side = 'SELL' AND date(created_at) >= ?
            UNION ALL
            SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, regime, created_at 
            FROM trades 
            WHERE side = 'SELL' AND date(created_at) >= ?
            ORDER BY created_at ASC
        """, (since_date, since_date))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            return {
                "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
                "expectancy": 0.0, "avg_win": 0.0, "avg_loss": 0.0
            }
            
        wins = [r['pnl'] for r in rows if r['pnl'] > 0]
        losses = [r['pnl'] for r in rows if r['pnl'] < 0]
        total_pnl = sum(r['pnl'] for r in rows)
        
        n_trades = len(rows)
        n_wins = len(wins)
        n_losses = len(losses)
        
        win_rate = (n_wins / n_trades * 100.0) if n_trades > 0 else 0.0
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        avg_win = (gross_profit / n_wins) if n_wins > 0 else 0.0
        avg_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
        expectancy = (total_pnl / n_trades) if n_trades > 0 else 0.0
        
        return {
            "total_trades": n_trades,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_pnl": total_pnl,
            "expectancy": expectancy,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }

    def run_autotune(self) -> dict:
        """
        Execute Institutional Precision Auto-Tuning Logic:
        Dynamically adjusts entry threshold, stop loss, profit target, and position sizing
        based on both global metrics and granular root-cause loss attribution.
        """
        metrics = self.analyze_performance(lookback_days=30)
        loss_analysis = self.analyze_loss_root_causes(lookback_days=30)
        logger.info("🤖 AutoTuning Engine running analysis: {} | Loss Root Causes: {}", metrics, loss_analysis)
        
        # Baseline Institutional Parameters
        tuned_params = {
            "MIN_ENTRY_SCORE": 80,
            "STOP_LOSS_PCT": 0.045,
            "TAKE_PROFIT_PCT": 0.090,
            "MAX_POSITION_PCT": 0.25,
            "RVOL_MIN": 1.5,
            "MAX_RSI_ENTRY": 72,
            "TUNED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "REASON": "Baseline Balanced Institutional Harmony"
        }
        
        n_trades = metrics.get("total_trades", 0)
        win_rate = metrics.get("win_rate", 0.0)
        pf = metrics.get("profit_factor", 1.0)
        causes = loss_analysis.get("root_causes", {})
        
        if n_trades >= 3:
            reasons = []
            
            # 1. False Breakout Dominance ➔ Tighten RVOL & Score Filter
            if causes.get("FALSE_BREAKOUT", 0) >= 2:
                tuned_params["RVOL_MIN"] = 2.0
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 83)
                reasons.append("가짜 돌파 방어(RVOL 2.0배 & 컷오프 83점 상향)")
                
            # 2. Overbought Climax Dominance ➔ Lower Max RSI Entry
            if causes.get("OVERBOUGHT_CLIMAX", 0) >= 2:
                tuned_params["MAX_RSI_ENTRY"] = 68
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 82)
                reasons.append("상투 과열 차단(진입 상한 RSI 68로 엄격화)")

            # 3. Whipsaw Stop Dominance ➔ Expand Stop Cushion to avoid premature stopout
            if causes.get("WHIPSAW_STOP", 0) >= 2:
                tuned_params["STOP_LOSS_PCT"] = 0.052
                reasons.append("노이즈 털림 방지(손절 버퍼 5.2% 완충 확대)")

            # 4. Global Win Rate Adjustment
            if win_rate < 50.0 or pf < 1.2:
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 85)
                tuned_params["MAX_POSITION_PCT"] = 0.18
                reasons.append(f"수익률 방어 모드(승률 {win_rate:.1f}% / 85점 컷오프)")
            elif win_rate >= 65.0 and pf >= 1.8:
                tuned_params["TAKE_PROFIT_PCT"] = 0.130
                tuned_params["MAX_POSITION_PCT"] = 0.30
                reasons.append(f"알파 극대화 모드(승률 {win_rate:.1f}% / 익절 +13% 확장)")

            if reasons:
                tuned_params["REASON"] = " + ".join(reasons)

        # Persist tuned parameters to JSON override file
        try:
            with open(self.config_override_file, "w", encoding="utf-8") as f:
                json.dump(tuned_params, f, indent=2, ensure_ascii=False)
            # Apply in-memory immediately
            load_autotune_overrides()
            logger.info("✅ AutoTuning parameters saved and applied in-memory: {} | Reason: {}", tuned_params, tuned_params["REASON"])
        except Exception as e:
            logger.error("Failed to save autotune config: {}", e)
            
        return tuned_params

    def format_telegram_card(self) -> str:
        """Formats the Auto-Tuning results as a beautiful Telegram HTML Card."""
        metrics = self.analyze_performance(lookback_days=30)
        loss_analysis = self.analyze_loss_root_causes(lookback_days=30)
        tuned = self.run_autotune()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        causes_str = ", ".join([f"{k}: {v}건" for k, v in loss_analysis.get('root_causes', {}).items() if v > 0]) or "손실 원인 없음 (100% 승리/초기)"

        card = (
            f"⚙️ <b>[주간 AI 파라미터 자가 튜닝 리포트]</b>\n"
            f"<i>{now_str} (Autonomous Self-Optimization Engine)</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>최근 30일 매매 실적 분석</b>:\n"
            f"  • 전적: {metrics.get('total_trades', 0)}전 {metrics.get('wins', 0)}승 {metrics.get('losses', 0)}패\n"
            f"  • 승률: <b>{metrics.get('win_rate', 0.0):.1f}%</b> | Profit Factor: <b>{metrics.get('profit_factor', 1.0):.2f}</b>\n"
            f"  • 손실 원인 추적: <i>{causes_str}</i>\n\n"
            f"💎 <b>자동 최적화 적용 파라미터</b>:\n"
            f"  • 🎯 <b>진입 최저 점수 (Min Score)</b>: <code>{tuned.get('MIN_ENTRY_SCORE', 80)}점</code>\n"
            f"  • 🛡️ <b>손절선 기준폭 (Stop Loss)</b>: <code>{tuned.get('STOP_LOSS_PCT', 0.045)*100:.1f}%</code>\n"
            f"  • 📈 <b>트레일링 익절폭 (Take Profit)</b>: <code>{tuned.get('TAKE_PROFIT_PCT', 0.090)*100:.1f}%</code>\n"
            f"  • ⚡ <b>수급 폭발 필터 (Min RVOL)</b>: <code>{tuned.get('RVOL_MIN', 1.5):.1f}배</code>\n"
            f"  • 🚫 <b>상투 과열 차단 (Max RSI)</b>: <code>RSI {tuned.get('MAX_RSI_ENTRY', 72)} 이하만 허용</code>\n\n"
            f"🤖 <b>[AI 자율 최적화 판정 사유]</b>:\n"
            f"<i>\"{tuned.get('REASON', 'Baseline Institutional Balance')}\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>이 파라미터는 다음 30초 매매 루프부터 즉시 실시간 인메모리에 100% 자동 적용됩니다.</i>"
        )
        return card

    def send_tuning_report_to_telegram(self) -> bool:
        """Sends the tuning report directly to Telegram."""
        try:
            card_text = self.format_telegram_card()
            
            token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
            if not token or not chat_id:
                env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                if os.path.exists(env_file):
                    from dotenv import load_dotenv
                    load_dotenv(env_file)
                    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
                    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

            if not token or not chat_id:
                logger.warning("Telegram credentials missing. Tuning report cannot be sent.")
                return False

            import requests
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": card_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            resp = requests.post(url, json=payload, timeout=10)
            if resp.ok:
                logger.success("Auto-Tuning report successfully sent to Telegram!")
                return True
            else:
                import re
                clean_text = re.sub(r'<[^>]+>', '', card_text)
                payload["text"] = clean_text
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=10)
                logger.info("Auto-Tuning report sent via plain text fallback.")
                return True
        except Exception as e:
            logger.error("Failed to send tuning report to Telegram: {}", e)
            return False

if __name__ == "__main__":
    tuner = AutoTuningEngine()
    tuner.run_autotune()
    print("AutoTuning test run completed successfully.")
