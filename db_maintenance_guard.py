"""
3. Zero-Downtime SQLite Integrity, Vacuum & 7-Day Rotating Backup Guard (db_maintenance_guard.py)
==================================================================================================
Features:
1. Automated SQLite Integrity Check (PRAGMA integrity_check).
2. Database Vacuuming & B-Tree Defragmentation (VACUUM & PRAGMA optimize).
3. 7-Day Rotating Snapshot Backup (trades_backup_YYYYMMDD.db), keeping the database file lean and corruption-free.
"""

import os
import shutil
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any
from loguru import logger

class DBMaintenanceGuard:
    """Manages SQLite database health, defragmentation, and rotating snapshots"""

    def __init__(self, db_path: str = "trades.db", backup_dir: str = "backups", max_backups: int = 7):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.max_backups = max_backups

    def run_daily_maintenance(self) -> Dict[str, Any]:
        """
        Execute full database health check, vacuuming, and dated backup snapshot.
        """
        res = {
            "integrity_ok": False,
            "vacuum_ok": False,
            "backup_created": "",
            "cleaned_old_backups": 0,
            "error": None
        }

        if not self.db_path.exists():
            res["error"] = "DB file does not exist"
            return res

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # 1. Integrity Check
            conn = sqlite3.connect(str(self.db_path))
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check;")
            row = cur.fetchone()
            if row and row[0] == "ok":
                res["integrity_ok"] = True
            else:
                logger.error("🚨 DB Integrity Check Failed: {}", row)

            # 2. Optimize & Vacuum
            cur.execute("PRAGMA optimize;")
            conn.commit()
            conn.close()

            # Vacuum via dedicated connection
            conn_vac = sqlite3.connect(str(self.db_path))
            conn_vac.execute("VACUUM;")
            conn_vac.close()
            res["vacuum_ok"] = True

            # 3. Create Dated Snapshot Backup
            today_str = datetime.now().strftime("%Y%m%d")
            backup_file = self.backup_dir / f"trades_backup_{today_str}.db"
            shutil.copy2(str(self.db_path), str(backup_file))
            res["backup_created"] = str(backup_file)
            logger.info("💾 [DB_MAINTENANCE] Snapshot created: {}", backup_file)

            # 4. Clean backups older than max_backups days
            existing_backups = sorted(list(self.backup_dir.glob("trades_backup_*.db")))
            if len(existing_backups) > self.max_backups:
                to_delete = existing_backups[:-self.max_backups]
                for old_f in to_delete:
                    try:
                        old_f.unlink()
                        res["cleaned_old_backups"] += 1
                        logger.info("🗑️ [DB_MAINTENANCE] Removed old backup: {}", old_f.name)
                    except Exception:
                        pass

            logger.success("✅ [DB_MAINTENANCE] Daily SQLite optimization, integrity check & backup finished successfully.")
            return res

        except Exception as e:
            logger.error("DB Maintenance failed: {}", e)
            res["error"] = str(e)
            return res
