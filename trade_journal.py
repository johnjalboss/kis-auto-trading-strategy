"""
Trade Journal & Logging
=========================
Log all trades for analysis and review.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
from loguru import logger
import json
import os
import sqlite3


@dataclass
class TradeLog:
    id: str
    timestamp: str
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    price: float
    total_value: float
    strategy: str
    regime: str
    composite_score: int
    stop_loss: float
    take_profit: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    closed_at: Optional[str]
    notes: str


class TradeJournal:
    """SQLite-based trade journal for persistence"""
    
    def __init__(self, db_path: str = "trade_journal.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id TEXT PRIMARY KEY, timestamp TEXT, symbol TEXT,
                      action TEXT, quantity INTEGER, price REAL,
                      total_value REAL, strategy TEXT, regime TEXT,
                      composite_score INTEGER, stop_loss REAL, take_profit REAL,
                      pnl REAL, pnl_pct REAL, closed_at TEXT, notes TEXT)''')
        conn.commit()
        conn.close()
    
    def log_trade(self, trade: TradeLog):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO trades VALUES
                     (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                  (trade.id, trade.timestamp, trade.symbol, trade.action,
                   trade.quantity, trade.price, trade.total_value,
                   trade.strategy, trade.regime, trade.composite_score,
                   trade.stop_loss, trade.take_profit, trade.pnl,
                   trade.pnl_pct, trade.closed_at, trade.notes))
        conn.commit()
        conn.close()
        logger.info(f"📝 Trade logged: {trade.action} {trade.symbol}")
    
    def close_trade(self, trade_id: str, close_price: float, notes: str = ""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM trades WHERE id=?", (trade_id,))
        row = c.fetchone()
        if row:
            entry_price = row[5]
            action = row[3]
            total_value = row[6]
            if action == "BUY":
                pnl_pct = (close_price / entry_price - 1) * 100
            else:
                pnl_pct = (entry_price / close_price - 1) * 100
            pnl = total_value * (pnl_pct / 100)
            
            c.execute('''UPDATE trades SET pnl=?, pnl_pct=?, closed_at=?, notes=?
                        WHERE id=?''',
                      (pnl, pnl_pct, datetime.now().isoformat(), notes, trade_id))
            conn.commit()
            logger.info(f"✅ Trade closed: {trade_id} P/L: {pnl_pct:+.2f}%")
        conn.close()
    
    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT pnl, pnl_pct FROM trades WHERE pnl IS NOT NULL")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return {"total_trades": 0, "win_rate": 0, "total_pnl": 0}
        
        pnls = [r[0] for r in rows]
        pnl_pcts = [r[1] for r in rows]
        wins = sum(1 for p in pnls if p > 0)
        
        return {
            "total_trades": len(rows),
            "wins": wins,
            "losses": len(rows) - wins,
            "win_rate": wins / len(rows) * 100,
            "total_pnl": sum(pnls),
            "avg_pnl_pct": sum(pnl_pcts) / len(pnl_pcts),
            "best_trade": max(pnl_pcts),
            "worst_trade": min(pnl_pcts)
        }
    
    def get_recent(self, n: int = 10, limit: Optional[int] = None) -> List[dict]:
        if limit is not None:
            n = limit
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (n,))
        rows = c.fetchall()
        conn.close()
        return rows


def get_trade_journal() -> TradeJournal:
    return TradeJournal()


if __name__ == "__main__":
    print("Testing TradeJournal...")
    j = TradeJournal("test_journal.db")
    
    trade = TradeLog(
        id="T001", timestamp=datetime.now().isoformat(),
        symbol="AAPL", action="BUY", quantity=10, price=150.0,
        total_value=1500.0, strategy="MOMENTUM", regime="BULL",
        composite_score=65, stop_loss=145.0, take_profit=165.0,
        pnl=None, pnl_pct=None, closed_at=None, notes=""
    )
    j.log_trade(trade)
    j.close_trade("T001", 160.0)
    print(f"Stats: {j.get_stats()}")
