"""
Health Monitor
================
System health and performance monitoring.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List
from loguru import logger
import json
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class HealthStatus:
    is_healthy: bool
    uptime_hours: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    api_status: str
    data_age_seconds: int
    last_trade_hours: float
    errors_24h: int
    warnings: List[str]


class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self, state_file: str = "health_state.json"):
        self.state_file = state_file
        self.start_time = datetime.now()
        self.last_trade_time = None
        self.last_data_update = datetime.now()
        self.errors: List[datetime] = []
        self.api_status = "UNKNOWN"
    
    def check_health(self) -> HealthStatus:
        warnings = []
        
        # System resources (with fallback if psutil not available)
        if HAS_PSUTIL:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        else:
            cpu, mem, disk = 0, 0, 0
        
        if cpu > 80:
            warnings.append(f"High CPU: {cpu}%")
        if mem > 85:
            warnings.append(f"High Memory: {mem}%")
        if disk > 90:
            warnings.append(f"Low Disk: {disk}%")
        
        # Uptime
        uptime = (datetime.now() - self.start_time).total_seconds() / 3600
        
        # Data freshness
        data_age = (datetime.now() - self.last_data_update).total_seconds()
        if data_age > 300:
            warnings.append(f"Stale data: {data_age:.0f}s")
        
        # Last trade
        last_trade = 0
        if self.last_trade_time:
            last_trade = (datetime.now() - self.last_trade_time).total_seconds() / 3600
        
        # Errors in last 24h
        cutoff = datetime.now() - timedelta(hours=24)
        errors_24h = sum(1 for e in self.errors if e > cutoff)
        if errors_24h > 10:
            warnings.append(f"Many errors: {errors_24h}")
        
        is_healthy = len(warnings) == 0 and self.api_status == "OK"
        
        return HealthStatus(
            is_healthy=is_healthy,
            uptime_hours=uptime,
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            api_status=self.api_status,
            data_age_seconds=int(data_age),
            last_trade_hours=last_trade,
            errors_24h=errors_24h,
            warnings=warnings
        )
    
    def record_error(self, error: str):
        self.errors.append(datetime.now())
        logger.error(f"Error recorded: {error}")
        self.errors = self.errors[-100:]  # Keep last 100
    
    def update_data_time(self):
        self.last_data_update = datetime.now()
    
    def update_trade_time(self):
        self.last_trade_time = datetime.now()
    
    def set_api_status(self, status: str):
        self.api_status = status


_monitor = None
def get_health_monitor() -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


if __name__ == "__main__":
    print("Testing HealthMonitor...")
    h = HealthMonitor()
    h.set_api_status("OK")
    status = h.check_health()
    print(f"Healthy: {status.is_healthy}")
    print(f"CPU: {status.cpu_percent}%")
    print(f"Memory: {status.memory_percent}%")
    print(f"Uptime: {status.uptime_hours:.2f}h")
    print(f"Warnings: {status.warnings}")
