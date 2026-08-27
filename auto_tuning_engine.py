"""
World-Class Institutional Quant Auto-Tuning Engine (auto_tuning_engine.py)
========================================================================
Continuously analyzes real closed trade executions, win rate, profit factor,
loss attribution root causes, asset volatility clusters, and market regime
to autonomously optimize multi-tier parameter matrices:
  - Global Parameters: Min Entry Score, RVOL, Max RSI
  - Cluster-Specific Matrix: High-Vol Growth vs Mid-Vol Momentum vs Low-Vol Defensive
  - Post-Exit Remorse & Mistake Feedback: Dynamic Take-Profit & Trailing ATR scaling
"""

import os
import sqlite3
import math
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
import config

CONFIG_OVERRIDE_FILE = "autotune_config.json"

def load_autotune_overrides():
    """Dynamically applies autotuned parameters into in-memory config."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    f_path = os.path.join(base_dir, CONFIG_OVERRIDE_FILE)
    if os.path.exists(f_path):
        try:
            with open(f_path, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            for k, v in overrides.items():
                if hasattr(config, k) and not isinstance(v, dict):
                    setattr(config, k, v)
            return overrides
        except Exception as e:
            logger.debug("Failed loading autotune overrides: {}", e)
    return {}

def get_symbol_tuned_parameters(symbol: str, atr_pct: float = None) -> Dict[str, Any]:
    """
    Returns tailored trading parameters for a specific stock
    by resolving: Asset Volatility Cluster -> Global Fallback
    """
    overrides = load_autotune_overrides()
    clusters = overrides.get("CLUSTERS", {})
    
    try:
        from post_exit_tracker import classify_symbol_cluster
        c_name = classify_symbol_cluster(symbol, atr_pct)
    except Exception:
        c_name = "MID_VOL_MOMENTUM"
        
    c_params = clusters.get(c_name, {})
    
    tp_val = float(c_params.get("TAKE_PROFIT_PCT", overrides.get("TAKE_PROFIT_PCT", 0.090)))
    sl_val = float(c_params.get("STOP_LOSS_PCT", overrides.get("STOP_LOSS_PCT", 0.038)))
    tr_val = float(c_params.get("TRAILING_ATR", 2.0))
    min_hold = float(c_params.get("MIN_HOLD_HOURS", 12.0))
    c_label = c_params.get("label", c_name)
    
    return {
        "symbol": symbol,
        "cluster": c_name,
        "cluster_label": c_label,
        "take_profit_pct": tp_val,
        "stop_loss_pct": sl_val,
        "trailing_atr": tr_val,
        "min_hold_hours": min_hold
    }

class AutoTuningEngine:
    """Institutional-Grade Self-Optimizing Quant Parameter Tuner with Multi-Tier Clustering"""
    
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
        conn = self._get_db_connection()
        if not conn:
            return {"loss_count": 0, "root_causes": {}}

        cur = conn.cursor()
        since_date = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

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

    def analyze_post_exit_remorse(self) -> Dict[str, Any]:
        """
        Analyzes 1~2 week post-sale price performance from post_exit_tracking:
        Grouped by Asset Volatility Cluster (HIGH_VOL_GROWTH, MID_VOL_MOMENTUM, LOW_VOL_DEFENSIVE).
        """
        try:
            from post_exit_tracker import get_post_exit_tracker
            get_post_exit_tracker()._init_db()
        except Exception:
            pass

        conn = self._get_db_connection()
        if not conn:
            return {"total_tracked": 0, "early_exits": 0, "avoided_drops": 0, "avg_post_return": 0.0, "by_cluster": {}}

        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, cluster, atr_pct, realized_pnl_pct, post_exit_return_pct, evaluation
                FROM post_exit_tracking
                WHERE post_exit_return_pct IS NOT NULL
            """)
            rows = cur.fetchall()
            conn.close()

            if not rows:
                return {"total_tracked": 0, "early_exits": 0, "avoided_drops": 0, "avg_post_return": 0.0, "by_cluster": {}}

            early_exits = [r for r in rows if r['evaluation'] == 'EARLY_EXIT_MISSED_RALLY']
            avoided_drops = [r for r in rows if r['evaluation'] == 'PERFECT_EXIT_AVOIDED_DROP']
            avg_post = sum(float(r['post_exit_return_pct'] or 0.0) for r in rows) / len(rows)

            by_cluster = {}
            for c_name in ["HIGH_VOL_GROWTH", "MID_VOL_MOMENTUM", "LOW_VOL_DEFENSIVE"]:
                c_rows = [r for r in rows if (r['cluster'] or 'MID_VOL_MOMENTUM') == c_name]
                c_early = [r for r in c_rows if r['evaluation'] == 'EARLY_EXIT_MISSED_RALLY']
                c_avoid = [r for r in c_rows if r['evaluation'] == 'PERFECT_EXIT_AVOIDED_DROP']
                c_avg = sum(float(r['post_exit_return_pct'] or 0.0) for r in c_rows) / len(c_rows) if c_rows else 0.0
                by_cluster[c_name] = {
                    "count": len(c_rows),
                    "early_exits": len(c_early),
                    "avoided_drops": len(c_avoid),
                    "avg_post_return": c_avg
                }

            return {
                "total_tracked": len(rows),
                "early_exits": len(early_exits),
                "avoided_drops": len(avoided_drops),
                "avg_post_return": avg_post,
                "by_cluster": by_cluster
            }
        except Exception as e:
            logger.debug("Post-exit remorse analysis error: {}", e)
            return {"total_tracked": 0, "early_exits": 0, "avoided_drops": 0, "avg_post_return": 0.0, "by_cluster": {}}

    def analyze_performance(self, lookback_days: int = 30) -> dict:
        conn = self._get_db_connection()
        if not conn:
            return {}
            
        cur = conn.cursor()
        since_date = (date.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        
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
        metrics = self.analyze_performance(lookback_days=30)
        loss_analysis = self.analyze_loss_root_causes(lookback_days=30)
        remorse = self.analyze_post_exit_remorse()
        
        # 1. Base Global Parameters
        tuned_params = {
            "MIN_ENTRY_SCORE": 80,
            "STOP_LOSS_PCT": 0.040,
            "TAKE_PROFIT_PCT": 0.090,
            "MAX_POSITION_PCT": 0.25,
            "RVOL_MIN": 1.5,
            "MAX_RSI_ENTRY": 72,
            "TUNED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "REASON": "Baseline Balanced Institutional Matrix"
        }

        # 2. Cluster-Specific Parameter Matrix (종목 성향별 분리 매트릭스)
        cluster_params = {
            "HIGH_VOL_GROWTH": {
                "label": "🚀 고변동 성장주",
                "TAKE_PROFIT_PCT": 0.150,
                "STOP_LOSS_PCT": 0.050,
                "TRAILING_ATR": 2.8,
                "MIN_HOLD_HOURS": 24.0
            },
            "MID_VOL_MOMENTUM": {
                "label": "⚖️ 중변동 표준주",
                "TAKE_PROFIT_PCT": 0.090,
                "STOP_LOSS_PCT": 0.038,
                "TRAILING_ATR": 2.0,
                "MIN_HOLD_HOURS": 12.0
            },
            "LOW_VOL_DEFENSIVE": {
                "label": "🛡️ 저변동 방어주",
                "TAKE_PROFIT_PCT": 0.055,
                "STOP_LOSS_PCT": 0.028,
                "TRAILING_ATR": 1.4,
                "MIN_HOLD_HOURS": 6.0
            }
        }
        
        n_trades = metrics.get("total_trades", 0)
        win_rate = metrics.get("win_rate", 0.0)
        pf = metrics.get("profit_factor", 1.0)
        causes = loss_analysis.get("root_causes", {})
        mae_wins_95 = metrics.get("mae_wins_95", 0.038)
        mfe_median = metrics.get("mfe_median", 0.060)
        ic = metrics.get("ic", 0.0)
        
        reasons = []

        if n_trades >= 3:
            optimal_sl = min(0.055, max(0.030, mae_wins_95 + 0.005))
            tuned_params["STOP_LOSS_PCT"] = round(optimal_sl, 3)
            
            optimal_tp = min(0.140, max(0.060, mfe_median * 0.75))
            tuned_params["TAKE_PROFIT_PCT"] = round(optimal_tp, 3)

            if ic >= 0.25:
                tuned_params["MIN_ENTRY_SCORE"] = 78
                reasons.append(f"고예측 알파(IC={ic:+.2f} ➔ 78점)")
            elif ic < -0.10:
                tuned_params["MIN_ENTRY_SCORE"] = 84
                reasons.append(f"노이즈 방어(IC={ic:+.2f} ➔ 84점)")

            if causes.get("FALSE_BREAKOUT", 0) >= 2:
                tuned_params["RVOL_MIN"] = 2.0
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 83)
                reasons.append("가짜돌파 방어(RVOL 2.0배)")
                
            if causes.get("OVERBOUGHT_CLIMAX", 0) >= 2:
                tuned_params["MAX_RSI_ENTRY"] = 68
                reasons.append("상투 과열 차단(RSI 68)")

            if win_rate < 50.0 or pf < 1.2:
                tuned_params["MIN_ENTRY_SCORE"] = max(tuned_params["MIN_ENTRY_SCORE"], 85)
                tuned_params["MAX_POSITION_PCT"] = 0.18
                reasons.append(f"계좌 방어 모드(승률 {win_rate:.1f}%)")
            elif win_rate >= 65.0 and pf >= 1.8:
                tuned_params["MAX_POSITION_PCT"] = 0.30
                reasons.append(f"알파 집중 모드(승률 {win_rate:.1f}%)")

        # 3. Dynamic Cluster-Level Remorse Feedback Calibration (군집별 독립 튜닝)
        by_cluster = remorse.get("by_cluster", {})
        for c_name, c_data in by_cluster.items():
            if c_name not in cluster_params:
                continue
            lbl = cluster_params[c_name]["label"]
            if c_data.get("early_exits", 0) >= 1 or c_data.get("avg_post_return", 0.0) >= 4.0:
                cluster_params[c_name]["TAKE_PROFIT_PCT"] = round(cluster_params[c_name]["TAKE_PROFIT_PCT"] * 1.25, 3)
                cluster_params[c_name]["TRAILING_ATR"] = round(cluster_params[c_name]["TRAILING_ATR"] * 1.20, 2)
                reasons.append(f"{lbl} 조기매도({c_data['early_exits']}건) ➔ 익절 {cluster_params[c_name]['TAKE_PROFIT_PCT']*100:.1f}%·트레일 {cluster_params[c_name]['TRAILING_ATR']}x 상향")
            elif c_data.get("avoided_drops", 0) >= 1:
                reasons.append(f"{lbl} 손실회피({c_data['avoided_drops']}건) 고점탈출 확인")

        tuned_params["CLUSTERS"] = cluster_params
        if reasons:
            tuned_params["REASON"] = " + ".join(reasons)

        try:
            with open(self.config_override_file, "w", encoding="utf-8") as f:
                json.dump(tuned_params, f, indent=2, ensure_ascii=False)
            load_autotune_overrides()
            logger.info("✅ Multi-Tier AutoTuning parameters saved and applied in-memory: {}", tuned_params)
        except Exception as e:
            logger.error("Failed to save autotune config: {}", e)
            
        return tuned_params

    def format_telegram_card(self) -> str:
        metrics = self.analyze_performance(lookback_days=30)
        loss_analysis = self.analyze_loss_root_causes(lookback_days=30)
        tuned = self.run_autotune()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        causes_str = ", ".join([f"{k}: {v}건" for k, v in loss_analysis.get('root_causes', {}).items() if v > 0]) or "손실 원인 없음 (100% 승리/초기)"
        ic_val = metrics.get('ic', 0.0)
        remorse = self.analyze_post_exit_remorse()
        remorse_str = f"조기매도 {remorse.get('early_exits', 0)}건, 손실회피 {remorse.get('avoided_drops', 0)}건 (추적: {remorse.get('total_tracked', 0)}건, 평균 변동: {remorse.get('avg_post_return', 0.0):+.1f}%)"

        clusters = tuned.get("CLUSTERS", {})
        high_c = clusters.get("HIGH_VOL_GROWTH", {})
        mid_c = clusters.get("MID_VOL_MOMENTUM", {})
        low_c = clusters.get("LOW_VOL_DEFENSIVE", {})

        card = (
            f"⚙️ <b>[종목 성향별 AI 파라미터 자가 튜닝 리포트]</b>\n"
            f"<i>{now_str} (Asset-Specific Volatility Cluster Matrix)</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>최근 30일 매매 실적 및 오답노트 피드백</b>:\n"
            f"  • 전적: {metrics.get('total_trades', 0)}전 {metrics.get('wins', 0)}승 {metrics.get('losses', 0)}패\n"
            f"  • 승률: <b>{metrics.get('win_rate', 0.0):.1f}%</b> | Profit Factor: <b>{metrics.get('profit_factor', 1.0):.2f}</b>\n"
            f"  • 📈 <b>평균 MFE</b>: <code>+{metrics.get('avg_mfe', 0.0)*100:.1f}%</code> | 📉 <b>평균 MAE</b>: <code>-{metrics.get('avg_mae', 0.0)*100:.1f}%</code>\n"
            f"  • 🔮 <b>알파 점수 예측력(IC)</b>: <code>{ic_val:+.2f}</code>\n"
            f"  • 📝 <b>매도 사후 오답노트</b>: <i>{remorse_str}</i>\n\n"
            f"🏛️ <b>3대 자산 성향별 맞춤 튜닝 매트릭스</b>:\n"
            f"  🚀 <b>고변동 성장주 (NVDA/PLTR/CRWD 등)</b>\n"
            f"     • 익절선: <code>+{high_c.get('TAKE_PROFIT_PCT', 0.15)*100:.1f}%</code> | 손절선: <code>-{high_c.get('STOP_LOSS_PCT', 0.05)*100:.1f}%</code> | 트레일: <code>{high_c.get('TRAILING_ATR', 2.8)}x ATR</code>\n\n"
            f"  ⚖️ <b>중변동 표준주 (AAPL/MSFT/NOW 등)</b>\n"
            f"     • 익절선: <code>+{mid_c.get('TAKE_PROFIT_PCT', 0.09)*100:.1f}%</code> | 손절선: <code>-{mid_c.get('STOP_LOSS_PCT', 0.038)*100:.1f}%</code> | 트레일: <code>{mid_c.get('TRAILING_ATR', 2.0)}x ATR</code>\n\n"
            f"  🛡️ <b>저변동 방어주 (MDT/ADP/KO/JNJ 등)</b>\n"
            f"     • 익절선: <code>+{low_c.get('TAKE_PROFIT_PCT', 0.055)*100:.1f}%</code> | 손절선: <code>-{low_c.get('STOP_LOSS_PCT', 0.028)*100:.1f}%</code> | 트레일: <code>{low_c.get('TRAILING_ATR', 1.4)}x ATR</code>\n\n"
            f"🤖 <b>[AI 자율 최적화 수학적 근거]</b>:\n"
            f"<i>'{tuned.get('REASON', 'Multi-Tier Institutional Cluster Harmony')}'</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>각 종목은 본인의 변동성(ATR) 군집에 할당된 개별 파라미터로 정밀 매매됩니다.</i>"
        )
        return card

    def send_tuning_report_to_telegram(self) -> bool:
        try:
            card_text = self.format_telegram_card()
            token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
            chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')
            if token and chat_id:
                import requests
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                requests.post(url, json={"chat_id": chat_id, "text": card_text, "parse_mode": "HTML"}, timeout=10)
                return True
        except Exception as e:
            logger.error("Failed sending autotune report: {}", e)
        return False