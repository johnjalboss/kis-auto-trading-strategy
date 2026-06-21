import os
import sqlite3
import datetime
from typing import Dict, List, Any, Tuple

# US Theme Tracker DB Path
DB_PATH = r"C:\Users\wngud\.gemini\antigravity\scratch\us-theme-tracker\us_stocks_data.db"

class ThemeRadarAdapter:
    """
    US Theme Radar와 한국투자증권 자동매매봇(kis-auto-trading)을 연결해 주는 브릿지 어댑터
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _query(self, sql: str, params: tuple = ()) -> List[tuple]:
        """데이터베이스 쿼리 헬퍼"""
        if not os.path.exists(self.db_path):
            print(f"[ThemeRadarAdapter] Warning: DB file not found at {self.db_path}")
            return []
        
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()
        except sqlite3.Error as e:
            print(f"[ThemeRadarAdapter] SQLite error: {e}")
            return []
        finally:
            conn.close()

    def get_true_signals(self) -> List[Dict[str, Any]]:
        """
        테마 레이더에서 'TRUE_SIGNAL'(🟢 진짜 신호)이 감지된 테마들의 목록을 반환
        """
        sql = """
            SELECT theme_id, name_ko, signal_type, quality, med_rvol, ret_5d, updated_at
            FROM theme_signals
            WHERE signal_type = 'TRUE_SIGNAL'
            ORDER BY quality DESC
        """
        rows = self._query(sql)
        signals = []
        for r in rows:
            signals.append({
                "theme_id": r[0],
                "name_ko": r[1],
                "signal_type": r[2],
                "quality": r[3],
                "med_rvol": r[4],
                "ret_5d": r[5],
                "updated_at": r[6]
            })
        return signals

    def get_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """
        실시간 추천 탑픽 종목군(LEADER 및 SETUP)을 Ticker 기준의 딕셔너리로 반환
        """
        sql = """
            SELECT r.ticker, r.theme_id, r.pick_type, r.price, r.target_price, r.stop_loss, r.target_pct, r.stop_pct, r.updated_at, s.name_ko
            FROM theme_recommendations r
            JOIN theme_signals s ON r.theme_id = s.theme_id
            WHERE s.signal_type IN ('TRUE_SIGNAL', 'WATCH')
        """
        rows = self._query(sql)
        recs = {}
        for r in rows:
            ticker = r[0]
            recs[ticker] = {
                "theme_id": r[1],
                "pick_type": r[2],
                "price": r[3],
                "target_price": r[4],
                "stop_loss": r[5],
                "target_pct": r[6],
                "stop_pct": r[7],
                "updated_at": r[8],
                "theme_name": r[9]
            }
        return recs

    def filter_candidates(self, candidates: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        매매 후보군 종목(candidates) 중 테마 레이더 탑픽에 걸려있는 종목들만 필터링하여 반환
        """
        recs = self.get_recommendations()
        matched = []
        for t in candidates:
            if t in recs:
                matched.append((t, recs[t]))
        return matched
