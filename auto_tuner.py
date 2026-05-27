"""
Auto Tuner - 매매 데이터 기반 자동 파라미터 튜닝 v2
================================================
매주 일요일 자동 실행 (시장 휴장일).
지난 1~2주 매매 결과를 분석하여 .env 파라미터를 자동 조정.
텔레그램으로 변경 내역 리포트 전송.

[수정 내역]
- DB 경로: config.DB_FILE 사용 (기존 trading.db → trades.db)
- 소수점 형식: config와 동일한 0.03 형식 사용
- 전략 파라미터: PHASE_CONFIGS와 연동
"""

import os
import json
import sqlite3
import config
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv, set_key

load_dotenv()

# Telegram
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENV_FILE = Path(__file__).parent / ".env"
TUNING_LOG = Path(__file__).parent / "tuning_history.json"

# ★ config의 DB_FILE과 동일하게 사용
DB_FILE = Path(__file__).parent / os.getenv("DB_FILE", "trades.db")


def send_tg(msg):
    try:
        import requests
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def get_recent_trades(days=14):
    """최근 N일간 매매 기록 조회"""
    if not DB_FILE.exists():
        logger.warning("DB file not found: {}", DB_FILE)
        return []
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM trades WHERE entry_time >= ? ORDER BY entry_time DESC", (cutoff,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("DB read failed: {}", e)
        return []


def get_daily_stats(days=14):
    """최근 N일간 일별 통계"""
    if not DB_FILE.exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date DESC", (cutoff,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("DB read failed: {}", e)
        return []


def analyze_performance(trades, daily_stats):
    """매매 성과 분석"""
    if not trades:
        return None

    # SELL 거래만 분석 (BUY는 진입이므로)
    sell_trades = [t for t in trades if t.get("side") == "SELL" and t.get("pnl") is not None]
    if not sell_trades:
        sell_trades = trades  # fallback

    total = len(sell_trades)
    wins = sum(1 for t in sell_trades if (t.get("pnl") or 0) > 0)
    losses = total - wins
    win_rate = wins / total if total > 0 else 0

    avg_win = 0
    avg_loss = 0
    win_trades = [t for t in sell_trades if (t.get("pnl") or 0) > 0]
    loss_trades = [t for t in sell_trades if (t.get("pnl") or 0) <= 0]

    if win_trades:
        avg_win = sum(t.get("pnl", 0) for t in win_trades) / len(win_trades)
    if loss_trades:
        avg_loss = abs(sum(t.get("pnl", 0) for t in loss_trades) / len(loss_trades))

    profit_factor = avg_win / avg_loss if avg_loss > 0 else 999
    total_pnl = sum(t.get("pnl", 0) or 0 for t in sell_trades)

    # 종목별 성과
    symbol_performance = {}
    for t in sell_trades:
        sym = t.get("symbol", "unknown")
        if sym not in symbol_performance:
            symbol_performance[sym] = {"wins": 0, "losses": 0, "pnl": 0, "count": 0}
        symbol_performance[sym]["count"] += 1
        if (t.get("pnl") or 0) > 0:
            symbol_performance[sym]["wins"] += 1
        else:
            symbol_performance[sym]["losses"] += 1
        symbol_performance[sym]["pnl"] += t.get("pnl", 0) or 0

    # 연속 손실
    max_consecutive_losses = 0
    current_streak = 0
    for t in sell_trades:
        if (t.get("pnl") or 0) <= 0:
            current_streak += 1
            max_consecutive_losses = max(max_consecutive_losses, current_streak)
        else:
            current_streak = 0

    # 평균 보유 시간 분석
    avg_hold_hours = 0
    hold_count = 0
    for t in sell_trades:
        entry = t.get("entry_time")
        exit_t = t.get("exit_time")
        if entry and exit_t:
            try:
                entry_dt = datetime.fromisoformat(entry) if isinstance(entry, str) else entry
                exit_dt = datetime.fromisoformat(exit_t) if isinstance(exit_t, str) else exit_t
                hours = (exit_dt - entry_dt).total_seconds() / 3600
                avg_hold_hours += hours
                hold_count += 1
            except Exception:
                pass
    if hold_count > 0:
        avg_hold_hours /= hold_count

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "max_consecutive_losses": max_consecutive_losses,
        "avg_hold_hours": avg_hold_hours,
        "symbol_performance": symbol_performance,
    }


