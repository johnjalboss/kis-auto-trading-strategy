"""
Risk Manager - Daily Stop Loss & Position Limits
=================================================
Manages trading risk with daily limits, consecutive loss detection,
and position concentration controls.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List
from loguru import logger
import pytz

import config


@dataclass
class DailyStats:
    """Daily trading statistics"""
    date: date
    starting_balance: float = 0.0
    current_balance: float = 0.0
    intraday_peak: float = 0.0
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    gross_pnl: float = 0.0
    consecutive_losses: int = 0
    max_drawdown: float = 0.0
    
    @property
    def net_pnl(self) -> float:
        return self.current_balance - self.starting_balance
    
    @property
    def pnl_pct(self) -> float:
        if self.starting_balance == 0:
            return 0.0
        return (self.current_balance - self.starting_balance) / self.starting_balance
    
    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0


@dataclass 
class PositionRisk:
    """Position-level risk tracking"""
    symbol: str
    entry_price: float
    current_price: float
    quantity: int
    exposure_pct: float  # % of portfolio
    
    @property
    def pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


class RiskManager:
    """
    Trading Risk Management System
    
    Features:
    1. Daily Stop Loss - Halt trading when daily loss exceeds threshold
    2. Consecutive Loss Cooldown - Pause after N consecutive losses
    3. Position Limits - Max exposure per stock and total positions
    4. Max Drawdown Tracking - Monitor peak-to-trough decline
    """
    
    # Default thresholds (Refined Quant Parameters)
    DAILY_STOP_LOSS_PCT = 0.05  # 5% daily max loss (allows normal swing portfolio volatility)
    CONSECUTIVE_LOSS_LIMIT = 5  # Pause after 5 losses (avoids stopping out completely during a normal red day)
    COOLDOWN_MINUTES = 60  # 1 hour cooldown
    MAX_POSITION_PCT = 0.20  # 20% max per position (forces diversification)
    MAX_TOTAL_POSITIONS = 5  # Max concurrent positions
    
    def __init__(self):
        self._daily_stats: Optional[DailyStats] = None
        self._trading_halted = False
        self._cooldown_until: Optional[datetime] = None
        self._positions: Dict[str, PositionRisk] = {}
        
        # ★ 주간 드로다운 추적
        self._weekly_pnl: float = 0.0
        self._week_start_date: Optional[date] = None
        self._weekly_halted = False
        self.weekly_stop_pct = 0.10  # 10% 주간 손실 한도 (스윙 매매의 V자 반등을 버티기 위한 넉넉한 룸)
        
        # Load from config if available
        self.daily_stop_pct = getattr(config, 'DAILY_STOP_LOSS_PCT', self.DAILY_STOP_LOSS_PCT)
        self.consecutive_limit = getattr(config, 'CONSECUTIVE_LOSS_LIMIT', self.CONSECUTIVE_LOSS_LIMIT)
        self.cooldown_mins = getattr(config, 'COOLDOWN_MINUTES', self.COOLDOWN_MINUTES)
        self.max_position_pct = getattr(config, 'MAX_POSITION_PCT', self.MAX_POSITION_PCT)
        self.max_positions = getattr(config, 'MAX_POSITIONS', self.MAX_TOTAL_POSITIONS)

    def get_systemic_risk_multiplier(self) -> float:
        """
        Geopolitical Yen Carry & Systemic Risk Shield (Option 3)
        Returns a risk multiplier based on Yen Carry Trade monitor & VIX term structure.
        Also dynamically updates self.max_positions and alerts if high risk!
        """
        multiplier = 1.0
        
        # 1. Yen Carry Trade Unwinding Risk Check
        try:
            from yen_carry import get_yen_carry
            yc = get_yen_carry()
            sig = yc.analyze()
            
            logger.info("[YEN_SHIELD] Carry Status: {} | Unwind Risk: {} | Severity: {}/100", 
                        sig.carry_status, sig.unwind_risk, sig.impact_severity)
            
            if sig.carry_status == "CRISIS" or sig.unwind_risk == "CRITICAL":
                multiplier *= 0.25
                self.max_positions = 1
                logger.warning("🚨 [YEN_SHIELD] CRITICAL Yen Carry Unwind detected! Clamping risk multiplier to 25% and slots to 1.")
            elif sig.carry_status == "UNWINDING" or sig.unwind_risk == "HIGH":
                multiplier *= 0.50
                self.max_positions = 2
                logger.warning("⚠️ [YEN_SHIELD] HIGH Yen Carry Unwind detected! Clamping risk multiplier to 50% and slots to 2.")
            elif sig.carry_status == "UNSTABLE" or sig.unwind_risk == "MEDIUM":
                multiplier *= 0.75
                self.max_positions = 3
                logger.info("⚡ [YEN_SHIELD] MEDIUM Yen Carry Unwind detected! Clamping risk multiplier to 75% and slots to 3.")
            else:
                # Restore default max positions from config
                self.max_positions = getattr(config, 'MAX_POSITIONS', self.MAX_TOTAL_POSITIONS)
        except Exception as e:
            logger.error("[YEN_SHIELD] Failed to analyze Yen Carry: {}", e)

        # 2. VIX Structure / Tail Risk Check
        try:
            from vix_structure import get_vix_metrics
            vix_sig = get_vix_metrics()
            
            logger.info("[VIX_SHIELD] VIX: {:.2f} | Term Structure: {} | Vol Regime: {}", 
                        vix_sig.vix, vix_sig.term_structure, vix_sig.vol_regime)
            
            if vix_sig.vol_regime == "EXTREME" or vix_sig.term_structure == "BACKWARDATION":
                if vix_sig.vix > 35:
                    multiplier *= 0.40
                    self.max_positions = min(self.max_positions, 1)
                    logger.warning("🚨 [VIX_SHIELD] EXTREME VIX regime! Clamping risk multiplier by additional 40% and slots to 1.")
                elif vix_sig.vix > 25:
                    multiplier *= 0.70
                    self.max_positions = min(self.max_positions, 2)
                    logger.warning("⚠️ [VIX_SHIELD] HIGH VIX regime! Clamping risk multiplier by additional 70% and slots to 2.")
        except Exception as e:
            logger.error("[VIX_SHIELD] Failed to analyze VIX: {}", e)

        # Final safety clamp
        multiplier = max(0.10, min(1.20, multiplier))
        return multiplier
    
    # ==============================================
    # Daily Stats Management
    # ==============================================
    
    def _get_us_trading_date(self) -> date:
        """미국 트레이딩 세션 기준 날짜 (핵심 수정)
        
        KST 23:30~06:00 = US 장중
        KST 자정(00:00) 넘어가도 같은 US 트레이딩 세션
        ET 기준으로 날짜를 반환해야 장중에 리셋이 안 됨
        """
        try:
            et = pytz.timezone('US/Eastern')
            return datetime.now(et).date()
        except Exception:
            return date.today()
    
    def start_day(self, starting_balance: float):
        """Initialize daily tracking (★ US 세션 기준)"""
        today = self._get_us_trading_date()
        
        # Reset if new day
        if self._daily_stats is None or self._daily_stats.date != today:
            self._daily_stats = DailyStats(
                date=today,
                starting_balance=starting_balance,
                current_balance=starting_balance,
                intraday_peak=starting_balance
            )
            self._trading_halted = False
            self._cooldown_until = None
            
            # ★ [QUANT RISK v1.0.9] 주간 드로다운 및 누적 P&L 복원 메커니즘
            # 단순 0.0 초기화가 아닌, trades.db 데이터베이스에서 
            # 이번 주 월요일 00:00:00 EST 이후 완료된 거래 손익의 실질 합계액을 쿼리하여 복원
            current_week_monday = today - timedelta(days=today.weekday())
            is_new_week = (self._week_start_date is None or 
                           self._week_start_date < current_week_monday)
            if is_new_week:
                self._week_start_date = current_week_monday
                self._weekly_halted = False
                
                # 이번 주 월요일(EST) 계산
                et = pytz.timezone('US/Eastern')
                now_et = datetime.now(et)
                monday_et = now_et - timedelta(days=now_et.weekday())
                monday_start_str = monday_et.strftime("%Y-%m-%d 00:00:00")
                
                self._weekly_pnl = 0.0
                
                # trades.db에서 이번 주 실거래 P&L 누적값 복원 시도
                db_path = "trades.db"
                if os.path.exists(db_path):
                    conn = None
                    try:
                        conn = sqlite3.connect(db_path)
                        cur = conn.cursor()
                        # 이번 주 월요일 00:00 이후 완료된 매매 pnl 합계 조회
                        cur.execute("""
                            SELECT SUM(pnl) FROM trades 
                            WHERE exit_time IS NOT NULL AND exit_time >= ?
                        """, (monday_start_str,))
                        res = cur.fetchone()
                        if res and res[0] is not None:
                            self._weekly_pnl = float(res[0])
                            logger.info("[QUANT_RISK] Successfully recovered weekly P&L from DB: ${:+,.2f} since {}", 
                                        self._weekly_pnl, monday_start_str)
                    except Exception as q_err:
                        logger.error("[QUANT_RISK] Failed to query weekly P&L: {}", q_err)
                    finally:
                        if conn:
                            conn.close()
                else:
                    logger.debug("[QUANT_RISK] trades.db not found for weekly recovery, starting from 0.0")
                
                # 복원된 누적 주간 P&L에 따른 리스크 정지 선제 체크
                self._check_weekly_stop()
                logger.info("Weekly stats reset/recovered")
            
            logger.info("Risk Manager: Day started with ${:,.2f} (US date: {})", 
                       starting_balance, today)
    
    def update_balance(self, new_balance: float):
        """Update current balance and check limits"""
        if self._daily_stats is None:
            return
        
        self._daily_stats.current_balance = new_balance
        
        # Track max drawdown using running intraday peak
        self._daily_stats.intraday_peak = max(self._daily_stats.intraday_peak, new_balance)
        peak = self._daily_stats.intraday_peak
        current_drawdown = (peak - new_balance) / peak if peak > 0 else 0
        self._daily_stats.max_drawdown = max(self._daily_stats.max_drawdown, current_drawdown)
        
        # Check daily stop loss
        self._check_daily_stop()
    
    def record_trade(self, pnl: float, is_win: bool):
        """Record trade result"""
        if self._daily_stats is None:
            return
        
        self._daily_stats.trades_count += 1
        self._daily_stats.gross_pnl += pnl
        
        # ★ 주간 P&L 누적
        self._weekly_pnl += pnl
        
        if is_win:
            self._daily_stats.wins += 1
            self._daily_stats.consecutive_losses = 0
        else:
            self._daily_stats.losses += 1
            self._daily_stats.consecutive_losses += 1
            self._check_consecutive_losses()
        
        # ★ 주간 드로다운 체크
        self._check_weekly_stop()
    
    # ==============================================
    # Risk Checks
    # ==============================================
    
    def _check_daily_stop(self):
        """Check if daily stop loss triggered"""
        if self._daily_stats is None:
            return
        
        pnl_pct = self._daily_stats.pnl_pct
        
        if pnl_pct <= -self.daily_stop_pct and not self._trading_halted:
            self._trading_halted = True
            logger.warning("DAILY STOP LOSS TRIGGERED: {:.1%} loss", abs(pnl_pct))
            
            # Notify
            from notifier import get_notifier
            get_notifier().daily_stop_triggered(pnl_pct, self.daily_stop_pct)
    
    def _check_consecutive_losses(self):
        """Check consecutive loss limit"""
        if self._daily_stats is None:
            return
        
        if self._daily_stats.consecutive_losses >= self.consecutive_limit:
            from datetime import timedelta
            self._cooldown_until = datetime.now() + timedelta(minutes=self.cooldown_mins)
            
            logger.warning("CONSECUTIVE LOSS LIMIT: {} losses, cooling down {}min",
                          self._daily_stats.consecutive_losses, self.cooldown_mins)
            
            # Notify
            from notifier import get_notifier
            get_notifier().consecutive_loss(
                self._daily_stats.consecutive_losses, 
                self.cooldown_mins
            )
    
    def can_trade(self) -> tuple:
        """
        Check if trading is allowed
        
        Returns:
            (allowed: bool, reason: str)
        """
        # ★ 주간 드로다운 확인
        if self._weekly_halted:
            return False, f"Weekly stop: ${self._weekly_pnl:,.0f} loss this week"
        
        # Check daily halt
        if self._trading_halted:
            return False, "Daily stop loss triggered"
        
        # Check cooldown
        if self._cooldown_until:
            if datetime.now() < self._cooldown_until:
                delta = self._cooldown_until - datetime.now()
                remaining = max(0, int(delta.total_seconds())) // 60
                return False, f"Cooldown: {remaining}min remaining"
            else:
                self._cooldown_until = None
        
        # Check max positions
        if len(self._positions) >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"
        
        return True, "OK"
    
    def _check_weekly_stop(self):
        """★ 주간 드로다운 체크"""
        if self._daily_stats is None:
            return
        starting = self._daily_stats.starting_balance
        # [BUG FIX v1.0.9] 오직 주간 P&L이 손실(self._weekly_pnl < 0)일 때만 주간 정지가 동작하도록 수정
        # 이전: abs(self._weekly_pnl)로 인해 주간 10% 이상 수익이 났을 때도 계좌를 강제 정지하는 치명적인 논리 결함 존재.
        if starting > 0 and self._weekly_pnl < 0 and abs(self._weekly_pnl) / starting > self.weekly_stop_pct:
            self._weekly_halted = True
            logger.warning("WEEKLY STOP: ${:,.0f} loss ({:.1%} of balance)",
                         self._weekly_pnl, self._weekly_pnl / starting)
            from notifier import get_notifier
            get_notifier().system_status("WEEKLY STOP", 
                f"Weekly loss ${self._weekly_pnl:,.0f} exceeds {self.weekly_stop_pct:.0%} limit")
    
    # ==============================================
    # Position Management
    # ==============================================
    
    def check_position_limit(self, symbol: str, amount: float, 
                            total_portfolio: float) -> tuple:
        """
        Check if position size is within limits
        
        Returns:
            (allowed: bool, adjusted_amount: float, reason: str)
        """
        if total_portfolio <= 0:
            return False, 0, "Invalid portfolio value"
        
        exposure_pct = amount / total_portfolio
        
        # Check single position limit
        if exposure_pct > self.max_position_pct:
            adjusted = total_portfolio * self.max_position_pct
            return True, adjusted, f"Reduced to {self.max_position_pct:.0%} limit"
        
        # Check if already have position in symbol
        if symbol in self._positions:
            existing = self._positions[symbol]
            new_exposure = (existing.exposure_pct * total_portfolio + amount) / total_portfolio
            
            if new_exposure > self.max_position_pct:
                remaining = self.max_position_pct - existing.exposure_pct
                adjusted = max(0, remaining * total_portfolio)
                return True, adjusted, f"Adding to existing position, capped at {self.max_position_pct:.0%}"
        
        return True, amount, "OK"
    
    def add_position(self, symbol: str, entry_price: float, quantity: int,
                    exposure_pct: float):
        """Track new position"""
        self._positions[symbol] = PositionRisk(
            symbol=symbol,
            entry_price=entry_price,
            current_price=entry_price,
            quantity=quantity,
            exposure_pct=exposure_pct
        )
    
    def update_position(self, symbol: str, current_price: float):
        """Update position price"""
        if symbol in self._positions:
            self._positions[symbol].current_price = current_price
    
    def remove_position(self, symbol: str):
        """Remove closed position"""
        if symbol in self._positions:
            del self._positions[symbol]
    
    # ==============================================
    # Reports
    # ==============================================
    
    def get_daily_stats(self) -> Optional[DailyStats]:
        """Get current day's stats"""
        return self._daily_stats
    
    def get_risk_summary(self) -> dict:
        """Get current risk status"""
        can_trade, reason = self.can_trade()
        
        return {
            "can_trade": can_trade,
            "reason": reason,
            "trading_halted": self._trading_halted,
            "positions_count": len(self._positions),
            "positions_limit": self.max_positions,
            "daily_pnl_pct": self._daily_stats.pnl_pct if self._daily_stats else 0,
            "consecutive_losses": self._daily_stats.consecutive_losses if self._daily_stats else 0,
        }
    
    def reset_cooldown(self):
        """Manually reset cooldown (for testing)"""
        self._cooldown_until = None
        if self._daily_stats:
            self._daily_stats.consecutive_losses = 0
        logger.info("Cooldown reset")


# Global instance
_risk_manager = None

def get_risk_manager() -> RiskManager:
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing RiskManager...")
    rm = RiskManager()
    
    # Simulate day
    rm.start_day(10000)
    
    # Simulate trades
    rm.record_trade(-50, False)
    rm.record_trade(-30, False)
    rm.record_trade(-40, False)  # Should trigger cooldown
    
    can_trade, reason = rm.can_trade()
    print(f"\nCan Trade: {can_trade}")
    print(f"Reason: {reason}")
    print(f"Stats: {rm.get_daily_stats()}")
