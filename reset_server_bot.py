import os
import json
import sqlite3
from loguru import logger

def reset_bot_state():
    # 1. Reset Circuit Breaker
    state_file = "emergency_state.json"
    logger.info(f"Resetting {state_file}...")
    try:
        with open(state_file, "w") as f:
            json.dump({"is_active": False, "severity": "", "reason": ""}, f)
        logger.info("Circuit breaker reset successfully.")
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker: {e}")

    # 2. Sync Database
    db_file = "trades.db"
    logger.info(f"Cleaning up {db_file}...")
    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        
        # Update confirmed positions
        positions_to_sync = [
            ('HST', 1),
            ('MRVL', 1),
            ('TALK', 25)
        ]
        
        # Zero out everything first
        c.execute("UPDATE positions SET qty = 0")
        
        # Update/Insert actual positions
        for ticker, qty in positions_to_sync:
            # Check if exists
            c.execute("SELECT ticker FROM positions WHERE ticker=?", (ticker,))
            if c.fetchone():
                c.execute("UPDATE positions SET qty = ? WHERE ticker = ?", (qty, ticker))
            else:
                # Insert minimal entry
                c.execute("INSERT INTO positions (ticker, qty, avg_price, entry_time) VALUES (?, ?, 0, datetime('now'))", (ticker, qty))
        
        conn.commit()
        
        c.execute("SELECT ticker, qty FROM positions WHERE qty > 0")
        after_pos = c.fetchall()
        logger.info(f"After cleanup DB positions: {after_pos}")
        
        conn.close()
        logger.info("Database cleaned up successfully.")
    except Exception as e:
        logger.error(f"Failed to cleanup database: {e}")

    # 3. Frequency Controller Reset (to allow immediate trades if needed)
    freq_file = "frequency_state.json"
    if os.path.exists(freq_file):
        try:
            with open(freq_file, "w") as f:
                json.dump({"trades_today": 0, "last_reset": ""}, f)
            logger.info("Frequency controller reset.")
        except: pass

if __name__ == "__main__":
    reset_bot_state()
