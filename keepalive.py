"""
Keep-Alive Module - Oracle Cloud Free Tier Anti-Idle
=====================================================
Prevents Oracle Cloud from reclaiming idle instances.
Uses CPU-intensive tasks to maintain activity.
"""

import threading
import time
import random
from datetime import datetime
from loguru import logger
import numpy as np


class AntiIdleThread:
    """
    Background thread that keeps Oracle Cloud instance alive
    
    Oracle may reclaim "idle" instances on Free Tier.
    This thread performs periodic CPU work to maintain activity.
    
    Features:
    - Matrix multiplication (CPU intensive)
    - Random memory allocation
    - Periodic disk I/O
    - Heartbeat logging
    """
    
    PULSE_INTERVAL = 600  # 10 minutes
    MATRIX_SIZE = 500     # 500x500 matrix
    
    def __init__(self, interval: int = None):
        self.interval = interval or self.PULSE_INTERVAL
        self._running = False
        self._thread = None
        self._pulse_count = 0
        self._start_time = None
    
    def start(self):
        """Start the anti-idle thread"""
        if self._running:
            return
        
        self._running = True
        self._start_time = datetime.now()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("AntiIdle started (pulse every {}s)", self.interval)
    
    def stop(self):
        """Stop the anti-idle thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("AntiIdle stopped after {} pulses", self._pulse_count)
    
    def _run_loop(self):
        """Main loop"""
        while self._running:
            try:
                self._pulse()
            except Exception as e:
                logger.warning("AntiIdle pulse error: {}", e)
            
            time.sleep(self.interval)
    
    def _pulse(self):
        """Perform keepalive activities"""
        self._pulse_count += 1
        start = time.time()
        
        # 1. CPU: Matrix multiplication
        a = np.random.rand(self.MATRIX_SIZE, self.MATRIX_SIZE)
        b = np.random.rand(self.MATRIX_SIZE, self.MATRIX_SIZE)
        _ = np.dot(a, b)
        
        # 2. Memory: Random allocation
        _ = [random.random() for _ in range(10000)]
        
        # 3. Disk: Write heartbeat
        try:
            with open(".heartbeat", "w") as f:
                f.write(f"{datetime.now().isoformat()}\n")
                f.write(f"Pulses: {self._pulse_count}\n")
        except Exception as err:
            logger.warning("⚠️ [keepalive.py] Fallback triggered: {}", err)
        
        elapsed = time.time() - start
        
        uptime = datetime.now() - self._start_time
        uptime_str = str(uptime).split('.')[0]
        
        logger.debug("💓 Pulse #{} | {:.1f}ms | Uptime: {}", 
                    self._pulse_count, elapsed * 1000, uptime_str)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def pulse_count(self) -> int:
        return self._pulse_count
    
    def get_status(self) -> dict:
        """Get current status"""
        uptime = None
        if self._start_time:
            uptime = str(datetime.now() - self._start_time).split('.')[0]
        
        return {
            "running": self._running,
            "pulses": self._pulse_count,
            "uptime": uptime,
            "interval": self.interval
        }


# Global instance
_keepalive = None

def start_keepalive(interval: int = None):
    """Start global keepalive thread"""
    global _keepalive
    if _keepalive is None:
        _keepalive = AntiIdleThread(interval)
    _keepalive.start()

def stop_keepalive():
    """Stop global keepalive thread"""
    global _keepalive
    if _keepalive:
        _keepalive.stop()
        _keepalive = None

def get_keepalive_status() -> dict:
    """Get keepalive status"""
    if _keepalive:
        return _keepalive.get_status()
    return {"running": False}


if __name__ == "__main__":
    import sys
    import argparse
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run quick test")
    args = parser.parse_args()
    
    print("=" * 50)
    print("Testing AntiIdleThread")
    print("=" * 50)
    
    thread = AntiIdleThread(interval=5)  # 5s for testing
    thread.start()
    
    if args.test:
        # Quick test
        time.sleep(30)
    else:
        try:
            print("\nRunning (Ctrl+C to stop)...")
            while True:
                time.sleep(10)
                print(f"Status: {thread.get_status()}")
        except Exception as err:
            logger.warning("⚠️ [keepalive.py] Fallback triggered: {}", err)
    
    thread.stop()
    print(f"\nTotal pulses: {thread.pulse_count}")
