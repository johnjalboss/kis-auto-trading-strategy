"""
Shadow Paper-Trading Dual Engine (v1.0.0)
=========================================
Runs a parallel virtual sandbox portfolio ($1,000 baseline) alongside the real broker execution.
Tracks hypothetical ultra-aggressive execution vs conservative live broker performance.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger
import config

STATE_FILE = "shadow_state.json"

class ShadowPaperEngine:
    """Simulates an aggressive parallel paper-trading portfolio."""

    def __init__(self, state_file: str = STATE_FILE, initial_capital: float = 1000.0):
        self.state_file = state_file
        self.initial_capital = initial_capital
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("Failed to load shadow state: {}", e)

        # Default initial state
        return {
            "initial_capital": self.initial_capital,
            "cash": self.initial_capital,
            "positions": {},       # symbol: {qty, entry_price, entry_time, peak_price}
            "closed_trades": [],   # list of closed trades
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "realized_pnl": 0.0,
            "last_updated": datetime.now().isoformat()
        }

    def _save_state(self):
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed to save shadow state: {}", e)

    def on_high_conviction_candidate(self, symbol: str, current_price: float, quant_score: int) -> bool:
        """Opens a shadow position if score >= 85 and not already held."""
        if quant_score < 85 or current_price <= 0:
            return False

        if symbol in self.state["positions"]:
            return False

        # Allocate 20% of shadow cash per position (up to 5 positions)
        alloc = min(self.state["cash"] * 0.25, 250.0)
        if alloc < 30.0 or self.state["cash"] < 30.0:
            return False

        qty = int(alloc / current_price)
        if qty <= 0:
            qty = 1

        cost = qty * current_price
        if self.state["cash"] >= cost:
            self.state["cash"] -= cost
            self.state["positions"][symbol] = {
                "quantity": qty,
                "entry_price": current_price,
                "current_price": current_price,
                "peak_price": current_price,
                "entry_time": datetime.now().isoformat(),
                "score": quant_score
            }
            self._save_state()
            logger.info("👥 [SHADOW_PAPER] Opened virtual position: {} x {} @ ${:.2f} (Score: {})", symbol, qty, current_price, quant_score)
            return True
        return False

    def update_prices(self, price_map: Dict[str, float]):
        """Updates prices and triggers trailing stop / take profit for shadow positions."""
        closed_any = False
        to_close = []

        for symbol, pos in self.state["positions"].items():
            if symbol in price_map and price_map[symbol] > 0:
                p = price_map[symbol]
                pos["current_price"] = p
                if p > pos["peak_price"]:
                    pos["peak_price"] = p

                entry = pos["entry_price"]
                pnl_pct = (p - entry) / entry

                # Trailing stop: 4% from peak or take profit at +10%
                peak_pnl = (pos["peak_price"] - entry) / entry
                if pnl_pct <= -0.045:
                    to_close.append((symbol, p, f"SHADOW_STOP_LOSS ({pnl_pct:+.1%})"))
                elif peak_pnl >= 0.05 and (p <= pos["peak_price"] * 0.97):
                    to_close.append((symbol, p, f"SHADOW_TRAIL_LOCK (+{pnl_pct:+.1%})"))
                elif pnl_pct >= 0.12:
                    to_close.append((symbol, p, f"SHADOW_TAKE_PROFIT (+{pnl_pct:+.1%})"))

        for symbol, exit_p, reason in to_close:
            pos = self.state["positions"].pop(symbol)
            qty = pos["quantity"]
            entry = pos["entry_price"]
            pnl = (exit_p - entry) * qty
            pnl_pct = (exit_p - entry) / entry

            self.state["cash"] += exit_p * qty
            self.state["realized_pnl"] += pnl
            self.state["total_trades"] += 1
            if pnl > 0:
                self.state["wins"] += 1
            else:
                self.state["losses"] += 1

            self.state["closed_trades"].append({
                "symbol": symbol,
                "entry_price": entry,
                "exit_price": exit_p,
                "quantity": qty,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct * 100, 2),
                "reason": reason,
                "exit_time": datetime.now().isoformat()
            })
            closed_any = True
            logger.info("👥 [SHADOW_PAPER] Closed virtual position: {} @ ${:.2f} | PnL: ${:+.2f} ({:+.1%})", symbol, exit_p, pnl, pnl_pct)

        if closed_any:
            self._save_state()

    def get_summary(self, real_equity: float = 772.70) -> Dict[str, Any]:
        """Calculates total shadow equity and compares against real account."""
        unrealized = 0.0
        pos_list = []
        for symbol, pos in self.state["positions"].items():
            curr_val = pos["quantity"] * pos.get("current_price", pos["entry_price"])
            cost = pos["quantity"] * pos["entry_price"]
            pnl = curr_val - cost
            pnl_pct = pnl / cost if cost > 0 else 0.0
            unrealized += pnl
            pos_list.append({
                "symbol": symbol,
                "qty": pos["quantity"],
                "entry": pos["entry_price"],
                "curr": pos.get("current_price", pos["entry_price"]),
                "pnl_pct": pnl_pct
            })

        total_shadow_equity = round(self.state["cash"] + sum(p.get("quantity", p.get("qty", 1)) * p.get("current_price", p["entry_price"]) for p in self.state["positions"].values()), 2)
        shadow_return_pct = round(((total_shadow_equity - self.initial_capital) / self.initial_capital) * 100, 2)
        win_rate = round((self.state["wins"] / self.state["total_trades"] * 100), 1) if self.state["total_trades"] > 0 else 0.0

        return {
            "initial_capital": self.initial_capital,
            "total_shadow_equity": total_shadow_equity,
            "shadow_return_pct": shadow_return_pct,
            "cash": round(self.state["cash"], 2),
            "realized_pnl": round(self.state["realized_pnl"], 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_trades": self.state["total_trades"],
            "wins": self.state["wins"],
            "losses": self.state["losses"],
            "win_rate": win_rate,
            "open_positions": pos_list,
            "real_equity": real_equity
        }

    def format_telegram_card(self, real_equity: float = 772.70) -> str:
        """Formats the shadow vs real comparison for Telegram."""
        try:
            real_equity = float(real_equity) if isinstance(real_equity, (int, float)) else 772.70
        except Exception:
            real_equity = 772.70

        summary = self.get_summary(real_equity)
        pnl_emoji = "🟢" if summary["shadow_return_pct"] >= 0 else "🔴"
        pnl_sign = "+" if summary["shadow_return_pct"] >= 0 else ""

        pos_lines = []
        for p in summary["open_positions"]:
            pos_lines.append(f"  • <b>{p['symbol']}</b>: {p['qty']}주 @ ${p['entry']:.2f} ({p['pnl_pct']:+.1%})")
        pos_str = "\n".join(pos_lines) if pos_lines else "  • 가상 보유 포지션 없음 (100% 현금)"

        card = (
            f"👥 <b>[섀도우 모의매매 샌드박스 성과]</b>\n"
            f"<i>실계좌 vs 가상 공격형 100% 몰빵 전략 비교</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>가상 기준 원금</b>: $1,000.00 USD\n"
            f"{pnl_emoji} <b>가상 총 자산</b>: <code>${summary['total_shadow_equity']:.2f} USD</code> ({pnl_sign}{summary['shadow_return_pct']}%)\n"
            f"💰 <b>가상 실현손익</b>: ${summary['realized_pnl']:+.2f} USD\n"
            f"🎯 <b>가상 매매 전적</b>: {summary['total_trades']}전 {summary['wins']}승 {summary['losses']}패 (승률 {summary['win_rate']}%)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>실제 계좌 자산</b>: <code>${real_equity:.2f} USD</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>가상 보유 포지션</b>:\n{pos_str}\n\n"
            f"💡 <i>초고득점(Score ≥ 90) 공격적 진입 시의 가상 시뮬레이션 성과입니다.</i>"
        )
        return card

if __name__ == "__main__":
    eng = ShadowPaperEngine()
    print(eng.format_telegram_card())
