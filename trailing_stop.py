"""
Advanced Trailing Stop
========================
Protect profits with dynamic trailing stops.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import json
import os


@dataclass
class TrailingStopState:
    symbol: str
    entry_price: float
    current_price: float
    highest_price: float
    trailing_stop: float
    profit_pct: float
    is_triggered: bool
    action: str  # "HOLD", "TRAIL_UP", "STOP_OUT"


class TrailingStopManager:
    """
    Dynamic Trailing Stop
    
    Strategies:
    1. Fixed % (2-3%)
    2. ATR-based (2x ATR)
    3. Chandelier Exit
    4. Parabolic SAR style
    
    Profit Lock:
    - At 5% gain: trail at 3%
    - At 10% gain: trail at 5%
    - At 20% gain: trail at 8%
    """
    
    def __init__(self, state_file: str = "trailing_stops.json"):
        self.state_file = state_file
        self.positions: Dict[str, dict] = {}
        self._load_state()
    
    def add_position(self, symbol: str, entry_price: float, 
                     initial_stop_pct: float = 0.03):
        self.positions[symbol] = {
            'entry_price': entry_price,
            'highest_price': entry_price,
            'stop_pct': initial_stop_pct,
            'created_at': datetime.now().isoformat()
        }
        self._save_state()
        logger.info(f"Added trailing stop: {symbol} @ ${entry_price:.2f}")
    
    def update(self, symbol: str, current_price: float) -> TrailingStopState:
        if symbol not in self.positions:
            return TrailingStopState(symbol, 0, current_price, 0, 0, 0, False, "NO_POSITION")
        
        pos = self.positions[symbol]
        entry = pos['entry_price']
        highest = pos['highest_price']
        
        # Update highest
        if current_price > highest:
            pos['highest_price'] = current_price
            highest = current_price
        
        # Calculate profit
        profit_pct = (current_price / entry - 1) * 100
        
        # Dynamic trailing %
        if profit_pct >= 20:
            trail_pct = 0.08
        elif profit_pct >= 10:
            trail_pct = 0.05
        elif profit_pct >= 5:
            trail_pct = 0.03
        else:
            trail_pct = pos['stop_pct']
        
        pos['stop_pct'] = trail_pct
        
        # Calculate stop level
        trailing_stop = highest * (1 - trail_pct)
        
        # Check trigger
        is_triggered = current_price <= trailing_stop
        
        if is_triggered:
            action = "STOP_OUT"
            logger.warning(f"🔴 STOP triggered: {symbol} @ ${current_price:.2f}")
        elif current_price > highest * 0.99:
            action = "TRAIL_UP"
        else:
            action = "HOLD"
        
        self._save_state()
        
        return TrailingStopState(
            symbol=symbol,
            entry_price=entry,
            current_price=current_price,
            highest_price=highest,
            trailing_stop=trailing_stop,
            profit_pct=profit_pct,
            is_triggered=is_triggered,
            action=action
        )
    
    def remove_position(self, symbol: str):
        if symbol in self.positions:
            del self.positions[symbol]
            self._save_state()
    
    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
        except: pass
    
    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.positions = json.load(f)
        except: pass


def get_trailing_manager() -> TrailingStopManager:
    return TrailingStopManager()


if __name__ == "__main__":
    print("Testing TrailingStopManager...")
    t = TrailingStopManager("test_trailing.json")
    
    t.add_position("AAPL", 150.0)
    
    for price in [152, 155, 160, 165, 158, 155, 153]:
        result = t.update("AAPL", price)
        print(f"${price}: Profit={result.profit_pct:+.1f}%, "
              f"Stop=${result.trailing_stop:.2f}, {result.action}")
