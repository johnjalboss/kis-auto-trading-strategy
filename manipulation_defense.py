"""
Manipulation Defense System
==============================
Detect and defend against institutional manipulation.

Tactics defended:
1. Stop Hunting - Sudden spike to trigger stops
2. Fake Breakouts - False breakout then reversal
3. Volume Spikes - Artificial volume to fake momentum
4. VWAP Games - Manipulation around VWAP
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class ManipulationAlert:
    alert_type: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    description: str
    recommended_action: str


@dataclass
class SmartStopLevel:
    raw_stop: float
    smart_stop: float
    buffer_pct: float
    reason: str


class ManipulationDefense:
    """
    Defense Against Institutional Manipulation
    
    Key Defenses:
    1. Smart Stop Placement - Avoid obvious levels
    2. Stop Hunt Detection - Recognize the pattern
    3. Fake Breakout Filter - Wait for confirmation
    4. Volume Spike Analysis - Distinguish real vs fake
    5. Time-Based Entry - Avoid manipulation windows
    """
    
    # Common manipulation times (market open, close, options expiry)
    DANGEROUS_TIMES = [
        (9, 30, 10, 0),   # First 30 min
        (15, 30, 16, 0),  # Last 30 min
    ]
    
    def __init__(self):
        pass
    
    # ===== SMART STOP PLACEMENT =====
    
    def get_smart_stop(self, 
                       entry_price: float,
                       raw_stop: float,
                       atr: float,
                       recent_lows: List[float]) -> SmartStopLevel:
        """
        Calculate smart stop that avoids obvious levels
        
        Problems with normal stops:
        - Round numbers (100, 150, 200)
        - Just below recent lows
        - Exact ATR multiples
        
        Solution: Add buffer and randomization
        """
        
        # Find if raw stop is near obvious level
        round_levels = [int(entry_price / 10) * 10 - 10,
                        int(entry_price / 5) * 5 - 5]
        
        # Check if stop is near recent lows (where everyone else has stops)
        near_low = any(abs(raw_stop - low) / low < 0.01 for low in recent_lows)
        
        # Check if stop is at round number
        near_round = any(abs(raw_stop - lvl) / lvl < 0.005 for lvl in round_levels)
        
        # Add buffer
        if near_low or near_round:
            # Place stop 0.5-1% below the obvious level
            buffer = atr * 0.3 * (1 + np.random.random() * 0.5)
            smart = raw_stop - buffer
            reason = "Moved below obvious level"
            buffer_pct = buffer / entry_price * 100
        else:
            smart = raw_stop
            reason = "No obvious level nearby"
            buffer_pct = 0
        
        return SmartStopLevel(
            raw_stop=raw_stop,
            smart_stop=smart,
            buffer_pct=buffer_pct,
            reason=reason
        )
    
    # ===== STOP HUNT DETECTION =====
    
    def detect_stop_hunt(self, df: pd.DataFrame) -> Optional[ManipulationAlert]:
        """
        Detect stop hunting pattern:
        - Quick spike down (or up for shorts)
        - Hit stops
        - Immediate reversal
        """
        
        if len(df) < 10:
            return None
        
        # Get recent price action
        close = df['Close']
        low = df['Low']
        high = df['High']
        
        # Check for wick patterns (long lower wick = stop hunt)
        recent = df.tail(5)
        
        for i in range(len(recent)):
            row = recent.iloc[i]
            body = abs(row['Close'] - row['Open'])
            lower_wick = min(row['Open'], row['Close']) - row['Low']
            upper_wick = row['High'] - max(row['Open'], row['Close'])
            
            # Long lower wick = potential stop hunt down
            if lower_wick > body * 3 and body > 0:
                recovery_pct = (row['Close'] - row['Low']) / row['Low'] * 100
                
                if recovery_pct > 2.5:
                    return ManipulationAlert(
                        alert_type="STOP_HUNT_DOWN",
                        severity="HIGH",
                        description=f"Stop hunt detected: {recovery_pct:.1f}% wick recovery",
                        recommended_action="Wait 15 min before entry, may be buying opportunity"
                    )
            
            # Long upper wick = potential stop hunt up (for shorts)
            if upper_wick > body * 3 and body > 0:
                reversal_pct = (row['High'] - row['Close']) / row['High'] * 100
                
                if reversal_pct > 2.5:
                    return ManipulationAlert(
                        alert_type="STOP_HUNT_UP",
                        severity="HIGH",
                        description=f"Stop hunt up: {reversal_pct:.1f}% rejection",
                        recommended_action="Avoid new longs, potential reversal"
                    )
        
        return None
    
    # ===== FAKE BREAKOUT DETECTION =====
    
    def detect_fake_breakout(self, 
                             df: pd.DataFrame,
                             breakout_level: float) -> Optional[ManipulationAlert]:
        """
        Detect fake breakout pattern:
        - Break above resistance
        - Low volume on breakout
        - Quick reversal back below
        """
        
        if len(df) < 5:
            return None
        
        close = df['Close']
        volume = df['Volume']
        
        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        avg_volume = float(volume.rolling(20).mean().iloc[-1])
        current_volume = float(volume.iloc[-1])
        
        # Check for failed breakout
        if prev > breakout_level and current < breakout_level:
            # Breakout failed
            if current_volume < avg_volume * 0.7:
                return ManipulationAlert(
                    alert_type="FAKE_BREAKOUT",
                    severity="HIGH",
                    description="Breakout failed on low volume - likely trap",
                    recommended_action="Exit longs, potential short opportunity"
                )
            else:
                return ManipulationAlert(
                    alert_type="BREAKOUT_FAILURE",
                    severity="MEDIUM",
                    description="Breakout reversal on normal volume",
                    recommended_action="Tighten stops, watch for continuation"
                )
        
        return None
    
    # ===== VOLUME SPIKE ANALYSIS =====
    
    def analyze_volume_spike(self, df: pd.DataFrame) -> Optional[ManipulationAlert]:
        """
        Distinguish real vs fake volume spikes
        
        Real: Sustained volume, price follows
        Fake: One-candle spike, immediate reversal
        """
        
        volume = df['Volume']
        close = df['Close']
        
        avg_vol = float(volume.rolling(20).mean().iloc[-5])
        
        # Check for isolated volume spike
        for i in range(-3, 0):
            if float(volume.iloc[i]) > avg_vol * 3:
                # High volume candle
                price_change = (float(close.iloc[i]) - float(close.iloc[i-1])) / float(close.iloc[i-1]) * 100
                next_change = (float(close.iloc[-1]) - float(close.iloc[i])) / float(close.iloc[i]) * 100
                
                # Did it reverse?
                if (price_change > 0 and next_change < -price_change * 0.5) or \
                   (price_change < 0 and next_change > -price_change * 0.5):
                    return ManipulationAlert(
                        alert_type="FAKE_VOLUME",
                        severity="MEDIUM",
                        description="Volume spike followed by reversal - potential trap",
                        recommended_action="Ignore this signal, wait for confirmation"
                    )
        
        return None
    
    # ===== SAFE ENTRY TIMES =====
    
    def is_safe_time(self) -> Tuple[bool, str]:
        """Check if current time is safe for entry"""
        
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Check dangerous times
        for start_h, start_m, end_h, end_m in self.DANGEROUS_TIMES:
            start = start_h * 60 + start_m
            end = end_h * 60 + end_m
            current = hour * 60 + minute
            
            if start <= current <= end:
                return False, f"Dangerous time window ({start_h}:{start_m:02d}-{end_h}:{end_m:02d})"
        
        # Check options expiry (Friday)
        if now.weekday() == 4 and hour >= 14:
            return False, "Options expiry manipulation risk"
        
        return True, "Safe trading window"
    
    # ===== FULL SCAN =====
    
    def full_scan(self, symbol: str) -> List[ManipulationAlert]:
        """Run all manipulation checks"""
        
        alerts = []
        
        try:
            df = yf.download(symbol, period='5d', interval='15m', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                return alerts
            
            # Stop hunt
            sh = self.detect_stop_hunt(df)
            if sh:
                alerts.append(sh)
            
            # Volume analysis
            vs = self.analyze_volume_spike(df)
            if vs:
                alerts.append(vs)
            
            # Time check
            safe, reason = self.is_safe_time()
            if not safe:
                alerts.append(ManipulationAlert(
                    alert_type="DANGEROUS_TIME",
                    severity="MEDIUM",
                    description=reason,
                    recommended_action="Wait for safer entry window"
                ))
            
        except Exception as e:
            logger.debug(f"Manipulation scan error: {e}")
        
        return alerts


def get_manipulation_defense() -> ManipulationDefense:
    return ManipulationDefense()


if __name__ == "__main__":
    print("Testing ManipulationDefense...")
    md = ManipulationDefense()
    
    # Test smart stop
    stop = md.get_smart_stop(
        entry_price=150.0,
        raw_stop=145.0,
        atr=3.0,
        recent_lows=[145.5, 145.2, 146.0]
    )
    print(f"\nSmart Stop:")
    print(f"  Raw: ${stop.raw_stop:.2f}")
    print(f"  Smart: ${stop.smart_stop:.2f}")
    print(f"  Buffer: {stop.buffer_pct:.2f}%")
    print(f"  Reason: {stop.reason}")
    
    # Test time check
    safe, reason = md.is_safe_time()
    print(f"\nTime Check: {'Safe' if safe else 'Dangerous'} - {reason}")
    
    # Full scan
    alerts = md.full_scan("AAPL")
    print(f"\nManipulation Alerts: {len(alerts)}")
    for a in alerts:
        print(f"  [{a.severity}] {a.alert_type}: {a.description}")
        print(f"    → {a.recommended_action}")
