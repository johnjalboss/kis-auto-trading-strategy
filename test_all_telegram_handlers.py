"""
Exhaustive Automated Diagnostic: Test Every Single Telegram Handler & Quant Subsystem
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.stdout.reconfigure(encoding='utf-8')

# Ensure current dir is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_interactive_bot import TelegramInteractiveBot

class TestTelegramHandlers(unittest.TestCase):
    def setUp(self):
        self.mock_orchestrator = MagicMock()
        self.mock_orchestrator.state = MagicMock()
        self.mock_orchestrator.state.current_regime = "BULL_TRENDING"
        self.mock_orchestrator.state.target_universe = ["NVDA", "AAPL", "MSFT"]
        self.bot = TelegramInteractiveBot(orchestrator_ref=self.mock_orchestrator)
        # Mock _send_reply and _send_photo to avoid network calls
        self.sent_messages = []
        self.bot._send_reply = lambda text, reply_markup=None: self.sent_messages.append(("text", text))
        self.bot._send_photo = lambda path, caption="": self.sent_messages.append(("photo", path, caption))
        self.bot._answer_callback = lambda cb_id, text="": self.sent_messages.append(("callback", cb_id, text))

    def test_all_handlers(self):
        handlers = [
            ("status", self.bot._handle_status),
            ("positions", self.bot._handle_positions),
            ("pnl_today", lambda: self.bot._handle_pnl("today")),
            ("pnl_weekly", lambda: self.bot._handle_pnl("weekly")),
            ("pnl_monthly", lambda: self.bot._handle_pnl("monthly")),
            ("pnl_total", lambda: self.bot._handle_pnl("total")),
            ("quant_status", self.bot._handle_quant_status),
            ("auto_tuning", self.bot._handle_auto_tuning),
            ("macro_dday", self.bot._handle_macro_dday),
            ("economic_surprise", self.bot._handle_economic_surprise),
            ("smart_money", self.bot._handle_smart_money),
            ("monte_carlo", self.bot._handle_monte_carlo),
            ("weekly_ai_report", self.bot._handle_weekly_ai_report),
            ("shadow_paper", self.bot._handle_shadow_paper),
            ("top_picks", self.bot._handle_top_picks),
            ("theme", self.bot._handle_theme),
            ("screener", self.bot._handle_screener),
            ("regime", self.bot._handle_regime),
            ("risk", self.bot._handle_risk),
            ("rotation", self.bot._handle_rotation),
            ("stock_charts_menu", self.bot._handle_stock_charts_menu),
            ("one_click_menu", self.bot._send_one_click_menu),
        ]

        errors = []
        for name, func in handlers:
            try:
                self.sent_messages.clear()
                func()
                # Verify that at least one message was generated and no error text was sent
                last_msg = self.sent_messages[-1] if self.sent_messages else None
                if not last_msg:
                    errors.append((name, "No message sent (silent failure)"))
                elif isinstance(last_msg[1], str) and ("실패" in last_msg[1] or "오류" in last_msg[1] or "Exception" in last_msg[1]):
                    errors.append((name, f"Handler returned error response: {last_msg[1][:100]}"))
                else:
                    print(f"  [OK] {name:<20}: Responded cleanly ({len(self.sent_messages)} msg/photo)")
            except Exception as e:
                errors.append((name, f"Unhandled exception: {str(e)}"))

        if errors:
            print(f"\n❌ FOUND {len(errors)} HANDLER ERRORS:")
            for n, err in errors:
                print(f"  • {n}: {err}")
            sys.exit(1)
        else:
            print("\n✅ ALL 21 TELEGRAM HANDLERS EXECUTED FLAWLESSLY WITH ZERO ERRORS!")


if __name__ == "__main__":
    t = TestTelegramHandlers()
    t.setUp()
    t.test_all_handlers()
