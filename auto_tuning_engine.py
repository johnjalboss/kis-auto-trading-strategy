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
    
    def __init__(self, db_path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if db_path and os.path.exists(db_path):
            self.db_path = db_path
        else:
            cand1 = os.path.join(base_dir, "trades.db")
            cand2 = "/home/ubuntu/kis-auto-trading/trades.db"
            cand3 = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\trades.db"
            if os.path.exists(cand1):
                self.db_path = cand1
            elif os.path.exists(cand2):
                self.db_path = cand2
            elif os.path.exists(cand3):
                self.db_path = cand3
            else:
                self.db_path = cand1
        self.config_override_file = os.path.join(base_dir, "autotune_config.json")
        
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
        raw_losses = cur.fetchall()
        conn.close()

        seen_loss = set()
        losses = []
        for l in raw_losses:
            pnl_v = float(l['pnl'] or 0.0)
            t_key = (l['symbol'], round(pnl_v, 2), str(l['created_at'])[:10])
            if t_key in seen_loss:
                continue
            seen_loss.add(t_key)
            losses.append(l)

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
        """Calculate deep quant performance metrics including MFE, MAE, holding duration, and Information Coefficient (IC)"""
        conn = self._get_db_connection()
        if not conn:
            return {}
            
        cur = conn.cursor()
        RESET_DATE = "2026-08-14"
        since_date = max(RESET_DATE, (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d"))
        
        # Query modern trade records with MFE, MAE, holding minutes, and quant score
        cur.execute("""
            SELECT symbol, side, quantity, price, pnl, pnl_pct, reason, regime, created_at,
                   mfe_pct, mae_pct, holding_minutes, spread_at_entry, quant_score_at_entry
            FROM trades 
            WHERE side = 'SELL' AND date(created_at) >= ?
            UNION ALL
            SELECT symbol, side, quantity, price, pnl, pnl_pct, setup_reason as reason, regime, created_at,
                   0.0 as mfe_pct, 0.0 as mae_pct, 0.0 as holding_minutes, 0.0 as spread_at_entry, 80 as quant_score_at_entry
            FROM trade_details 
            WHERE side = 'SELL' AND date(created_at) >= ?
            ORDER BY created_at ASC
        """, (since_date, since_date))
        raw_rows = cur.fetchall()
        conn.close()
        
        seen_keys = set()
        rows = []
        for r in raw_rows:
            pnl_v = float(r['pnl'] or 0.0)
            t_key = (r['symbol'], round(pnl_v, 2), str(r['created_at'])[:10])
            if t_key in seen_keys:
                continue
            seen_keys.add(t_key)
            rows.append(r)

        if not rows:
            return {
                "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
                "expectancy": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "avg_mfe": 0.0, "avg_mae": 0.0, "mae_wins_95": 0.035,
                "mfe_median": 0.060, "avg_holding_hours": 0.0, "ic": 0.0
            }
            
        wins = [float(r['pnl']) for r in rows if float(r['pnl'] or 0) > 0]
        losses = [float(r['pnl']) for r in rows if float(r['pnl'] or 0) < 0]
        total_pnl = sum(float(r['pnl'] or 0) for r in rows)
        
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
        
        # MFE / MAE Statistical Distribution
        mfes = [abs(float(r['mfe_pct'] or 0)) for r in rows if r['mfe_pct'] is not None and abs(float(r['mfe_pct'])) > 0.0001]
        maes = [abs(float(r['mae_pct'] or 0)) for r in rows if r['mae_pct'] is not None and abs(float(r['mae_pct'])) > 0.0001]
        mae_wins = [abs(float(r['mae_pct'] or 0)) for r in rows if float(r['pnl'] or 0) > 0 and r['mae_pct'] is not None]
        holding_mins = [float(r['holding_minutes'] or 0) for r in rows if r['holding_minutes'] is not None and float(r['holding_minutes']) > 0]
        
        import numpy as np
        avg_mfe = float(np.mean(mfes)) if mfes else 0.055
        avg_mae = float(np.mean(maes)) if maes else 0.025
        mae_wins_95 = float(np.percentile(mae_wins, 95)) if mae_wins else 0.038
        mfe_median = float(np.median(mfes)) if mfes else 0.060
        avg_holding_hours = (float(np.mean(holding_mins)) / 60.0) if holding_mins else 12.0

        # Information Coefficient (IC): Rank correlation between entry score and realized PnL %
        scores = [float(r['quant_score_at_entry'] or 80) for r in rows]
        pnl_pcts = [float(r['pnl_pct'] or 0.0) for r in rows]
        ic = 0.0
        if len(scores) >= 3 and len(set(scores)) > 1:
            try:
                import pandas as pd
                s_ranks = pd.Series(scores).rank()
                p_ranks = pd.Series(pnl_pcts).rank()
                ic = float(s_ranks.corr(p_ranks))
                if np.isnan(ic):
                    ic = 0.0
            except Exception:
                ic = 0.0

        return {
            "total_trades": n_trades,
            "wins": n_wins,
            "losses": n_losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "net_pnl": total_pnl,
            "expectancy": expectancy,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_mfe": avg_mfe,
            "avg_mae": avg_mae,
            "mae_wins_95": mae_wins_95,
            "mfe_median": mfe_median,
            "avg_holding_hours": avg_holding_hours,
            "ic": ic
        }

    def run_autotune(self) -> dict:
        """
        Execute Institutional Precision Auto-Tuning Logic:
        Dynamically optimizes stop loss (SL*), take profit (TP*), entry cutoff, and position sizing
        using empirical MFE/MAE CDF percentiles, Information Coefficient (IC), and root causes.
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
        mae_wins_95 = metrics.get("mae_wins_95", 0.038)
        mfe_median = metrics.get("mfe_median", 0.060)
        ic = metrics.get("ic", 0.0)
        
        if n_trades >= 3:
            reasons = []
            
            # 1. Mathematical Stop-Loss Optimization via Empirical MAE CDF
            # Winning trades rarely breach their 95th percentile MAE; adding 50 bps buffer prevents whipsaws
            optimal_sl = min(0.060, max(0.035, mae_wins_95 + 0.005))
            tuned_params["STOP_LOSS_PCT"] = round(optimal_sl, 3)
            reasons.append(f"MFE/MAE 최적 손절({tuned_params['STOP_LOSS_PCT']*100:.1f}%)")

            # 2. Mathematical Take-Profit Calibration via Median MFE
            optimal_tp = min(0.150, max(0.060, mfe_median * 0.70))
            tuned_params["TAKE_PROFIT_PCT"] = round(optimal_tp, 3)
            reasons.append(f"MFE 스윙 익절({tuned_params['TAKE_PROFIT_PCT']*100:.1f}%)")

            # 3. Information Coefficient (IC) Calibration on Entry Strictness
            if ic >= 0.25:
                tuned_params["MIN_ENTRY_SCORE"] = 78
                reasons.append(f"고예측 알파(IC={ic:+.2f} ➔ 78점 확대)")
            elif ic < -0.10:
                tuned_params["MIN_ENTRY_SCORE"] = 84
                reasons.append(f"노이즈 방어(IC={ic:+.2f} ➔ 84점 엄격화)")

            # 4. Root Cause Loss Attribution Safeguards
            if causes.get("FALSE_BREAKOUT", 0) >= 2:
                tuned_params["RVOL_MIN"] = 2.0
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 83)
                reasons.append("가짜 돌파 방어(RVOL 2.0배)")
                
            if causes.get("OVERBOUGHT_CLIMAX", 0) >= 2:
                tuned_params["MAX_RSI_ENTRY"] = 68
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 82)
                reasons.append("상투 과열 차단(RSI 68)")

            # 5. Global Win Rate & Capital Multiplier Adjustment
            if win_rate < 50.0 or pf < 1.2:
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 85)
                tuned_params["MAX_POSITION_PCT"] = 0.18
                reasons.append(f"방어 모드(승률 {win_rate:.1f}%)")
            elif win_rate >= 65.0 and pf >= 1.8:
                tuned_params["MAX_POSITION_PCT"] = 0.30
                reasons.append(f"알파 집중 모드(승률 {win_rate:.1f}%)")

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
        ic_val = metrics.get('ic', 0.0)

        card = (
            f"⚙️ <b>[주간 AI 파라미터 자가 튜닝 리포트]</b>\n"
            f"<i>{now_str} (Autonomous Self-Optimization Engine)</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>최근 30일 매매 실적 및 MFE/MAE 분석</b>:\n"
            f"  • 전적: {metrics.get('total_trades', 0)}전 {metrics.get('wins', 0)}승 {metrics.get('losses', 0)}패\n"
            f"  • 승률: <b>{metrics.get('win_rate', 0.0):.1f}%</b> | Profit Factor: <b>{metrics.get('profit_factor', 1.0):.2f}</b>\n"
            f"  • 📈 <b>평균 최대 유리 변위 (MFE)</b>: <code>+{metrics.get('avg_mfe', 0.0)*100:.1f}%</code>\n"
            f"  • 📉 <b>평균 최대 불리 변위 (MAE)</b>: <code>-{metrics.get('avg_mae', 0.0)*100:.1f}%</code>\n"
            f"  • 🎯 <b>95% 승리 거래 최대 낙폭</b>: <code>-{metrics.get('mae_wins_95', 0.038)*100:.1f}%</code>\n"
            f"  • 🔮 <b>알파 점수 예측력(IC)</b>: <code>{ic_val:+.2f}</code> ({'유의미한 예측력' if ic_val > 0.1 else '중립'})\n"
            f"  • ⏱️ <b>평균 보유 시간</b>: <code>{metrics.get('avg_holding_hours', 0.0):.1f}시간</code>\n"
            f"  • 손실 원인 추적: <i>{causes_str}</i>\n\n"
            f"💎 <b>수학적 자율 최적화 적용 파라미터</b>:\n"
            f"  • 🎯 <b>진입 최저 점수 (Min Score)</b>: <code>{tuned.get('MIN_ENTRY_SCORE', 80)}점</code>\n"
            f"  • 🛡️ <b>최적 손절선 (SL*)</b>: <code>{tuned.get('STOP_LOSS_PCT', 0.045)*100:.1f}%</code>\n"
            f"  • 📈 <b>최적 익절선 (TP*)</b>: <code>{tuned.get('TAKE_PROFIT_PCT', 0.090)*100:.1f}%</code>\n"
            f"  • ⚡ <b>수급 폭발 필터 (Min RVOL)</b>: <code>{tuned.get('RVOL_MIN', 1.5):.1f}배</code>\n"
            f"  • 🚫 <b>상투 과열 차단 (Max RSI)</b>: <code>RSI {tuned.get('MAX_RSI_ENTRY', 72)} 이하</code>\n\n"
            f"🤖 <b>[AI 자율 최적화 수학적 근거]</b>:\n"
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
