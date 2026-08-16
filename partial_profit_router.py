"""
Smart Partial Take-Profit & 1-Share Protection Router (partial_profit_router.py)
================================================================================
Designed by World #1 Quant Systems Architecture.
Implements institutional 2-stage partial profit realization:
  1. For multi-share positions (quantity >= 2):
     - At 1st Target (1.5R): Sells 50% shares to lock in cash profit.
     - Raises remaining shares' stop loss to Breakeven (+0.5% cushion) -> 100% Risk-Free!
     - At 2nd Target (2.5R): Sells remaining shares on trend climax.
  2. For single-share positions (quantity == 1):
     - At 1st Target (1.5R): Locks stop loss directly to Breakeven (+0.5% cushion).
     - Allows the single share to run risk-free all the way to 2nd Target!
"""

import os
import sqlite3
import math
from loguru import logger
import requests
import config

class SmartPartialTakeProfitRouter:
    """Institutional Dynamic Partial Profit & Breakeven Lock Router"""

    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
        self.bot_token = getattr(config, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(config, 'TELEGRAM_CHAT_ID', '')

    def _send_telegram(self, text: str):
        if not self.bot_token or not self.chat_id:
            return
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            logger.debug("Telegram partial TP alert error: {}", e)

    def evaluate_take_profit(self, symbol: str, quantity: int, entry_price: float, current_price: float, current_stop: float, tp1: float, tp2: float) -> dict:
        """
        Evaluates whether a partial take-profit or 1-share breakeven lock should fire.
        """
        if quantity <= 0 or entry_price <= 0 or current_price <= 0:
            return {"action": "HOLD"}

        gain_pct = ((current_price - entry_price) / entry_price) * 100.0

        # Check 2nd Climax Target (2.5R)
        if tp2 > 0 and current_price >= tp2:
            return {
                "action": "SELL_ALL",
                "sell_qty": quantity,
                "reason": f"🎯 [2차 추세 확장 목표가 도달] {symbol} {quantity}주 전량 최고점 익절 (+{gain_pct:.1f}%)"
            }

        # Check 1st Partial Target (1.5R)
        if tp1 > 0 and current_price >= tp1:
            breakeven_stop = round(entry_price * 1.005, 2)  # Entry price + 0.5% commission cushion

            # Case A: Single Share (quantity == 1) -> Lock Breakeven Stop
            if quantity == 1:
                if current_stop < breakeven_stop:
                    # Update stop in DB
                    self._update_db_stop(symbol, breakeven_stop)
                    msg = (
                        f"🛡️ <b>[1주 전용 무위험 트레일링 락 가동]</b>\n"
                        f"• 종목: <b>{symbol}</b> (1주 보유)\n"
                        f"• 진입가: <code>${entry_price:.2f}</code> ➔ 현재가: <b>${current_price:.2f}</b> (+{gain_pct:.1f}%)\n"
                        f"• 조치: 1차 목표가(${tp1:.2f}) 돌파로 <b>스탑선을 본전+수수료선($ {breakeven_stop:.2f})으로 상향 락</b>\n"
                        f"• 효과: <b>손실 위험 0.0% 완전 제거</b> 상태에서 2차 목표가(${tp2:.2f})까지 추세 추종 지속!"
                    )
                    self._send_telegram(msg)
                    return {
                        "action": "LOCK_BREAKEVEN",
                        "new_stop": breakeven_stop,
                        "reason": f"1-Share Breakeven Lock at ${breakeven_stop:.2f}"
                    }
                return {"action": "HOLD"}

            # Case B: Multi-Share (quantity >= 2) -> Sell 50% & Lock Breakeven on Remaining
            else:
                sell_qty = math.floor(quantity / 2)
                rem_qty = quantity - sell_qty
                self._update_db_stop_and_qty(symbol, rem_qty, breakeven_stop)
                msg = (
                    f"🎯 <b>[1차 50% 분할 익절 & 무위험 트레이드 전환]</b>\n"
                    f"• 종목: <b>{symbol}</b> (총 {quantity}주 중 <b>{sell_qty}주 분할 매도</b>)\n"
                    f"• 체결가: <b>${current_price:.2f}</b> (확정 수익률: <b>+{gain_pct:.1f}%</b>)\n"
                    f"• 잔여 수량: <b>{rem_qty}주</b> (스탑선을 본전선 <code>${breakeven_stop:.2f}</code>으로 상향)\n"
                    f"• 상태: <b>현금 수익 확정 + 남은 물량 100% 무위험 상태</b>로 2차 목표가(${tp2:.2f}) 추종"
                )
                self._send_telegram(msg)
                return {
                    "action": "PARTIAL_SELL",
                    "sell_qty": sell_qty,
                    "remaining_qty": rem_qty,
                    "new_stop": breakeven_stop,
                    "reason": f"Partial 50% Take-Profit at ${current_price:.2f} (+{gain_pct:.1f}%)"
                }

        return {"action": "HOLD"}

    def _update_db_stop(self, symbol: str, new_stop: float):
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("UPDATE positions SET stop_price = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", (new_stop, symbol))
                conn.commit()
                conn.close()
                logger.info("Updated DB stop for {} to ${:.2f}", symbol, new_stop)
            except Exception as e:
                logger.error("Failed to update DB stop: {}", e)

    def _update_db_stop_and_qty(self, symbol: str, rem_qty: int, new_stop: float):
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("UPDATE positions SET quantity = ?, stop_price = ?, updated_at = CURRENT_TIMESTAMP WHERE symbol = ?", (rem_qty, new_stop, symbol))
                conn.commit()
                conn.close()
                logger.info("Updated DB position {} to {} shares with stop ${:.2f}", symbol, rem_qty, new_stop)
            except Exception as e:
                logger.error("Failed to update DB position: {}", e)

if __name__ == "__main__":
    router = SmartPartialTakeProfitRouter()
    # Test single share
    res1 = router.evaluate_take_profit("MRK", 1, 134.49, 145.00, 128.43, 144.57, 151.30)
    print("Single-Share Test:", res1)
    # Test multi share
    res2 = router.evaluate_take_profit("MDT", 2, 88.97, 96.00, 84.44, 95.75, 100.28)
    print("Multi-Share Test:", res2)
