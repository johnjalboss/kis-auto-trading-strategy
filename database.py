"""
Database Module - SQLite Trade History
=======================================
Persistent storage for trades, daily stats, and performance metrics.
Optimized for Oracle Cloud Free Tier (minimal disk usage).
"""

import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from contextlib import contextmanager
from loguru import logger


@dataclass
class TradeRecord:
    """Trade record for database"""
    id: Optional[int] = None
    symbol: str = ""
    side: str = ""  # BUY/SELL
    quantity: int = 0
    price: float = 0.0
    total: float = 0.0
    entry_time: datetime = None
    exit_time: datetime = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""
    regime: str = ""


@dataclass
class DailyRecord:
    """Daily performance record"""
    date: date
    starting_balance: float
    ending_balance: float
    trades_count: int
    wins: int
    losses: int
    gross_pnl: float
    net_pnl: float
    max_drawdown: float
    regime: str


class TradeDatabase:
    """
    SQLite database for trade history
    
    Tables:
    - trades: Individual trade records
    - daily_stats: Daily performance summary
    - positions: Current open positions
    """
    
    DB_FILE = "trades.db"
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_FILE
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        """Get database connection with auto-commit"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables"""
        with self._get_conn() as conn:
            # Enable WAL mode for high concurrency
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception as wal_err:
                logger.warning("Failed to set WAL mode: {}", wal_err)
                
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    total REAL NOT NULL,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    pnl REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    reason TEXT,
                    regime TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date DATE PRIMARY KEY,
                    starting_balance REAL,
                    ending_balance REAL,
                    trades_count INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    gross_pnl REAL DEFAULT 0,
                    net_pnl REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    regime TEXT
                );
                
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity INTEGER,
                    avg_price REAL,
                    entry_time TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS sent_reports (
                    report_type TEXT NOT NULL,
                    report_date DATE NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (report_type, report_date)
                );
                
                CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(entry_time);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
            """)
        logger.debug("Database initialized: {}", self.db_path)
    
    # ==============================================
    # Trade Records
    # ==============================================
    
    def record_entry(self, symbol: str, quantity: int, price: float,
                    regime: str = "") -> int:
        """Record trade entry"""
        total = quantity * price
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (symbol, side, quantity, price, total, entry_time, regime)
                VALUES (?, 'BUY', ?, ?, ?, ?, ?)
            """, (symbol, quantity, price, total, datetime.now(), regime))
            trade_id = cursor.lastrowid
            
            # Update positions
            conn.execute("""
                INSERT OR REPLACE INTO positions (symbol, quantity, avg_price, entry_time, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (symbol, quantity, price, datetime.now(), datetime.now()))
            
        logger.debug("Recorded entry: {} x {} @ ${:.2f}", symbol, quantity, price)
        return trade_id

    def update_position(self, symbol: str, quantity: int, avg_price: float):
        """Update or remove a position manually (for synchronization)"""
        with self._get_conn() as conn:
            if quantity <= 0:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
                logger.debug("Removed position via update: {}", symbol)
            else:
                conn.execute("""
                    INSERT OR REPLACE INTO positions (symbol, quantity, avg_price, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (symbol, quantity, avg_price, datetime.now()))
                logger.debug("Updated position via sync: {} x {} @ ${:.2f}", symbol, quantity, avg_price)
    
    def record_exit(self, symbol: str, quantity: int, price: float,
                   entry_price: float, reason: str = "") -> int:
        """Record trade exit with P&L"""
        total = quantity * price
        pnl = (price - entry_price) * quantity
        pnl_pct = (price - entry_price) / entry_price if entry_price > 0 else 0
        
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (symbol, side, quantity, price, total, exit_time, pnl, pnl_pct, reason)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, quantity, price, total, datetime.now(), pnl, pnl_pct, reason))
            trade_id = cursor.lastrowid
            
            # Remove from positions
            conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            
        logger.debug("Recorded exit: {} x {} @ ${:.2f} (P&L: ${:.2f})", 
                    symbol, quantity, price, pnl)
        return trade_id
    
    def get_trades_today(self, target_date: date = None) -> List[TradeRecord]:
        """Get all trades for a specific US Eastern date (defaults to today)"""
        try:
            import pytz
            today = target_date.isoformat() if target_date else datetime.now(pytz.timezone('US/Eastern')).date().isoformat()
        except Exception:
            today = target_date.isoformat() if target_date else date.today().isoformat()
            
        with self._get_conn() as conn:
            # Shift KST entry_time by 14 hours backwards to align with US Eastern Date
            # 23:30 KST - 14h = 09:30 US Date, 06:00 KST - 14h = 16:00 US Date
            rows = conn.execute("""
                SELECT * FROM trades 
                WHERE DATE(entry_time, '-14 hours') = ? OR DATE(exit_time, '-14 hours') = ?
                ORDER BY created_at DESC
            """, (today, today)).fetchall()
        
        return [self._row_to_trade(row) for row in rows]
    
    def get_trades_range(self, start: date, end: date) -> List[TradeRecord]:
        """Get trades in date range"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM trades 
                WHERE (entry_time IS NOT NULL AND DATE(entry_time) BETWEEN ? AND ?)
                   OR (exit_time IS NOT NULL AND DATE(exit_time) BETWEEN ? AND ?)
                ORDER BY created_at DESC
            """, (start.isoformat(), end.isoformat(), start.isoformat(), end.isoformat())).fetchall()
        
        return [self._row_to_trade(row) for row in rows]
    
    def _row_to_trade(self, row) -> TradeRecord:
        """Convert database row to TradeRecord"""
        
        def parse_dt(dt_str):
            if not dt_str: return None
            try: return datetime.fromisoformat(dt_str)
            except Exception: return dt_str

        return TradeRecord(
            id=row['id'],
            symbol=row['symbol'],
            side=row['side'],
            quantity=row['quantity'],
            price=row['price'],
            total=row['total'],
            entry_time=parse_dt(row['entry_time']),
            exit_time=parse_dt(row['exit_time']),
            pnl=row['pnl'] or 0,
            pnl_pct=row['pnl_pct'] or 0,
            reason=row['reason'] or "",
            regime=row['regime'] or ""
        )
    
    # ==============================================
    # Daily Stats
    # ==============================================
    
    def save_daily_stats(self, stats: DailyRecord):
        """Save daily statistics"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_stats 
                (date, starting_balance, ending_balance, trades_count, wins, losses,
                 gross_pnl, net_pnl, max_drawdown, regime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.date.isoformat(),
                stats.starting_balance,
                stats.ending_balance,
                stats.trades_count,
                stats.wins,
                stats.losses,
                stats.gross_pnl,
                stats.net_pnl,
                stats.max_drawdown,
                stats.regime
            ))
        logger.debug("Saved daily stats for {}", stats.date)
    
    def get_daily_stats(self, d: date) -> Optional[DailyRecord]:
        """Get stats for specific date"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM daily_stats WHERE date = ?",
                (d.isoformat(),)
            ).fetchone()
        
        if row:
            return DailyRecord(
                date=datetime.fromisoformat(row['date']).date(),
                starting_balance=row['starting_balance'],
                ending_balance=row['ending_balance'],
                trades_count=row['trades_count'],
                wins=row['wins'],
                losses=row['losses'],
                gross_pnl=row['gross_pnl'],
                net_pnl=row['net_pnl'],
                max_drawdown=row['max_drawdown'],
                regime=row['regime'] or ""
            )
        return None
    
    def get_weekly_stats(self) -> List[DailyRecord]:
        """Get last 7 days stats"""
        end = date.today()
        start = end - timedelta(days=7)
        
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM daily_stats 
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (start.isoformat(), end.isoformat())).fetchall()
        
        return [DailyRecord(
            date=datetime.fromisoformat(row['date']).date(),
            starting_balance=row['starting_balance'],
            ending_balance=row['ending_balance'],
            trades_count=row['trades_count'],
            wins=row['wins'],
            losses=row['losses'],
            gross_pnl=row['gross_pnl'],
            net_pnl=row['net_pnl'],
            max_drawdown=row['max_drawdown'],
            regime=row['regime'] or ""
        ) for row in rows]
    
    # ==============================================
    # Statistics
    # ==============================================
    
    def get_symbol_stats(self, symbol: str) -> dict:
        """Get performance stats for a symbol"""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as total_pnl,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM trades 
                WHERE symbol = ? AND side = 'SELL'
            """, (symbol,)).fetchone()
        
        return {
            "symbol": symbol,
            "trades": row['trades'] or 0,
            "wins": row['wins'] or 0,
            "total_pnl": row['total_pnl'] or 0,
            "avg_pnl_pct": row['avg_pnl_pct'] or 0,
            "win_rate": (row['wins'] or 0) / max(row['trades'] or 1, 1)
        }
    
    def get_open_positions(self) -> List[dict]:
        """Get current open positions"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM positions").fetchall()
        
        return [dict(row) for row in rows]
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Remove old data to save disk space"""
        cutoff = (date.today() - timedelta(days=days_to_keep)).isoformat()
        
        with self._get_conn() as conn:
            conn.execute("DELETE FROM trades WHERE DATE(entry_time) < ?", (cutoff,))
            conn.execute("DELETE FROM daily_stats WHERE date < ?", (cutoff,))
            conn.execute("DELETE FROM sent_reports WHERE report_date < ?", (cutoff,))
        
        logger.info("Cleaned up data older than {} days", days_to_keep)

    # ==============================================
    # Report Tracking
    # ==============================================

    def is_report_sent(self, report_type: str, report_date: date) -> bool:
        """Check if a report has already been sent for a specific date"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM sent_reports WHERE report_type = ? AND report_date = ?",
                (report_type, report_date.isoformat())
            ).fetchone()
        return row is not None

    def mark_report_sent(self, report_type: str, report_date: date):
        """Mark a report as sent for a specific date"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sent_reports (report_type, report_date) VALUES (?, ?)",
                (report_type, report_date.isoformat())
            )
        logger.info("Marked report {} sent for {}", report_type, report_date)


# Global instance
_db = None

def get_database() -> TradeDatabase:
    global _db
    if _db is None:
        _db = TradeDatabase()
    return _db


if __name__ == "__main__":
    print("Testing TradeDatabase...")
    db = TradeDatabase("test_trades.db")
    
    # Test entry/exit
    trade_id = db.record_entry("AAPL", 10, 150.0, "RISK_ON")
    print(f"Entry recorded: ID={trade_id}")
    
    db.record_exit("AAPL", 10, 155.0, 150.0, "Take profit")
    print("Exit recorded")
    
    # Get today's trades
    trades = db.get_trades_today()
    print(f"Today's trades: {len(trades)}")
    
    # Cleanup test file
    Path("test_trades.db").unlink(missing_ok=True)
