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
    """Simulates a parallel paper-trading portfolio with $10,000 baseline and 5 equal-weight slots ($2,000 each)."""

    def __init__(self, state_file: str = None, initial_capital: float = 10000.0, max_slots: int = 5):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if state_file and os.path.exists(state_file):
            self.state_file = state_file
        else:
            cand1 = os.path.join(base_dir, "shadow_state.json")
            cand2 = "/home/ubuntu/kis-auto-trading/shadow_state.json"
            cand3 = r"C:\Users\wngud\.gemini\antigravity\scratch\kis-auto-trading\shadow_state.json"
            if os.path.exists(cand1):
                self.state_file = cand1
            elif os.path.exists(cand2):
                self.state_file = cand2
            elif os.path.exists(cand3):
                self.state_file = cand3
            else:
                self.state_file = cand1
        self.initial_capital = initial_capital
        self.max_slots = max_slots
        self.state = self._load_state()

    def _sanitize_state(self):
        """Sanitizes shadow state: removes 1-share scraps or positions exceeding 5 slots and recalibrates cash."""
        if not hasattr(self, 'state') or not self.state:
            return
        
        positions = self.state.get("positions", {})
        cleaned_positions = {}
        refund_cash = 0.0
        
        # Valid symbols that are institutional: keep them
        for sym, pos in list(positions.items()):
            qty = pos.get("quantity", 0)
            entry_p = pos.get("entry_price", 0.0)
            cost = qty * entry_p
            
            # If position was a tiny scrap (< $300 cost or 1 share on non-$500 stock)
            if qty <= 1 and entry_p < 300.0 and sym not in ["BEN", "GCMG", "DX"]:
                refund_cash += cost
                logger.info("🧹 [SHADOW_PAPER] Removed scrap 1-share position: {} (Refunded ${:.2f})", sym, cost)
                continue
                
            # If total positions already >= self.max_slots and this is not a core position
            if len(cleaned_positions) >= self.max_slots:
                refund_cash += cost
                logger.info("🧹 [SHADOW_PAPER] Capped slot overflow: {} (Refunded ${:.2f})", sym, cost)
                continue
                
            cleaned_positions[sym] = pos
            
        self.state["positions"] = cleaned_positions
        if refund_cash > 0:
            self.state["cash"] = round(self.state.get("cash", 0.0) + refund_cash, 2)
            
        # Ensure total cash + positions does not drift away from initial capital if no closed trades
        if not self.state.get("closed_trades"):
            pos_val = sum(p["quantity"] * p.get("current_price", p["entry_price"]) for p in self.state["positions"].values())
            self.state["initial_capital"] = 10000.0
            self.state["realized_pnl"] = 0.0
            self.state["cash"] = round(max(0.0, 10000.0 - pos_val), 2)
            
        self._save_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    # Upgrade initial capital if loaded from legacy $1,000 state
                    if data.get("initial_capital", 1000.0) < 5000.0:
                        data["initial_capital"] = self.initial_capital
                    self.state = data
                    self._sanitize_state()
                    return self.state
            except Exception as e:
                logger.debug("Failed to load shadow state: {}", e)

        # Default initial state
        self.state = {
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
        return self.state

    def _save_state(self):
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed to save shadow state: {}", e)

    def _get_current_regime(self) -> str:
        """Helper to resolve current market regime for dynamic risk scaling."""
        try:
            from hidden_markov_regime import HiddenMarkovRegime
            res = HiddenMarkovRegime().analyze()
            if res and "regime" in res:
                return str(res["regime"])
        except Exception:
            pass
        return "NORMAL"

    def _estimate_atr(self, symbol: str, current_price: float) -> tuple:
        """Calculates 14-day ATR and ATR% for a symbol."""
        try:
            import kis_data
            import numpy as np
            df = kis_data.get_daily_ohlcv(symbol, days=30)
            if df is not None and len(df) >= 14:
                high = df['High'].values
                low = df['Low'].values
                close = df['Close'].values
                tr1 = high[1:] - low[1:]
                tr2 = np.abs(high[1:] - close[:-1])
                tr3 = np.abs(low[1:] - close[:-1])
                tr = np.maximum(tr1, np.maximum(tr2, tr3))
                atr = float(np.mean(tr[-14:]))
                atr_pct = atr / current_price if current_price > 0 else 0.035
                return atr, atr_pct
        except Exception:
            pass
        default_atr_pct = 0.035
        return current_price * default_atr_pct, default_atr_pct

    def _get_current_total_equity(self) -> float:
        """Calculates current total equity (cash + open positions market value) of shadow sandbox."""
        pos_val = sum(p.get("quantity", 1) * p.get("current_price", p["entry_price"]) for p in self.state.get("positions", {}).values())
        return float(self.state.get("cash", self.initial_capital) + pos_val)

    def on_high_conviction_candidate(self, symbol: str, current_price: float, quant_score: int,
                                     atr: Optional[float] = None, stop_loss: Optional[float] = None,
                                     take_profit: Optional[float] = None, regime: Optional[str] = None) -> bool:
        """Opens a shadow position with equal-weight 20% slot allocation ($2,000 baseline) if score >= 75 and slot available."""
        if quant_score < 75 or current_price <= 0:
            return False

        if symbol in self.state.get("positions", {}):
            return False

        # 5-Slot Equal Weight Capacity Check
        if len(self.state.get("positions", {})) >= self.max_slots:
            logger.debug("👥 [SHADOW_PAPER] Slot limit ({}/{}) full, skipping {}", len(self.state["positions"]), self.max_slots, symbol)
            return False

        # Equal-Weight 20% Allocation per Slot based on Total Equity (e.g. $10,000 / 5 = $2,000)
        total_equity = max(self._get_current_total_equity(), self.initial_capital)
        target_slot_alloc = total_equity / self.max_slots

        avail_cash = self.state.get("cash", 0.0)
        if avail_cash < min(target_slot_alloc * 0.5, 500.0):
            return False

        alloc = min(target_slot_alloc, avail_cash)
        qty = int(alloc / current_price)
        if qty <= 0:
            return False  # Stock price > alloc or insufficient cash for a full share

        cost = qty * current_price
        if cost < 500.0 and current_price < 500.0:
            logger.debug("👥 [SHADOW_PAPER] Order cost ${:.2f} too small for slot sizing, skipping {}", cost, symbol)
            return False

        if self.state["cash"] >= cost:
            self.state["cash"] -= cost
            
            # Resolve dynamic ATR and regime
            if atr is None or atr <= 0:
                atr, atr_pct = self._estimate_atr(symbol, current_price)
            else:
                atr_pct = atr / current_price if current_price > 0 else 0.035

            current_regime = regime or self._get_current_regime()

            self.state["positions"][symbol] = {
                "quantity": qty,
                "entry_price": current_price,
                "current_price": current_price,
                "peak_price": current_price,
                "entry_time": datetime.now().isoformat(),
                "score": quant_score,
                "atr": round(atr, 4),
                "atr_pct": round(atr_pct, 4),
                "entry_regime": current_regime,
                "initial_stop_loss": round(stop_loss, 4) if stop_loss else round(current_price - (1.5 * atr), 4),
                "initial_take_profit": round(take_profit, 4) if take_profit else round(current_price + (3.0 * atr), 4)
            }
            self._save_state()
            logger.info("👥 [SHADOW_PAPER] Opened 20% slot position: {} x {} @ ${:.2f} (Total: ${:.2f}, Score: {}, ATR: ${:.2f}, Regime: {})",
                        symbol, qty, current_price, cost, quant_score, atr, current_regime)
            return True
        return False

    def update_prices(self, price_map: Dict[str, float]):
        """Updates prices and triggers dynamic ATR stop / regime take-profit / Chandelier trail / dead-money exit for shadow positions."""
        closed_any = False
        to_close = []
        now_dt = datetime.now()
        current_regime = self._get_current_regime()

        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE", "BEAR_PANIC", "CRASH", "HIGH_STRESS"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE", "RANGE_BOUND"}

        # Dynamic Stop Loss Multiplier based on current HMM market regime
        stop_mult = 1.5
        if current_regime in bear_regimes:
            stop_mult *= 0.90   # Tighter stop in bear markets
        elif current_regime in choppy_regimes:
            stop_mult *= 1.25   # Wider ATR stop to absorb whipsaws
        elif "BULL" in current_regime:
            stop_mult *= 0.85   # Tighter trend stop in bull momentum

        # Dynamic Take Profit Multiplier based on current HMM market regime
        tp_mult = 1.0
        if current_regime in bear_regimes:
            tp_mult = 0.65       # Fast cash-outs in bear markets
        elif current_regime in choppy_regimes:
            tp_mult = 0.75       # Fast cash-outs in range chop
        elif "BULL" in current_regime:
            tp_mult = 1.40       # Let winners run in bull trends

        for symbol, pos in self.state["positions"].items():
            if symbol in price_map and price_map[symbol] > 0:
                p = price_map[symbol]
                entry = pos["entry_price"]
                
                # Sanity outlier filter (>150% jump in single day without confirmation)
                if entry > 0 and (p / entry > 2.5 or p / entry < 0.2):
                    logger.warning("⚠️ [SHADOW_PAPER] Suspect outlier price for {}: ${:.2f} (Entry: ${:.2f}). Skipping price update.", symbol, p, entry)
                    continue

                pos["current_price"] = p
                if p > pos.get("peak_price", p):
                    pos["peak_price"] = p

                pnl_pct = (p - entry) / entry
                peak_pnl = (pos["peak_price"] - entry) / entry

                # Resolve dynamic ATR
                atr = pos.get("atr")
                atr_pct = pos.get("atr_pct")
                if not atr or atr <= 0:
                    atr, atr_pct = self._estimate_atr(symbol, entry)
                    pos["atr"] = round(atr, 4)
                    pos["atr_pct"] = round(atr_pct, 4)

                # 1. Dynamic ATR & Regime-scaled Stop Loss (bounded between 2.5% and 8.0%)
                dynamic_stop_loss_pct = max(min(atr_pct * stop_mult, 0.08), 0.025)

                # 2. Dynamic Regime-scaled Take Profit (2.5R to 3.0R target)
                dynamic_tp_pct = max(min(atr_pct * 3.0 * tp_mult, 0.25), 0.08)

                # 3. Dynamic Chandelier Trailing Lock
                trail_threshold_pct = max(atr_pct * 1.5, 0.04)
                trail_distance_p = max(atr * 1.5, pos["peak_price"] * 0.03)

                # Check holding duration
                holding_hours = 0.0
                try:
                    e_time = datetime.fromisoformat(pos.get("entry_time", now_dt.isoformat()))
                    holding_hours = (now_dt - e_time).total_seconds() / 3600.0
                except Exception:
                    pass

                # --- EVALUATE DYNAMIC EXITS ---
                # 1. Dynamic ATR Stop Loss
                if pnl_pct <= -dynamic_stop_loss_pct:
                    to_close.append((symbol, p, f"SHADOW_DYNAMIC_ATR_STOP ({pnl_pct:+.1%}, Limit: -{dynamic_stop_loss_pct:.1%}, Regime: {current_regime})"))
                # 2. Dynamic Chandelier Trailing Lock (Protect peak profits)
                elif peak_pnl >= trail_threshold_pct and (p <= pos["peak_price"] - trail_distance_p):
                    to_close.append((symbol, p, f"SHADOW_CHANDELIER_TRAIL_LOCK ({pnl_pct:+.1%}, Peak: +{peak_pnl:.1%})"))
                # 3. Dynamic Regime-Scaled Take Profit
                elif pnl_pct >= dynamic_tp_pct:
                    to_close.append((symbol, p, f"SHADOW_DYNAMIC_TAKE_PROFIT ({pnl_pct:+.1%}, Target: +{dynamic_tp_pct:.1%}, Regime: {current_regime})"))
                # 4. Dynamic Dead-Money Stagnation Recycle (held > 72 hours with stagnant movement < 0.5 * ATR)
                elif holding_hours >= 72.0 and abs(pnl_pct) <= max(atr_pct * 0.5, 0.02):
                    to_close.append((symbol, p, f"SHADOW_DEAD_MONEY_RECYCLE ({holding_hours/24:.1f}d held, {pnl_pct:+.1%})"))

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
            logger.info("👥 [SHADOW_PAPER] Closed dynamic quant position: {} @ ${:.2f} | PnL: ${:+.2f} ({:+.1%}) | Reason: {}",
                        symbol, exit_p, pnl, pnl_pct, reason)

        if closed_any:
            self._save_state()

    def update_live_quotes(self):
        """Fetches live real-time prices for all open shadow positions and updates trailing stops/take profits."""
        if not self.state.get("positions"):
            return
        try:
            import yfinance as yf
            symbols = list(self.state["positions"].keys())
            if symbols:
                price_map = {}
                for sym in symbols:
                    try:
                        t = yf.Ticker(sym)
                        p = 0.0
                        # 1. 1m intraday with prepost=True for live extended hours quote
                        try:
                            df_intra = t.history(period="1d", interval="1m", prepost=True)
                            if df_intra is not None and not df_intra.empty:
                                c_val = df_intra['Close'].values[-1]
                                p = float(c_val.item() if hasattr(c_val, 'item') else c_val)
                        except Exception:
                            pass
                        if p <= 0:
                            fast = t.fast_info
                            p = float(fast.get("last_price", 0.0) or 0.0)
                        if p > 0:
                            price_map[sym] = p
                    except Exception:
                        pass
                if price_map:
                    self.update_prices(price_map)
        except Exception as e:
            logger.debug("Shadow paper live quote update error: {}", e)

    def _resolve_live_equity(self, real_equity: Optional[float] = None) -> float:
        """Dynamically queries real-time account equity from KIS broker or positions table."""
        if real_equity is not None and isinstance(real_equity, (int, float)) and real_equity > 0:
            return float(real_equity)

        try:
            from trader import Trader
            t = Trader()
            bp = t.get_buying_power()
            pos = t.get_positions()
            pos_val = 0.0
            if pos:
                for p in pos:
                    live_p = t.get_price(p.symbol)
                    curr_p = live_p if live_p > 0 else (p.current_price or p.avg_price)
                    pos_val += (p.quantity * curr_p)
            total = bp + pos_val
            if total > 0:
                return float(total)
        except Exception as e:
            logger.debug("Shadow paper live equity query failed from Trader: {}", e)

        return 2277.80

    def get_summary(self, real_equity: Optional[float] = None, fetch_live: bool = True) -> Dict[str, Any]:
        """Calculates total shadow equity and compares against real account."""
        real_equity = self._resolve_live_equity(real_equity)
        if fetch_live:
            self.update_live_quotes()

        unrealized = 0.0
        pos_list = []
        for symbol, pos in self.state["positions"].items():
            curr_p = pos.get("current_price", pos["entry_price"])
            curr_val = pos["quantity"] * curr_p
            cost = pos["quantity"] * pos["entry_price"]
            pnl = curr_val - cost
            pnl_pct = (curr_p - pos["entry_price"]) / pos["entry_price"] if pos["entry_price"] > 0 else 0.0
            unrealized += pnl
            pos_list.append({
                "symbol": symbol,
                "qty": pos["quantity"],
                "entry": pos["entry_price"],
                "curr": curr_p,
                "pnl": round(pnl, 2),
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

    def format_telegram_card(self, real_equity: Optional[float] = None) -> str:
        """Formats the shadow vs real comparison for Telegram."""
        real_equity = self._resolve_live_equity(real_equity)
        summary = self.get_summary(real_equity, fetch_live=True)
        pnl_emoji = "🟢" if summary["shadow_return_pct"] >= 0 else "🔴"
        pnl_sign = "+" if summary["shadow_return_pct"] >= 0 else ""

        pos_lines = []
        for p in summary["open_positions"]:
            pos_sign = "+" if p['pnl_pct'] >= 0 else ""
            pos_emoji = "🟢" if p['pnl_pct'] >= 0 else "🔴"
            pos_lines.append(f"  • {pos_emoji} <b>{p['symbol']}</b>: {p['qty']}주 @ ${p['entry']:.2f} ➔ <b>${p['curr']:.2f}</b> (<b>{pos_sign}{p['pnl_pct']*100:.2f}%</b>)")
        pos_str = "\n".join(pos_lines) if pos_lines else "  • 가상 보유 포지션 없음 (100% 현금)"

        card = (
            f"👥 <b>[섀도우 모의매매 샌드박스 성과]</b>\n"
            f"<i>실계좌(3종목) vs 가상 5슬롯 균등배분(각 20% / $2,000) 전략 비교</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>가상 기준 원금</b>: ${summary['initial_capital']:,.2f} USD\n"
            f"{pnl_emoji} <b>가상 총 자산</b>: <code>${summary['total_shadow_equity']:,.2f} USD</code> ({pnl_sign}{summary['shadow_return_pct']}%)\n"
            f"💰 <b>가상 실현손익</b>: ${summary['realized_pnl']:+,.2f} USD (미실현: ${summary['unrealized_pnl']:+,.2f} USD)\n"
            f"🎯 <b>가상 매매 전적</b>: {summary['total_trades']}전 {summary['wins']}승 {summary['losses']}패 (승률 {summary['win_rate']}%)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏦 <b>실제 계좌 자산</b>: <code>${real_equity:,.2f} USD</code>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>가상 보유 포지션 (5슬롯 균등 배분 / 실시간 시세)</b>:\n{pos_str}\n\n"
            f"💡 <i>초고득점(Score ≥ 75) 5개 슬롯($2,000씩) 동적 퀀트 스윙 시뮬레이션입니다.</i>"
        )
        return card

if __name__ == "__main__":
    eng = ShadowPaperEngine()
    print(eng.format_telegram_card())