def calculate_adjustments(analysis):
    """분석 결과에 따라 파라미터 조정값 계산
    
    ★ 모든 값은 config.py와 동일한 형식 사용:
    - DAILY_STOP_LOSS_PCT: 0.03 (3%)
    - MAX_POSITION_PCT: 0.30 (30%)
    - TAKE_PROFIT_PCT: 0.05 (5%)
    """
    if not analysis:
        return {}

    changes = {}
    reasons = []

    wr = analysis["win_rate"]
    pf = analysis["profit_factor"]
    mcl = analysis["max_consecutive_losses"]
    total = analysis["total_trades"]

    # === 1. TAKE_PROFIT_PCT 조정 (config.py에서 사용) ===
    current_tp = float(os.getenv("TAKE_PROFIT_PCT", "0.10"))
    if analysis["avg_win"] > 0 and analysis["avg_loss"] > 0:
        ratio = analysis["avg_win"] / analysis["avg_loss"]
        if ratio < 1.0 and total >= 8:
            # 이익이 손실보다 작다 → TP 올려서 더 큰 수익 추구 (스윙: 최대 25%)
            new_tp = min(current_tp + 0.02, 0.25)  
            if new_tp != current_tp:
                changes["TAKE_PROFIT_PCT"] = f"{new_tp:.2f}"
                reasons.append(f"평균이익/손실 비율 {ratio:.1f} → TP {current_tp:.0%}→{new_tp:.0%}")
        elif ratio > 2.5 and wr > 0.50:
            # 이익이 많다 → TP 낮춰서 안정적인 체결 유도 (스윙: 최소 6%)
            new_tp = max(current_tp - 0.01, 0.06)  
            if new_tp != current_tp:
                changes["TAKE_PROFIT_PCT"] = f"{new_tp:.2f}"
                reasons.append(f"이익비율 {ratio:.1f} 우수 → TP {current_tp:.0%}→{new_tp:.0%} (체결↑)")

    # === 2. DAILY_STOP_LOSS_PCT 조정 ===
    current_sl = float(os.getenv("DAILY_STOP_LOSS_PCT", "0.05"))
    if mcl >= 4:
        new_sl = max(current_sl - 0.01, 0.04)  # 최소 4% (스윙 룸 확보)
        if new_sl != current_sl:
            changes["DAILY_STOP_LOSS_PCT"] = f"{new_sl:.3f}"
            reasons.append(f"연속손실 {mcl}회 → 일일한도 {current_sl:.1%}→{new_sl:.1%}")
    elif mcl <= 1 and wr > 0.55 and total >= 10:
        new_sl = min(current_sl + 0.01, 0.08)  # 최대 8% (장 변동성 허용)
        if new_sl != current_sl:
            changes["DAILY_STOP_LOSS_PCT"] = f"{new_sl:.3f}"
            reasons.append(f"손실 적음 → 일일한도 완화 {current_sl:.1%}→{new_sl:.1%}")

    # === 3. MAX_POSITION_PCT 조정 ===
    current_pos = float(os.getenv("MAX_POSITION_PCT", "0.20"))
    if pf < 1.0 and total >= 8:
        new_pos = max(current_pos - 0.05, 0.10)  # 최소 10%
        if new_pos != current_pos:
            changes["MAX_POSITION_PCT"] = f"{new_pos:.2f}"
            reasons.append(f"손익비 {pf:.1f} → 포지션 축소 {current_pos:.0%}→{new_pos:.0%}")
    elif pf > 2.0 and wr > 0.55 and total >= 10:
        new_pos = min(current_pos + 0.05, 0.30)  # 최대 30%
        if new_pos != current_pos:
            changes["MAX_POSITION_PCT"] = f"{new_pos:.2f}"
            reasons.append(f"손익비 {pf:.1f} 우수 → 포지션 확대 {current_pos:.0%}→{new_pos:.0%}")

    # === 4. ATR_STOP_MULTIPLIER 조정 ===
    current_atr = float(os.getenv("ATR_STOP_MULTIPLIER", "2.0"))
    if wr < 0.35 and total >= 8:
        # 승률 너무 낮음 → 손절 너무 타이트할 수 있음
        new_atr = min(current_atr + 0.5, 3.0)
        if new_atr != current_atr:
            changes["ATR_STOP_MULTIPLIER"] = f"{new_atr:.1f}"
            reasons.append(f"승률 {wr:.0%} 낮음 → 손절 여유 {current_atr}→{new_atr} ATR")
    elif wr > 0.60 and analysis["avg_loss"] > analysis["avg_win"] * 0.8:
        # 승률 높은데 손실 크기가 너무 큼 → 손절 타이트하게
        new_atr = max(current_atr - 0.5, 1.5)
        if new_atr != current_atr:
            changes["ATR_STOP_MULTIPLIER"] = f"{new_atr:.1f}"
            reasons.append(f"평균손실 큼 → 손절 타이트 {current_atr}→{new_atr} ATR")

    # === 5. CONSECUTIVE_LOSS_LIMIT 조정 ===
    current_cl = int(os.getenv("CONSECUTIVE_LOSS_LIMIT", "5"))
    if mcl >= current_cl and total >= 10:
        new_cl = max(current_cl - 1, 4) # 최소 4회
        if new_cl != current_cl:
            changes["CONSECUTIVE_LOSS_LIMIT"] = str(new_cl)
            reasons.append(f"연속손실 한도 도달 → {current_cl}→{new_cl}회로 강화")

    # === 반복 손실 종목 경고 ===
    best_symbols = sorted(
        analysis["symbol_performance"].items(),
        key=lambda x: x[1]["pnl"], reverse=True
    )
    losing_symbols = [s for s, d in best_symbols if d["pnl"] < 0 and d["count"] >= 2]
    if losing_symbols:
        reasons.append(f"⚠ 반복 손실 종목: {', '.join(losing_symbols[:5])}")

    return {"changes": changes, "reasons": reasons, "analysis": analysis}


