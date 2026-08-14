"""
Weekly AI Quant Executive Performance Report Generator (v1.0.0)
===============================================================
Synthesizes 7-day trade history, win-rate, profit factor, factor alpha attribution,
and generates a Wall-Street Hedge Fund Weekly Investor Letter via Gemini AI.
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import pandas as pd
from loguru import logger
import config

class WeeklyAIReportGenerator:
    """Generates weekly executive quant reports using trades.db and Gemini AI."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or getattr(config, 'DB_PATH', 'trades.db')
        self.api_key = getattr(config, 'GEMINI_API_KEY', '')

    def _get_weekly_trade_stats(self) -> Dict[str, Any]:
        """Queries the SQLite database for trades closed in the past 7 days."""
        now = datetime.now()
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")

        stats = {
            "start_date": start_date[:10],
            "end_date": now.strftime("%Y-%m-%d"),
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "gross_pnl": 0.0,
            "profit_factor": 0.0,
            "best_trade": None,
            "worst_trade": None,
            "trades_list": [],
            "current_positions": []
        }

        if not os.path.exists(self.db_path):
            return stats

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query closed trades in the last 7 days
            cursor.execute("""
                SELECT symbol, side, price, quantity, pnl, pnl_pct, reason, created_at
                FROM trades
                WHERE side = 'SELL' AND created_at >= ?
                ORDER BY created_at DESC
            """, (start_date,))
            rows = cursor.fetchall()

            gains = 0.0
            losses_val = 0.0
            trades = []

            for r in rows:
                pnl = float(r["pnl"] or 0.0)
                pnl_pct = float(r["pnl_pct"] or 0.0)
                trades.append({
                    "symbol": r["symbol"],
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": r["reason"] or "N/A",
                    "date": r["created_at"][:10]
                })
                if pnl > 0:
                    stats["wins"] += 1
                    gains += pnl
                elif pnl < 0:
                    stats["losses"] += 1
                    losses_val += abs(pnl)

            stats["total_trades"] = len(trades)
            stats["trades_list"] = trades
            stats["gross_pnl"] = round(gains - losses_val, 2)
            if stats["total_trades"] > 0:
                stats["win_rate"] = round((stats["wins"] / stats["total_trades"]) * 100, 1)
            if losses_val > 0:
                stats["profit_factor"] = round(gains / losses_val, 2)
            elif gains > 0:
                stats["profit_factor"] = 99.0

            if trades:
                sorted_by_pnl = sorted(trades, key=lambda x: x["pnl"], reverse=True)
                stats["best_trade"] = sorted_by_pnl[0]
                stats["worst_trade"] = sorted_by_pnl[-1]

            # Query open positions
            try:
                cursor.execute("SELECT symbol, quantity, entry_price, current_price, pnl_pct FROM positions")
                pos_rows = cursor.fetchall()
                for p in pos_rows:
                    stats["current_positions"].append({
                        "symbol": p["symbol"],
                        "qty": p["quantity"],
                        "entry": p["entry_price"],
                        "curr": p["current_price"],
                        "pnl_pct": p["pnl_pct"]
                    })
            except Exception:
                pass

            conn.close()
        except Exception as e:
            logger.debug("Failed to query weekly stats: {}", e)

        return stats

    def generate_report(self) -> str:
        """Generates an executive weekly quant brief (HTML formatted for Telegram)."""
        stats = self._get_weekly_trade_stats()
        
        # 1. Prepare trade breakdown text
        pnl_emoji = "🟢" if stats["gross_pnl"] >= 0 else "🔴"
        pnl_sign = "+" if stats["gross_pnl"] >= 0 else ""
        
        best_str = f"{stats['best_trade']['symbol']} ({stats['best_trade']['pnl_pct']:+.1%}, ${stats['best_trade']['pnl']:+.2f})" if stats["best_trade"] else "해당 없음"
        worst_str = f"{stats['worst_trade']['symbol']} ({stats['worst_trade']['pnl_pct']:+.1%}, ${stats['worst_trade']['pnl']:+.2f})" if stats["worst_trade"] else "해당 없음"
        
        pos_lines = []
        for p in stats["current_positions"]:
            pos_lines.append(f"  • <b>{p['symbol']}</b>: {p['qty']}주 @ ${p['entry']:.2f} (손익 {p['pnl_pct']:+.1%})")
        pos_str = "\n".join(pos_lines) if pos_lines else "  • 현재 보유 포지션 없음 (100% 현금 대기)"

        # 2. Try Gemini AI commentary
        ai_commentary = ""
        if self.api_key:
            try:
                import google.generativeai as genai
                prompt = (
                    f"너는 세계 최정상 퀀트 헤지펀드 수석 펀드매니저야. "
                    f"아래 우리 봇의 최근 7일간 실전 매매 데이터를 바탕으로, 대표님(투자자)께 보고할 주간 퀀트 운용 코멘터리를 작성해줘.\n\n"
                    f"- 기간: {stats['start_date']} ~ {stats['end_date']}\n"
                    f"- 총 매매 건수: {stats['total_trades']}회 (승 {stats['wins']}회 / 패 {stats['losses']}회, 승률 {stats['win_rate']}%)\n"
                    f"- 7일 실현손익: {pnl_sign}${stats['gross_pnl']:.2f} (Profit Factor: {stats['profit_factor']})\n"
                    f"- 최고 수익 종목: {best_str}\n"
                    f"- 최대 손실 종목: {worst_str}\n"
                    f"- 활용 퀀트 팩터: 마크 미네르비니 VCP 돌파, 잔차 모멘텀, 다크풀 블록, 1D 칼만 필터, 볼륨 프로파일 POC\n\n"
                    f"요구사항: 1) 전문적이고 신뢰감 있는 헤지펀드 어조로, 2) 이번 주 시장 평가와 봇의 리스크 방어 성과를 3~4문장으로 명쾌하게 총평해줘."
                )
                for m_name in ["gemini-2.0-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"]:
                    try:
                        m = genai.GenerativeModel(m_name)
                        resp = m.generate_content(prompt)
                        if resp and resp.text:
                            ai_commentary = resp.text.strip()
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug("Gemini AI weekly commentary failed: {}", e)

        if not ai_commentary:
            ai_commentary = (
                "이번 주 알고리즘은 거시 변동성(CPI/FOMC) 쉴드와 VCP 돌파 엔진을 기반으로 "
                "철저한 리스크 관리 하에 주도주 수급을 추적하였습니다. "
                "계좌 고점(High-Water Mark) 보호와 동적 켈리 사이징을 통해 자본 보존을 최우선으로 안정적 운용을 지속하고 있습니다."
            )

        # Build Complete Telegram HTML Card
        report_html = (
            f"📜 <b>[주간 AI 퀀트 운용 보고서]</b>\n"
            f"<i>{stats['start_date']} ~ {stats['end_date']} (Weekly Executive Letter)</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{pnl_emoji} <b>7일 총 실현손익</b>: <code>{pnl_sign}${stats['gross_pnl']:.2f} USD</code>\n"
            f"🎯 <b>매매 전적</b>: {stats['total_trades']}전 {stats['wins']}승 {stats['losses']}패\n"
            f"📊 <b>승률 (Win Rate)</b>: <b>{stats['win_rate']}%</b>\n"
            f"⚖️ <b>Profit Factor</b>: <b>{stats['profit_factor']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🥇 <b>주간 최우수 종목</b>: {best_str}\n"
            f"🛡️ <b>주간 손절 방어 종목</b>: {worst_str}\n\n"
            f"💼 <b>현재 보유 포지션</b>:\n{pos_str}\n\n"
            f"🤖 <b>[수석 펀드매니저 AI 코멘터리]</b>:\n"
            f"<i>\"{ai_commentary}\"</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 <a href='http://141.148.172.12:8080'>실시간 웹 대시보드 바로가기</a>"
        )
        return report_html

if __name__ == "__main__":
    rep = WeeklyAIReportGenerator()
    print(rep.generate_report())
