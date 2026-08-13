"""
Quant Trade Error Notebook & Post-Trade Diagnostic Engine (trade_error_notebook.py)
=============================================================================
Logs ultra-detailed trade execution metadata for both BUY entries and SELL exits,
creates automated "Error Notebook" (오답노트) diagnostic analysis for every loss trade,
and categorizes loss root causes (e.g., REGIME_BREAKDOWN, HIGH_SLIPPAGE, EARLY_EXIT, EARNINGS_TRAP)
to enable self-learning quant optimization!
"""

import os, sqlite3, json
from datetime import datetime, date
from loguru import logger
from typing import Dict, List, Optional

class TradeErrorNotebook:
    """Detailed Trade Execution Logger & Quant Error Notebook (오답노트)"""
    
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path if os.path.exists(db_path) else "/home/ubuntu/kis-auto-trading/trades.db"
        self._init_tables()

    def _init_tables(self):
        """Ensure detailed trade metadata & error notebook tables exist"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS trade_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id INTEGER,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            entry_score INTEGER,
            score_breakdown TEXT,
            regime TEXT,
            vpin_toxicity REAL,
            parkinson_vol REAL,
            rs_momentum_rank REAL,
            setup_reason TEXT,
            holding_hours REAL,
            pnl REAL DEFAULT 0,
            pnl_pct REAL DEFAULT 0,
            error_tag TEXT,
            diagnostic_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

    def record_entry_detail(self, symbol: str, quantity: int, price: float, score: int, 
                            score_breakdown: dict, regime: str, vpin: float = 0.0, 
                            volatility: float = 0.0, rs_rank: float = 0.0, reason: str = ""):
        """Record ultra-detailed metadata for BUY entries"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO trade_details 
            (symbol, side, quantity, price, entry_score, score_breakdown, regime, vpin_toxicity, parkinson_vol, rs_momentum_rank, setup_reason, created_at)
            VALUES (?, 'BUY', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, quantity, price, score, json.dumps(score_breakdown or {}), regime, vpin, volatility, rs_rank, reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            logger.info("📝 Detailed BUY entry recorded in Error Notebook for {}: Score={} | Reason={}", symbol, score, reason)
        except Exception as e:
            logger.error("Failed to record BUY detail for {}: {}", symbol, e)

    def record_exit_detail(self, symbol: str, quantity: int, exit_price: float, pnl: float, pnl_pct: float, reason: str):
        """Record ultra-detailed metadata and generate Error Notebook tag for SELL exits"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.row_factory = sqlite3.Row
            
            # Find matching BUY entry detail
            cur.execute("SELECT * FROM trade_details WHERE symbol = ? AND side = 'BUY' ORDER BY id DESC LIMIT 1", (symbol,))
            entry_row = cur.fetchone()
            
            entry_dt = entry_row['created_at'] if entry_row else None
            holding_hours = 0.0
            if entry_dt:
                try:
                    dt_e = datetime.strptime(entry_dt, "%Y-%m-%d %H:%M:%S")
                    dt_x = datetime.now()
                    holding_hours = round((dt_x - dt_e).total_seconds() / 3600.0, 2)
                except Exception:
                    pass

            # Diagnose Root Cause for Error Notebook (오답노트)
            error_tag = "WINNER" if pnl > 0 else "NORMAL_STOP"
            notes = f"Trade closed with PnL ${pnl:+.2f} ({pnl_pct:+.2%}) after {holding_hours} hours."
            
            if pnl < 0:
                if "STOP_LOSS" in reason.upper():
                    if holding_hours < 24.0:
                        error_tag = "EARLY_STOPOUT_NOISE"
                        notes = f"Stopped out quickly within {holding_hours}h. Market noise or tight stop."
                    else:
                        error_tag = "TREND_REVERSAL_LOSS"
                        notes = f"Held for {holding_hours}h before stop loss triggered. Trend failed."
                elif "REGIME" in reason.upper():
                    error_tag = "MACRO_REGIME_SHIFT"
                    notes = "Closed due to macro risk-off regime breakdown."
                else:
                    error_tag = "UNEXPECTED_LOSS"
                    notes = f"Closed with loss under reason: {reason}"

            cur.execute("""
            INSERT INTO trade_details 
            (symbol, side, quantity, price, entry_score, score_breakdown, regime, vpin_toxicity, parkinson_vol, rs_momentum_rank, setup_reason, holding_hours, pnl, pnl_pct, error_tag, diagnostic_notes, created_at)
            VALUES (?, 'SELL', ?, ?, 0, '', '', 0, 0, 0, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, quantity, exit_price, reason, holding_hours, pnl, pnl_pct, error_tag, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            conn.close()
            logger.info("📝 Detailed SELL exit & Error Notebook Tagged for {}: Tag={} | PnL=${:+.2f} ({:+.2%})", symbol, error_tag, pnl, pnl_pct)
        except Exception as e:
            logger.error("Failed to record SELL detail for {}: {}", symbol, e)

    def generate_error_notebook_report(self) -> dict:
        """Generate structured Error Notebook Summary for Quant Strategy Refinement"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM trade_details WHERE side = 'SELL' AND pnl < 0 ORDER BY id DESC LIMIT 50")
        loss_rows = cur.fetchall()
        conn.close()
        
        tag_counts = {}
        for r in loss_rows:
            tag = r['error_tag'] or 'UNCLASSIFIED'
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
        report = {
            "total_loss_trades_analyzed": len(loss_rows),
            "error_tag_breakdown": tag_counts,
            "recent_loss_diagnostics": [
                {
                    "symbol": r['symbol'],
                    "pnl": r['pnl'],
                    "pnl_pct": r['pnl_pct'],
                    "holding_hours": r['holding_hours'],
                    "error_tag": r['error_tag'],
                    "notes": r['diagnostic_notes']
                } for r in loss_rows[:10]
            ]
        }
        return report

if __name__ == "__main__":
    notebook = TradeErrorNotebook()
    # Test recording
    notebook.record_entry_detail("AAPL", 2, 220.50, 88, {"technical": 85, "macro": 90}, "RISK_ON", 0.12, 0.16, 0.95, "SWING_BREAKOUT")
    notebook.record_exit_detail("AAPL", 2, 225.80, 10.60, 0.024, "PROFIT_TAKE")
    rep = notebook.generate_error_notebook_report()
    print("Error Notebook Diagnostic Summary:", json.dumps(rep, indent=2, ensure_ascii=False))