def apply_changes(changes):
    """파라미터 변경을 .env에 적용"""
    if not changes:
        return

    for key, value in changes.items():
        set_key(str(ENV_FILE), key, value)
        logger.info("Updated {}: {}", key, value)


def save_tuning_log(result):
    """튜닝 이력 저장"""
    history = []
    if TUNING_LOG.exists():
        try:
            history = json.loads(TUNING_LOG.read_text(encoding="utf-8"))
        except Exception:
            history = []

    entry = {
        "date": datetime.now().isoformat(),
        "changes": result.get("changes", {}),
        "reasons": result.get("reasons", []),
        "win_rate": result.get("analysis", {}).get("win_rate", 0),
        "total_trades": result.get("analysis", {}).get("total_trades", 0),
        "total_pnl": result.get("analysis", {}).get("total_pnl", 0),
        "profit_factor": result.get("analysis", {}).get("profit_factor", 0),
    }
    history.append(entry)

    # 최근 50건만 유지
    history = history[-50:]
    TUNING_LOG.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def run_auto_tune():
    """자동 튜닝 실행 (매주 일요일 호출)"""
    logger.info("=== Auto Tuner v2 시작 ===")

    trades = get_recent_trades(14)
    daily_stats = get_daily_stats(14)

    if len(trades) < 5:
        msg = f"📊 <b>Auto Tuner</b>\n매매 건수 부족 ({len(trades)}건). 5건 이상 필요.\n다음 주에 다시 분석합니다."
        send_tg(msg)
        logger.info("Not enough trades: {}", len(trades))
        return

    analysis = analyze_performance(trades, daily_stats)
    if not analysis:
        return

    result = calculate_adjustments(analysis)
    changes = result.get("changes", {})
    reasons = result.get("reasons", [])

    # 텔레그램 리포트
    report = f"📊 <b>주간 자동 튜닝 리포트</b>\n"
    report += f"기간: 최근 14일\n\n"
    report += f"📈 <b>성과 요약</b>\n"
    report += f"• 총 매매: {analysis['total_trades']}건\n"
    report += f"• 승률: {analysis['win_rate']:.0%}\n"
    report += f"• 손익비: {analysis['profit_factor']:.1f}\n"
    report += f"• 총 손익: ${analysis['total_pnl']:,.2f}\n"
    report += f"• 연속 최대 손실: {analysis['max_consecutive_losses']}회\n"
    report += f"• 평균 보유: {analysis['avg_hold_hours']:.1f}시간\n\n"

    if changes:
        report += f"🔧 <b>파라미터 변경</b>\n"
        for reason in reasons:
            report += f"• {reason}\n"
        apply_changes(changes)
        save_tuning_log(result)
        report += f"\n✅ .env 자동 적용 완료. 봇 재시작 중..."
    else:
        report += f"✅ 현재 파라미터 적절. 변경 없음.\n"
        if reasons:
            report += "\n📋 <b>참고사항</b>\n"
            for reason in reasons:
                report += f"• {reason}\n"
        save_tuning_log(result)

    send_tg(report)
    logger.info("Auto Tuner complete. Changes: {}", len(changes))

    # 파라미터 변경 시 봇 재시작 (무한루프 방지를 위해 제거)
    if changes:
        logger.info("Changes saved. Will take effect on next cycle. No restart needed.")
        # ⚠️ 절대 서비스를 재시작하지 않음!
        # os.system("sudo systemctl restart kis-trading")


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    run_auto_tune()
