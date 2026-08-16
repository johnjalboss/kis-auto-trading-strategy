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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    high_since_entry REAL DEFAULT 0.0,
                    stop_price REAL DEFAULT 0.0
                );
                
                CREATE TABLE IF NOT EXISTS sent_reports (
                    report_type TEXT NOT NULL,
                    report_date DATE NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (report_type, report_date)
                );
                
                CREATE TABLE IF NOT EXISTS macro_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    risk_level TEXT NOT NULL,
                    penalty INTEGER NOT NULL,
                    reason TEXT,
                    resolved INTEGER DEFAULT 0,
                    spy_entry_price REAL,
                    spy_exit_price REAL,
                    accuracy TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(entry_time);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
            """)
            
            # positions 테이블의 트레일링 스탑 상태 컬럼 마이그레이션 (재시작 시 상태 손실 방지)
            try:
                existing_cols = [x[1] for x in conn.execute("PRAGMA table_info(positions)").fetchall()]
                if "high_since_entry" not in existing_cols:
                    conn.execute("ALTER TABLE positions ADD COLUMN high_since_entry REAL DEFAULT 0.0")
                if "stop_price" not in existing_cols:
                    conn.execute("ALTER TABLE positions ADD COLUMN stop_price REAL DEFAULT 0.0")
            except Exception as e:
                logger.error("Failed to migrate positions table schema: {}", e)
                
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
                # [CRITICAL FIX] 기존에는 INSERT OR REPLACE를 사용하여 기존 entry_time을 NULL로 덮어쓰고 있었음.
                # 이로 인해 매 재시작마다 보유 시간이 0으로 초기화되어 업그레이드(교체매매) 로직이 영구 작동 불능 상태였음.
                row = conn.execute("SELECT entry_time FROM positions WHERE symbol = ?", (symbol,)).fetchone()
                now_dt = datetime.now()
                if row and row[0] is not None:
                    conn.execute("""
                        UPDATE positions SET quantity = ?, avg_price = ?, updated_at = ?
                        WHERE symbol = ?
                    """, (quantity, avg_price, now_dt, symbol))
                else:
                    conn.execute("""
                        INSERT OR REPLACE INTO positions (symbol, quantity, avg_price, entry_time, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (symbol, quantity, avg_price, now_dt, now_dt))
                logger.debug("Updated position via sync: {} x {} @ ${:.2f}", symbol, quantity, avg_price)
                
    def update_position_tracking(self, symbol: str, high_since_entry: float, stop_price: float):
        """Update position tracking values (high_since_entry, stop_price) to prevent state loss on restart"""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE positions 
                SET high_since_entry = ?, stop_price = ?, updated_at = ?
                WHERE symbol = ?
            """, (high_since_entry, stop_price, datetime.now(), symbol))
        logger.debug("Updated position tracking: {} (High: ${:.2f}, Stop: ${:.2f})", symbol, high_since_entry, stop_price)
    
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
            
            # Check remaining quantity in positions table
            cur_pos = conn.execute("SELECT quantity FROM positions WHERE symbol = ?", (symbol,)).fetchone()
            if cur_pos and cur_pos[0] > quantity:
                rem_qty = cur_pos[0] - quantity
                conn.execute("UPDATE positions SET quantity = ?, updated_at = ? WHERE symbol = ?",
                             (rem_qty, datetime.now(), symbol))
                logger.info("Partial exit in DB: {} remaining {} -> {}", symbol, cur_pos[0], rem_qty)
            else:
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

    def claim_report_sending_lock(self, report_type: str, report_date: date) -> bool:
        """
        Atomically attempts to claim report sending lock.
        Returns True if lock acquired (first to send).
        Returns False if report was already claimed or sent by another process/thread.
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO sent_reports (report_type, report_date) VALUES (?, ?)",
                    (report_type, report_date.isoformat())
                )
                logger.info("🔒 Atomic report lock claimed for {} on {}", report_type, report_date)
                return True
        except Exception:
            # Primary key constraint violation (already claimed/sent)
            return False

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

    # ==============================================
    # Macro Feedback Loops (Self-Feedback Audit)
    # ==============================================

    def record_macro_decision(self, risk_level: str, penalty: int, reason: str, spy_price: float = None) -> int:
        """Record macro lockdown decision for future self-feedback audit"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO macro_feedback (risk_level, penalty, reason, spy_entry_price, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (risk_level, penalty, reason, spy_price, datetime.now()))
            return cursor.lastrowid

    def get_unresolved_macro_feedbacks(self) -> List[dict]:
        """Fetch macro decisions that are pending resolution (unresolved) and at least 3 days old"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM macro_feedback 
                WHERE resolved = 0 AND datetime(created_at) < datetime('now', '-3 days')
            """).fetchall()
        return [dict(row) for row in rows]

    def resolve_macro_feedback(self, feedback_id: int, spy_exit_price: float, accuracy: str):
        """Update macro decision outcome after post-mortem evaluation"""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE macro_feedback
                SET resolved = 1, spy_exit_price = ?, accuracy = ?, resolved_at = ?
                WHERE id = ?
            """, (spy_exit_price, accuracy, datetime.now(), feedback_id))

    def get_recent_resolved_feedbacks(self, days: int = 30) -> List[dict]:
        """Fetch resolved macro feedbacks within recent days"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM macro_feedback 
                WHERE resolved = 1 AND datetime(resolved_at) >= ?
            """, (cutoff,)).fetchall()
        return [dict(row) for row in rows]

    def create_daily_backup(self, backup_dir: str = "backups") -> Optional[str]:
        """Creates an atomic timestamped SQLite snapshot backup with 30-day retention."""
        import shutil
        import os
        try:
            os.makedirs(backup_dir, exist_ok=True)
            today_str = datetime.now().strftime("%Y%m%d")
            backup_file = os.path.join(backup_dir, f"trades_backup_{today_str}.db")
            
            if os.path.exists(self.db_path):
                # SQLite Online Backup API for 100% ACID consistency during live trading
                with self._get_conn() as src_conn:
                    dst_conn = sqlite3.connect(backup_file)
                    src_conn.backup(dst_conn)
                    dst_conn.close()
                logger.info("🛡️ [DB_BACKUP] Atomic snapshot created: {}", backup_file)
                
                # Retention cleanup (keep last 30 daily backups)
                all_backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith("trades_backup_")])
                if len(all_backups) > 30:
                    for old_b in all_backups[:-30]:
                        try:
                            os.remove(old_b)
                            logger.debug("Cleaned up expired DB backup: {}", old_b)
                        except Exception:
                            pass
                return backup_file
        except Exception as b_err:
            logger.warning("DB backup creation skipped: {}", b_err)
        return None


# Global instance
_db = None

def get_database() -> TradeDatabase:
    global _db
    if _db is None:
        _db = TradeDatabase()
        try:
            _db.create_daily_backup()
        except Exception:
            pass
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
