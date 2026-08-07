"""
Single Instance Process Guard (v3.7.2)
=====================================
Guarantees ONLY ONE instance of main.py can run concurrently on VPS.
Prevents duplicate Telegram reports and duplicate order executions.
"""

import os
import sys
import fcntl
from loguru import logger

_lock_file = None

def ensure_single_instance(lock_file_path: str = "/tmp/kis_auto_trading.lock"):
    """Acquire exclusive file lock. If already locked, exit process immediately."""
    global _lock_file
    try:
        _lock_file = open(lock_file_path, 'w')
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        logger.info("🔒 [SINGLE_INSTANCE_GUARD] Lock acquired cleanly (PID: {})", os.getpid())
    except (IOError, OSError):
        logger.warning("⛔ [SINGLE_INSTANCE_GUARD] Another main.py instance is already running (Lock: {}). Terminating duplicate instance.", lock_file_path)
        sys.exit(0)
