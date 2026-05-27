"""
Pre-market Analysis Module
===========================
Monitors pre-market activity for gap-up stocks and volume surges.
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional
import kis_data as yf  # KIS API drop-in replacement
import kis_data
import pandas as pd
from loguru import logger

from notifier import get_notifier
import config


@dataclass
class PremarketStock:
    """Pre-market stock data"""
    symbol: str
    prev_close: float
    premarket_price: float
    gap_pct: float
    premarket_volume: int
    avg_volume: int
    volume_ratio: float
    
    @property
    def is_significant(self) -> bool:
        """Check if gap/volume is significant"""
        return abs(self.gap_pct) >= 0.03 and self.volume_ratio >= 2.0


class PremarketAnalyzer:
    """
    Pre-market gap and volume analysis (KIS API)
    
    Monitors:
    - Gap Up/Down > 3%
    - Pre-market volume surge (> 2x average)
    - Earnings surprises
    """
    
    # Thresholds
    MIN_GAP_PCT = 0.03  # 3% gap
    MIN_VOLUME_RATIO = 2.0  # 2x average volume
    
    def __init__(self, watchlist: List[str] = None):
        self.watchlist = watchlist or [
            "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD",
            "GOOGL", "AMZN", "META", "PLTR", "COIN", "SOFI"
        ]
        self._cache = {}
        self.notifier = get_notifier()
    
    def analyze_stock(self, symbol: str) -> Optional[PremarketStock]:
        """Analyze single stock for pre-market activity using KIS API"""
        try:
            # KIS API 현재가 조회
            price_data = kis_data.get_current_price(symbol)
            
            if not price_data:
                return None
            
            prev_close = price_data.get('base', 0)  # 전일종가
            # 시간외 현재가가 있으면 사용, 없으면 현재가
            premarket = price_data.get('t_xprc', 0)
            if premarket == 0:
                premarket = price_data.get('last', 0)
            
            current_vol = price_data.get('tvol', 0)
            avg_volume = price_data.get('pvol', 1)  # 전일거래량
            
            if prev_close == 0:
                return None
            
            gap_pct = (premarket - prev_close) / prev_close
            volume_ratio = current_vol / max(avg_volume / 10, 1)  # PM vol is fraction of day
            
            return PremarketStock(
                symbol=symbol,
                prev_close=prev_close,
                premarket_price=premarket,
                gap_pct=gap_pct,
                premarket_volume=current_vol,
                avg_volume=avg_volume,
                volume_ratio=volume_ratio
            )
            
        except Exception as e:
            logger.debug("Could not analyze {}: {}", symbol, e)
            return None
    
    def scan_watchlist(self) -> List[PremarketStock]:
        """Scan watchlist for significant pre-market moves"""
        logger.info("Scanning {} stocks for pre-market activity...", len(self.watchlist))
        
        results = []
        
        for symbol in self.watchlist:
            data = self.analyze_stock(symbol)
            if data and data.is_significant:
                results.append(data)
                logger.info("{}: Gap {:+.1%}, Vol {:.1f}x", 
                           symbol, data.gap_pct, data.volume_ratio)
        
        # Sort by gap size
        results.sort(key=lambda x: abs(x.gap_pct), reverse=True)
        
        return results
    
    def scan_and_alert(self) -> List[PremarketStock]:
        """Scan and send Telegram alerts for significant moves"""
        results = self.scan_watchlist()
        
        for stock in results[:5]:  # Top 5 only
            self.notifier.premarket_alert(
                stock.symbol,
                stock.gap_pct,
                stock.volume_ratio
            )
        
        return results
    
    def get_gap_up_candidates(self, min_gap: float = 0.03) -> List[str]:
        """Get symbols with significant gap up"""
        results = self.scan_watchlist()
        return [s.symbol for s in results if s.gap_pct >= min_gap]
    
    def get_gap_down_candidates(self, min_gap: float = 0.03) -> List[str]:
        """Get symbols with significant gap down"""
        results = self.scan_watchlist()
        return [s.symbol for s in results if s.gap_pct <= -min_gap]
    
    @staticmethod
    def is_premarket_hours() -> bool:
        """Check if currently in pre-market hours (4:00-9:30 ET)"""
        import pytz
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et).time()
        
        premarket_start = time(4, 0)
        premarket_end = time(9, 30)
        
        return premarket_start <= now < premarket_end


# Global instance
_premarket = None

def get_premarket_analyzer() -> PremarketAnalyzer:
    global _premarket
    if _premarket is None:
        _premarket = PremarketAnalyzer()
    return _premarket


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing PremarketAnalyzer...")
    print(f"Is Pre-market: {PremarketAnalyzer.is_premarket_hours()}")
    
    analyzer = PremarketAnalyzer()
    
    # Test single stock
    print("\nAnalyzing AAPL...")
    result = analyzer.analyze_stock("AAPL")
    if result:
        print(f"  Gap: {result.gap_pct:+.2%}")
        print(f"  PM Volume: {result.premarket_volume:,}")
        print(f"  Volume Ratio: {result.volume_ratio:.1f}x")
    
    # Scan watchlist
    print("\nScanning watchlist...")
    results = analyzer.scan_watchlist()
    print(f"Found {len(results)} significant moves")
