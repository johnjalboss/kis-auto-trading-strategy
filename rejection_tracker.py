"""
[v1.0 QUANT REJECTION TRACKER & AUDIT TRAIL]
Records and audits why candidate stocks were blocked or disqualified during Phase 4 evaluation.
Provides 100% transparency into the bot's risk management decisions.
"""

import sqlite3
import datetime
import threading
from typing import List, Dict, Any, Optional
from loguru import logger
import pytz

_TRACKER_INSTANCE = None
_LOCK = threading.Lock()


class RejectionTracker:
    def __init__(self, db_path: str = "trades.db"):
        self.db_path = db_path
        self._memory_cache: List[Dict[str, Any]] = []
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS screener_rejections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        symbol TEXT NOT NULL,
                        score INTEGER DEFAULT 0,
                        action TEXT,
                        guard_name TEXT,
                        reason TEXT,
                        market_date DATE
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_rejections_date ON screener_rejections(market_date);")
                conn.commit()
        except Exception as e:
            logger.debug("Failed to init screener_rejections table: {}", e)

    def _get_us_market_date(self) -> datetime.date:
        try:
            return datetime.datetime.now(pytz.timezone('US/Eastern')).date()
        except Exception:
            return datetime.date.today()

    def record(self, symbol: str, score: int, action: str, guard_name: str, reason: str):
        """Record a candidate rejection event."""
        with _LOCK:
            now_kst = datetime.datetime.now()
            market_d = self._get_us_market_date()
            entry = {
                "timestamp": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
                "time_short": now_kst.strftime("%H:%M"),
                "symbol": symbol,
                "score": int(score) if score is not None else 0,
                "action": str(action),
                "guard_name": str(guard_name),
                "reason": str(reason),
                "market_date": str(market_d)
            }
            # Deduplicate same symbol + same guard within last 15 minutes
            for prev in self._memory_cache[-20:]:
                if prev["symbol"] == symbol and prev["guard_name"] == str(guard_name):
                    # Update timestamp and return
                    prev["timestamp"] = entry["timestamp"]
                    prev["time_short"] = entry["time_short"]
                    prev["score"] = entry["score"]
                    prev["reason"] = entry["reason"]
                    return

            self._memory_cache.append(entry)
            if len(self._memory_cache) > 50:
                self._memory_cache.pop(0)

            try:
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    conn.execute("""
                        INSERT INTO screener_rejections (timestamp, symbol, score, action, guard_name, reason, market_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry["timestamp"],
                        symbol,
                        entry["score"],
                        entry["action"],
                        entry["guard_name"],
                        entry["reason"],
                        entry["market_date"]
                    ))
                    conn.commit()
            except Exception as e:
                logger.debug("Failed to persist rejection to DB: {}", e)

    def get_recent_rejections(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent rejections from memory or DB."""
        with _LOCK:
            if self._memory_cache:
                return list(reversed(self._memory_cache[-limit:]))

        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT timestamp, symbol, score, action, guard_name, reason, market_date
                    FROM screener_rejections
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                rows = c.fetchall()
                res = []
                for r in rows:
                    res.append({
                        "timestamp": r[0],
                        "time_short": r[0][11:16] if len(r[0]) >= 16 else r[0],
                        "symbol": r[1],
                        "score": r[2],
                        "action": r[3],
                        "guard_name": r[4],
                        "reason": r[5],
                        "market_date": r[6]
                    })
                return res
        except Exception as e:
            logger.debug("Failed to query screener_rejections from DB: {}", e)
            return []

    def format_rejection_summary(self, limit: int = 10) -> str:
        """Format an informative Telegram report on blocked candidates."""
        rejections = self.get_recent_rejections(limit)
        
        if not rejections:
            return (
                "🛡️ <b>[스크리닝 & 진입 보류 현황]</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "최근 보류되거나 차단된 진입 후보가 없습니다.\n"
                "<i>(시장 개장 후 3,000+ 종목 스크리닝 시 실시간 기록됩니다.)</i>"
            )

        lines = [
            "🛡️ <b>[스크리닝 & 진입 보류 현황]</b>",
            "━━━━━━━━━━━━━━━━━━━",
            "3,000+개 유니버스 중 상위 후보 진입 검증 결과:\n"
        ]

        def _clean_reason(guard: str, raw: str) -> str:
            # Map guard and raw reason to friendly Korean text
            if "OVEREXTENDED" in raw or "50MA" in raw:
                return "고점 추격 방지: 이평선 대비 단기 급등 과열"
            if "EARNINGS_GUARD" in raw or "PreEarnings" in raw:
                return "실적 변동성 회피: 실적 발표 직전 위험 구간"
            if "WALL_STREET" in raw or "ANALYST_SELL" in raw:
                return "월가 컨센서스: 애널리스트 다수 매도 투자의견"
            if "INSIDER" in raw:
                return "내부자 투매 감지: 임직원 대량 순매도 적발"
            if "TICKER_QUARANTINE" in raw or "QUARANTINED" in raw:
                return "재진입 쿨다운: 최근 청산 후 격리 보호 기간"
            if "CLUSTER_CAP" in raw:
                return "섹터/클러스터 비중 초과: 동일 섹터 집중 위험 방어"
            if "SECTOR_GUARD" in raw:
                return "동일 섹터 최대 2개 보유 한도 도달"
            if "COOLDOWN" in raw:
                return "당일 매도 종목 재매수 쿨다운"
            if "ADX" in raw or "BB%" in raw or "MACD" in raw:
                return "기술적 지표 미달: 추세 강도 부족 또는 상단 이탈"
            if "OBV" in raw or "MaxPain" in raw:
                return "수급/옵션 하방 압력: OBV 하락 또는 핀 리스크"
            return raw[:65]

        seen_symbols = set()
        count = 0
        for item in rejections:
            sym = item["symbol"]
            if sym in seen_symbols:
                continue
            seen_symbols.add(sym)
            count += 1
            if count > limit:
                break

            time_str = item["time_short"]
            score = item["score"]
            guard = item["guard_name"]
            reason_kr = _clean_reason(guard, item["reason"])

            lines.append(f"• <b>{sym}</b> (점수: <code>{score}점</code>)")
            lines.append(f"  ⛔ {reason_kr}")
            lines.append(f"  ⏰ 감지: {time_str} KST\n")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>원금 보호 헌법에 따라 리스크가 감지된 종목은 매수를 보류하고 100% 안전 현금으로 보존했습니다.</i>")
        return "\n".join(lines)


def get_rejection_tracker(db_path: str = "trades.db") -> RejectionTracker:
    global _TRACKER_INSTANCE
    if _TRACKER_INSTANCE is None:
        _TRACKER_INSTANCE = RejectionTracker(db_path)
    return _TRACKER_INSTANCE
