"""
Emergency Stop System
=======================
Circuit breaker for extreme market conditions.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger
import json
import os


@dataclass
class EmergencyState:
    is_active: bool
    trigger_time: Optional[datetime]
    trigger_reason: str
    severity: str
    can_auto_recover: bool
    recovery_time: Optional[datetime]
    manual_restart_required: bool
    actions_taken: List[str]


class EmergencyStop:
    """Circuit breaker for flash crash, VIX spike, API errors"""
    
    def __init__(self, state_file: str = "emergency_state.json"):
        self.state_file = state_file
        self.is_active = False
        self.trigger_time: Optional[datetime] = None
        self.trigger_reason = ""
        self.severity = ""
        self.actions_taken: List[str] = []
        self.error_count = 0
        self._load_state()
    
    def check_flash_crash(self, current: float, reference: float) -> Optional[EmergencyState]:
        if reference <= 0:
            return None
        drop = (current / reference - 1)
        if drop < -0.05:
            return self._trigger("HALT", f"Flash crash: {drop:.1%}", True)
        elif drop < -0.03:
            return self._trigger("CRITICAL", f"Major drop: {drop:.1%}")
        return None
    
    def check_vix_spike(self, vix: float) -> Optional[EmergencyState]:
        if vix >= 50:
            return self._trigger("HALT", f"VIX: {vix:.0f}", True)
        elif vix >= 35:
            return self._trigger("CRITICAL", f"VIX elevated: {vix:.0f}")
        return None
    
    def check_portfolio_loss(self, loss_pct: float) -> Optional[EmergencyState]:
        if loss_pct < -0.05:
            return self._trigger("HALT", f"Portfolio crash: {loss_pct:.1%}", True)
        elif loss_pct < -0.03:
            return self._trigger("CRITICAL", f"Portfolio drop: {loss_pct:.1%}")
        return None
    
    def check_daily_loss(self, start_equity: float, current_equity: float) -> bool:
        """
        일일 손실 한도 서킷 브레이커
        실거래 데이터: 최악 트레이드 -$43, 최고 트레이드 +$11
        $700 계좌에서 3% = $21 이상 손실 시 당일 신규 진입 전면 차단
        """
        if start_equity <= 0:
            return False
        daily_loss_pct = (current_equity - start_equity) / start_equity
        MAX_DAILY_LOSS_PCT = -0.03  # -3% 하드 한도
        if daily_loss_pct < MAX_DAILY_LOSS_PCT:
            logger.warning(
                "🛑 DAILY_LOSS_CIRCUIT_BREAKER: 오늘 {:.1%} 손실 (한도: {:.1%}) — 신규 진입 전면 차단",
                daily_loss_pct, MAX_DAILY_LOSS_PCT
            )
            return True  # Block new entries
        return False
    
    def report_error(self, error_type: str) -> Optional[EmergencyState]:
        self.error_count += 1
        if self.error_count >= 5:
            return self._trigger("CRITICAL", f"Errors: {error_type} x{self.error_count}")
        return None
    
    def _trigger(self, severity: str, reason: str, manual: bool = False) -> EmergencyState:
        now = datetime.now()
        self.is_active = True
        self.trigger_time = now
        self.trigger_reason = reason
        self.severity = severity
        
        actions = ["REDUCE_EXPOSURE", "SEND_ALERT"]
        if severity == "HALT":
            actions = ["CLOSE_ALL", "DISABLE_ORDERS", "ALERT"]
        
        self.actions_taken = actions
        logger.warning(f"🚨 EMERGENCY {severity}: {reason}")
        self._save_state()
        
        return EmergencyState(True, now, reason, severity, severity != "HALT", 
                              now + timedelta(hours=24), manual, actions)
    
    def check_recovery(self) -> Optional[EmergencyState]:
        """Check if emergency is active, auto-recover if possible"""
        if not self.is_active:
            return None
        now = datetime.now()
        # Auto-recover after 24 hours for non-HALT severity
        if self.trigger_time and self.severity != "HALT":
            elapsed = (now - self.trigger_time).total_seconds() / 3600
            if elapsed > 24:
                logger.info("Emergency auto-recovered after {:.0f}h", elapsed)
                self.reset()
                return None
        return EmergencyState(
            is_active=True, trigger_time=self.trigger_time,
            trigger_reason=self.trigger_reason, severity=self.severity,
            can_auto_recover=self.severity != "HALT",
            recovery_time=None, manual_restart_required=self.severity == "HALT",
            actions_taken=self.actions_taken
        )

    def reset(self):
        self.is_active = False
        self.trigger_time = None
        self.trigger_reason = ""
        self.severity = ""
        self.actions_taken = []
        self.error_count = 0
        self._save_state()
    
    def _save_state(self):
        try:
            state = {'is_active': self.is_active, 'severity': self.severity,
                     'reason': self.trigger_reason}
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except: pass
    
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.is_active = state.get('is_active', False)
                self.severity = state.get('severity', '')
                self.trigger_reason = state.get('reason', '')
        except: pass


def get_emergency_stop() -> EmergencyStop:
    return EmergencyStop()


def check_circuit_breaker(trader, rm) -> bool:
    """Orchestrator compatibility: check if circuit breaker should activate"""
    es = get_emergency_stop()
    if es.is_active:
        return True
    try:
        positions = trader.get_positions()
        bp = trader.get_buying_power()
        total_value = bp + sum(p.market_value for p in positions)
        if total_value > 0 and hasattr(es, 'check_portfolio_loss'):
            # Estimate P&L from positions
            total_cost = sum(p.avg_price * p.quantity for p in positions)
            if total_cost > 0:
                loss_pct = (total_value - bp - total_cost) / total_cost
                result = es.check_portfolio_loss(loss_pct)
                return result is not None and result.is_active
    except Exception as e:
        logger.debug("Circuit breaker check error: {}", e)
    return False


if __name__ == "__main__":
    print("Testing EmergencyStop...")
    e = EmergencyStop()
    print(f"VIX 50: {e.check_vix_spike(50)}")
    e.reset()
    print(f"Flash -5%: {e.check_flash_crash(95, 100)}")
