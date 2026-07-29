"""
Real-Time News & Price Alert System
=====================================
Detect breaking news and sudden price moves instantly.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
import threading
import time
import yfinance as yf
from loguru import logger


@dataclass
class PriceAlert:
    symbol: str
    alert_type: str  # "SPIKE_UP", "SPIKE_DOWN", "VOLUME_SURGE"
    change_pct: float
    time_detected: datetime
    action_required: str  # "CHECK_NEWS", "CONSIDER_EXIT", "OPPORTUNITY"


@dataclass
class NewsAlert:
    symbol: str
    headline: str
    sentiment: str
    urgency: str  # "BREAKING", "HIGH", "NORMAL"
    action: str  # "EXIT_NOW", "REDUCE", "MONITOR", "BUY_OPPORTUNITY"


class RealTimeMonitor:
    """
    Real-Time Monitoring System
    
    Monitors:
    1. Price spikes (±2% in 5 min)
    2. Volume surges (3x average)
    3. Breaking news keywords
    
    Check interval: 1 minute for positions, 5 min for watchlist
    """
    
    # Breaking news keywords
    BREAKING_NEGATIVE = [
        'crash', 'plunge', 'halt', 'suspended', 'fraud', 'sec investigation',
        'fda reject', 'recall', 'lawsuit', 'bankrupt', 'ceo resign', 'data breach',
        'downgrade', 'guidance cut', 'miss earnings', 'layoff', 'default'
    ]
    
    BREAKING_POSITIVE = [
        'fda approve', 'upgrade', 'beat earnings', 'raised guidance', 
        'acquisition', 'buyback', 'dividend hike', 'contract win', 'breakthrough'
    ]
    
    def __init__(self, 
                 on_price_alert: Optional[Callable] = None,
                 on_news_alert: Optional[Callable] = None):
        self.positions: Dict[str, float] = {}  # symbol: entry_price
        self.watchlist: List[str] = []
        self.last_prices: Dict[str, float] = {}
        self.last_check: Dict[str, datetime] = {}
        
        self.on_price_alert = on_price_alert or self._default_alert
        self.on_news_alert = on_news_alert or self._default_alert
        
        self.running = False
        self._thread = None
    
    def add_position(self, symbol: str, entry_price: float):
        """Add position to monitor (1-min checks)"""
        self.positions[symbol] = entry_price
        logger.info(f"Monitoring position: {symbol}")
    
    def remove_position(self, symbol: str):
        """Remove position"""
        if symbol in self.positions:
            del self.positions[symbol]
    
    def set_watchlist(self, symbols: List[str]):
        """Set watchlist (5-min checks)"""
        self.watchlist = symbols
    
    def check_now(self, symbol: str) -> List:
        """Immediate check for a symbol"""
        alerts = []
        
        try:
            ticker = yf.Ticker(symbol)
            
            # Get intraday data
            data = ticker.history(period='1d', interval='1m')
            if data.empty or len(data) < 5:
                return alerts
            
            current = float(data['Close'].iloc[-1])
            price_5min_ago = float(data['Close'].iloc[-5]) if len(data) >= 5 else current
            
            # Price spike detection
            change_5min = (current / price_5min_ago - 1) * 100
            
            if change_5min >= 2.0:
                alerts.append(PriceAlert(
                    symbol=symbol,
                    alert_type="SPIKE_UP",
                    change_pct=change_5min,
                    time_detected=datetime.now(),
                    action_required="OPPORTUNITY" if symbol not in self.positions else "CONSIDER_EXIT_PARTIAL"
                ))
            elif change_5min <= -2.0:
                alerts.append(PriceAlert(
                    symbol=symbol,
                    alert_type="SPIKE_DOWN",
                    change_pct=change_5min,
                    time_detected=datetime.now(),
                    action_required="EXIT_NOW" if symbol in self.positions else "CHECK_NEWS"
                ))
            
            # Volume surge
            vol_avg = data['Volume'].mean()
            vol_current = float(data['Volume'].iloc[-1])
            
            if vol_current > vol_avg * 3:
                alerts.append(PriceAlert(
                    symbol=symbol,
                    alert_type="VOLUME_SURGE",
                    change_pct=vol_current / vol_avg,
                    time_detected=datetime.now(),
                    action_required="CHECK_NEWS"
                ))
            
            # News check
            news = ticker.news
            if news:
                for item in news[:3]:
                    title = item.get('title', '').lower()
                    pub_time = item.get('providerPublishTime', 0)
                    
                    # Check if recent (within 30 min)
                    if datetime.now().timestamp() - pub_time < 1800:
                        # Check for breaking keywords
                        for keyword in self.BREAKING_NEGATIVE:
                            if keyword in title:
                                alerts.append(NewsAlert(
                                    symbol=symbol,
                                    headline=item.get('title', ''),
                                    sentiment="NEGATIVE",
                                    urgency="BREAKING",
                                    action="EXIT_NOW" if symbol in self.positions else "AVOID"
                                ))
                                break
                        
                        for keyword in self.BREAKING_POSITIVE:
                            if keyword in title:
                                alerts.append(NewsAlert(
                                    symbol=symbol,
                                    headline=item.get('title', ''),
                                    sentiment="POSITIVE",
                                    urgency="BREAKING",
                                    action="HOLD" if symbol in self.positions else "BUY_OPPORTUNITY"
                                ))
                                break
            
            self.last_prices[symbol] = current
            self.last_check[symbol] = datetime.now()
            
        except Exception as e:
            logger.debug(f"Check failed for {symbol}: {e}")
        
        return alerts
    
    def start_monitoring(self):
        """Start background monitoring"""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Real-time monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Real-time monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Check positions every minute
                for symbol in list(self.positions.keys()):
                    alerts = self.check_now(symbol)
                    for alert in alerts:
                        self._handle_alert(alert)
                
                time.sleep(60)  # 1 minute
                
                # Check watchlist every 5 minutes
                if datetime.now().minute % 5 == 0:
                    for symbol in self.watchlist:
                        if symbol not in self.positions:
                            alerts = self.check_now(symbol)
                            for alert in alerts:
                                self._handle_alert(alert)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(30)
    
    def _handle_alert(self, alert):
        """Handle alerts"""
        if isinstance(alert, PriceAlert):
            logger.warning(f"🚨 PRICE ALERT: {alert.symbol} {alert.alert_type} {alert.change_pct:+.1f}%")
            self.on_price_alert(alert)
        elif isinstance(alert, NewsAlert):
            logger.warning(f"📰 NEWS ALERT: {alert.symbol} {alert.urgency} - {alert.headline[:50]}")
            self.on_news_alert(alert)
    
    def _default_alert(self, alert):
        """Default alert handler"""
        pass


def get_realtime_monitor() -> RealTimeMonitor:
    return RealTimeMonitor()


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing RealTimeMonitor...")
    
    monitor = RealTimeMonitor()
    
    # Add test position
    monitor.add_position("AAPL", 150.0)
    
    # Immediate check
    alerts = monitor.check_now("AAPL")
    print(f"AAPL Alerts: {len(alerts)}")
    for a in alerts:
        print(f"  {a}")
    
    # Check volatile stock
    alerts = monitor.check_now("NVDA")
    print(f"\nNVDA Alerts: {len(alerts)}")
    for a in alerts:
        print(f"  {a}")
