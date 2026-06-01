"""
Ultimate Swing Auto-Tuner AI (Reinforcement Learning)
=====================================================
Analyzes the trades.db over the past 14 days and adjusts .env
parameters to dynamically adapt the Swing Trading bot to market regimes.
Modifies: SCREENED_MIN_SCORE, MAX_POSITION_PCT, TAKE_PROFIT_PCT
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv, set_key
from loguru import logger

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
DB_FILE = BASE_DIR / "trades.db"

load_dotenv(ENV_FILE)

# Stub for Telegram Integration
def send_tg(msg: str):
    try:
        from notifier import get_notifier
        n = get_notifier()
        if n:
            n._send_sync(msg)
    except Exception as e:
        logger.error(f"TG Send Failed: {e}")

def get_recent_metrics(days: int = 21) -> dict:  # 14 → 21일로 확장 (더 많은 데이터 확보)
    """Fetch trading metrics from the SQLite DB"""
    metrics = {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "total_pnl": 0.0,
        "profit_factor": 0.0,
        "avg_hold_days": 0.0,
        "max_drawdown": 0.0,
    }
    
    if not DB_FILE.exists():
        return metrics
        
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get trades from last N days
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cur.execute("SELECT * FROM trades WHERE side='SELL' AND created_at >= ?", (cutoff,))
        rows = cur.fetchall()
        
        if not rows:
            return metrics
            
        metrics["total_trades"] = len(rows)
        
        gross_profit = 0
        gross_loss = 0
        total_hold_days = 0.0
        hold_days_count = 0
        
        for r in rows:
            pnl = float(r["pnl_pct"] or 0)
            realized = float(r["pnl"] or 0)
            metrics["total_pnl"] += realized
            
            # Simple Win/Loss count based on %
            if pnl > 0:
                metrics["wins"] += 1
                gross_profit += realized if realized > 0 else (pnl * 100) # Proxy if realized 0
            else:
                metrics["losses"] += 1
                gross_loss += abs(realized) if realized < 0 else abs(pnl * 100)
                
            # Hold time calculation from database
            symbol = r["symbol"]
            sell_time_str = r["exit_time"] or r["created_at"]
            
            try:
                # Query corresponding BUY trade before this exit
                cur2 = conn.cursor()
                cur2.execute("""
                    SELECT entry_time, created_at 
                    FROM trades 
                    WHERE symbol = ? AND side = 'BUY' AND created_at < ? 
                    ORDER BY created_at DESC LIMIT 1
                """, (symbol, r["created_at"]))
                buy_row = cur2.fetchone()
                
                if buy_row:
                    buy_time_str = buy_row["entry_time"] or buy_row["created_at"]
                    
                    fmt = "%Y-%m-%d %H:%M:%S"
                    def parse_sqlite_dt(dt_s):
                        if not dt_s: return datetime.now()
                        for char in ["T", "Z"]:
                            dt_s = dt_s.replace(char, " ")
                        dt_s = dt_s.split(".")[0].strip()
                        return datetime.strptime(dt_s, fmt)
                    
                    buy_dt = parse_sqlite_dt(buy_time_str)
                    sell_dt = parse_sqlite_dt(sell_time_str)
                    
                    diff = (sell_dt - buy_dt).total_seconds() / 86400.0
                    if diff > 0:
                        total_hold_days += diff
                        hold_days_count += 1
            except Exception as parse_e:
                logger.debug(f"Failed to calculate real hold time for {symbol}: {parse_e}")

        metrics["win_rate"] = metrics["wins"] / metrics["total_trades"] if metrics["total_trades"] > 0 else 0
        metrics["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else (99.9 if gross_profit > 0 else 0)
        metrics["avg_hold_days"] = total_hold_days / hold_days_count if hold_days_count > 0 else 7.0
        
        conn.close()
    except Exception as e:
        logger.error(f"Error reading DB metrics: {e}")

    return metrics

def calculate_adjustments(m: dict) -> dict:
    """The AI Learning Logic Core"""
    changes = {}
    reasons = []
    
    if m["total_trades"] < 2:  # 4 → 2건으로 완화 (스윙 봇은 거래 빈도가 낮음)
        return {"changes": changes, "reasons": ["최근 21일 거래 건수 부족 (최소 2건 필요). 학습 건너뜀."]}

    wr = m["win_rate"]
    pf = m["profit_factor"]
    
    logger.info(f"AI Eval -> WR: {wr:.1%}, PF: {pf:.2f}, Trades: {m['total_trades']}")

    # 1. Dynamic Hurdle Adjustment (SCREENED_MIN_SCORE)
    current_score = int(os.getenv("SCREENED_MIN_SCORE", "35"))
    if wr < 0.40:
        new_score = min(current_score + 5, 50)
        if new_score != current_score:
            changes["SCREENED_MIN_SCORE"] = str(new_score)
            reasons.append(f"승률 저조({wr:.0%}) -> 후보 검증 강화 (합격점 {current_score}->{new_score} 상향)")
    elif wr > 0.65 and current_score > 30:
        new_score = max(current_score - 3, 30)
        if new_score != current_score:
            changes["SCREENED_MIN_SCORE"] = str(new_score)
            reasons.append(f"승률 우수({wr:.0%}) -> 기회 창출 확대 (합격점 {current_score}->{new_score} 완화)")

    # 2. Market Regime Sizing (MAX_POSITION_PCT)
    current_pos_pct = float(os.getenv("MAX_POSITION_PCT", "0.25"))
    if pf < 0.8:
        new_pos = max(current_pos_pct - 0.05, 0.20)
        if new_pos != current_pos_pct:
            changes["MAX_POSITION_PCT"] = f"{new_pos:.2f}"
            reasons.append(f"손익비 악화(PF:{pf:.1f}) -> 수비 모드 (비중 {current_pos_pct:.0%}->{new_pos:.0%} 축소)")
    elif pf > 1.8 and wr > 0.50:
        new_pos = min(current_pos_pct + 0.05, 0.40)
        if new_pos != current_pos_pct:
            changes["MAX_POSITION_PCT"] = f"{new_pos:.2f}"
            reasons.append(f"장세 호조(PF:{pf:.1f}) -> 공격 모드 (비중 {current_pos_pct:.0%}->{new_pos:.0%} 확대)")

    # 3. Take-Profit Adaptation (TAKE_PROFIT_PCT)
    current_tp = float(os.getenv("TAKE_PROFIT_PCT", "0.20"))
    if wr > 0.45 and m["avg_hold_days"] > 8 and current_tp > 0.10:
        if pf < 1.0: 
            new_tp = max(current_tp - 0.02, 0.12)
            if new_tp != current_tp:
                changes["TAKE_PROFIT_PCT"] = f"{new_tp:.2f}"
                reasons.append(f"이익 반납 빈번 -> 현실적 목표가 조절 (TP {current_tp:.0%}->{new_tp:.0%})")
                
    return {"changes": changes, "reasons": reasons}

def run_auto_tune():
    """Main execution loop for AI Tuner"""
    logger.info("=== Autonomous Swing AI Tuner ===")
    
    lock_file = BASE_DIR / ".auto_tuner_lock"
    now = datetime.now()
    # COOLDOWN: 24시간에 1회만 실행 (이전: 12시간 → 중복 알림 방지)
    if lock_file.exists():
        try:
            with open(lock_file, "r") as f:
                last_run_str = f.read().strip()
                if last_run_str:
                    last_run = datetime.fromisoformat(last_run_str)
                    elapsed_hours = (now - last_run).total_seconds() / 3600
                    if elapsed_hours < 24:  # 24시간 쿨다운 (기존 12시간에서 강화)
                        logger.info(f"Auto tuner cooldown active. Last run {elapsed_hours:.1f}h ago. Skipping.")
                        return
        except Exception as e:
            logger.warning(f"Failed to read lock file: {e}")
            
    try:
        with open(lock_file, "w") as f:
            f.write(now.isoformat())
    except Exception as e:
        logger.warning(f"Failed to write lock file: {e}")
    
    metrics = get_recent_metrics(21)
    result = calculate_adjustments(metrics)
    changes = result["changes"]
    reasons = result["reasons"]
    
    report = f"🧠 <b>AI 스윙 학습 리포트 (최근 21일)</b>\n\n"
    report += f"📊 <b>성과 요약</b>\n"
    report += f"• 분석 건수: {metrics['total_trades']}건\n"
    report += f"• 체감 승률: {metrics['win_rate']:.0%}\n"
    report += f"• 자본 손익비: {metrics['profit_factor']:.2f}\n"
    report += f"• 평균 보유일수: {metrics['avg_hold_days']:.1f}일\n\n"

    if changes:
        report += f"🔧 <b>AI 자율 업데이트 내역</b>\n"
        for r in reasons:
            report += f"• {r}\n"
        
        for k, v in changes.items():
            set_key(str(ENV_FILE), k, str(v))
            logger.info(f"Updated {k} to {v}")
            
        report += f"\n✅ 지표 최적화 완료! 다음 사이클부터 새 파라미터가 자동 적용됩니다."
        send_tg(report)
        logger.info("Changes saved to .env. Will take effect on next orchestrator cycle (no restart needed).")
        # ⚠️ 절대 서비스를 재시작하지 않음!
        # os.system("sudo systemctl restart kis-trading")  
        # 이유: 재시작 → ran_post_market_today 초기화 → phase_6 재실행 → 무한루프 발생
    else:
        report += f"✅ AI 진단 결과: 현재 파라미터가 장세와 완벽히 호환됩니다. (변경 없음)"
        if reasons:
            report += "\n\n💡 <b>AI 코멘트</b>\n"
            for r in reasons:
                report += f"• {r}\n"
        send_tg(report)
        logger.info("No environment changes required.")

# Alias for backwards compatibility
run_hyperparameter_optimization = run_auto_tune

if __name__ == "__main__":
    run_auto_tune()
