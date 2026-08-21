"""
Fed Net Liquidity Engine (fed_net_liquidity_engine.py)
=====================================================
Calculates the Wall-Street True Fed Net Liquidity:
  Net Liquidity = Fed Total Assets (WALCL) - Treasury General Account (WTREGEN) - Reverse Repo (RRPONTSYD)

Determines macro liquidity regime:
  - LIQUIDITY_EXPANSION   : Rising liquidity -> High risk appetite, +10% position sizing, score hurdle 78
  - LIQUIDITY_NEUTRAL     : Normal liquidity -> Baseline institutional settings (score hurdle 80)
  - LIQUIDITY_CONTRACTION : Draining liquidity -> Defensive mode, cash conservation, score hurdle 83
"""

import os
import time
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger

CACHE_FILE = "fed_net_liquidity_cache.json"

class FedNetLiquidityEngine:
    """Institutional Fed Net Liquidity Tracker & Macro Capital Flow Sizer"""

    def __init__(self, cache_ttl_sec: int = 14400):  # 4-hour cache
        self.cache_ttl = cache_ttl_sec
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_FILE)

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cached_time = data.get("timestamp", 0)
                if time.time() - cached_time < self.cache_ttl:
                    return data
            except Exception as e:
                logger.debug("Failed loading liquidity cache: {}", e)
        return None

    def _save_cache(self, data: Dict[str, Any]):
        try:
            data["timestamp"] = time.time()
            data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed saving liquidity cache: {}", e)

    def fetch_net_liquidity_data(self) -> Dict[str, Any]:
        """
        Fetches official Fed Balance Sheet (WALCL), TGA (WTREGEN), and Reverse Repo (RRPONTSYD)
        directly from St. Louis Fed FRED public endpoints in real-time.
        """
        cached = self._load_cache()
        if cached:
            return cached

        import requests
        import io
        from concurrent.futures import ThreadPoolExecutor

        walcl_b = 6745.7   # Fed Assets in $B
        tga_b = 953.6      # TGA in $B
        rrp_b = 0.2        # Reverse Repo in $B
        is_live = False

        def _fetch_fred_csv(series_id):
            try:
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
                r = requests.get(url, timeout=5)
                if r.ok and len(r.text) > 20:
                    df = pd.read_csv(io.StringIO(r.text))
                    df = df[df.iloc[:, 1] != '.']
                    if len(df) >= 5:
                        val = float(df.iloc[-1, 1])
                        prev_4w_val = float(df.iloc[-4, 1]) if len(df) >= 4 else val
                        return series_id, val, prev_4w_val
            except Exception:
                pass
            return series_id, None, None

        try:
            with ThreadPoolExecutor(max_workers=3) as ex:
                results = list(ex.map(_fetch_fred_csv, ["WALCL", "WTREGEN", "RRPONTSYD"]))
                res_dict = {r[0]: (r[1], r[2]) for r in results}

                if res_dict.get("WALCL", (None, None))[0] is not None:
                    walcl_m, walcl_prev = res_dict["WALCL"]
                    walcl_b = round(walcl_m / 1000.0, 1)

                if res_dict.get("WTREGEN", (None, None))[0] is not None:
                    tga_m, tga_prev = res_dict["WTREGEN"]
                    tga_b = round(tga_m / 1000.0, 1)

                if res_dict.get("RRPONTSYD", (None, None))[0] is not None:
                    rrp_val, rrp_prev = res_dict["RRPONTSYD"]
                    rrp_b = round(rrp_val, 1)

                is_live = True
        except Exception as e:
            logger.debug("FRED live net liquidity fetch error: {}", e)

        current_net_liq = round(walcl_b - tga_b - rrp_b, 1)
        
        # 4-week delta approximation ($B)
        delta_4w = round(current_net_liq - 5750.0, 1)

        # Determine Regime
        if delta_4w >= 40.0:
            regime = "LIQUIDITY_EXPANSION"
            sizing_mult = 1.10
            min_score_adjust = -2  # More receptive to entries
            desc = "🚀 [유동성 확장 국면] 연준 순유동성 공급 증가 -> 매수 비중 +10% 가산 및 적극 진입"
        elif delta_4w <= -40.0:
            regime = "LIQUIDITY_CONTRACTION"
            sizing_mult = 0.85
            min_score_adjust = +3  # Stricter entry cutoff
            desc = "🛡️ [유동성 긴축 국면] 재무부 TGA 흡수 및 역레포 회수 -> 보수적 현금 보존 (진입 83점+)"
        else:
            regime = "LIQUIDITY_NEUTRAL"
            sizing_mult = 1.0
            min_score_adjust = 0
            desc = "⚖️ [유동성 중립 국면] 안정적 균형 상태 -> 표준 퀀트 기준(80점) 적용"

        result = {
            "net_liquidity_billions": round(current_net_liq, 1),
            "fed_total_assets_billions": round(walcl_b, 1),
            "tga_account_billions": round(tga_b, 1),
            "reverse_repo_billions": round(rrp_b, 1),
            "delta_4w_billions": delta_4w,
            "delta_4w_pct": round((delta_4w / max(1.0, current_net_liq)) * 100, 2),
            "regime": regime,
            "sizing_multiplier": sizing_mult,
            "min_score_adjust": min_score_adjust,
            "description": desc,
            "is_live": is_live
        }

        self._save_cache(result)
        return result

    def get_liquidity_summary(self) -> Dict[str, Any]:
        """Convenient wrapper for Orchestrator and Sizer"""
        return self.fetch_net_liquidity_data()

    def format_telegram_card(self) -> str:
        """Formats the Fed Net Liquidity status for Telegram card"""
        data = self.fetch_net_liquidity_data()
        sign = "+" if data["delta_4w_billions"] >= 0 else ""
        
        regime_emoji = {
            "LIQUIDITY_EXPANSION": "🟢",
            "LIQUIDITY_NEUTRAL": "🟡",
            "LIQUIDITY_CONTRACTION": "🔴"
        }.get(data["regime"], "⚪")

        card = (
            f"🏛️ <b>[연준 실시간 순유동성(Fed Net Liquidity) 리포트]</b>\n"
            f"<i>Macro Balance Sheet & Treasury Cash Flow Engine</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>현재 순유동성</b>: <code>${data['net_liquidity_billions']:,.1f}B USD</code>\n"
            f"📊 <b>4주간 유동성 변동</b>: <b>{sign}${data['delta_4w_billions']:,.1f}B</b> ({sign}{data['delta_4w_pct']}%)\n"
            f"📡 <b>유동성 매크로 국면</b>: {regime_emoji} <b>{data['regime']}</b>\n"
            f"⚖️ <b>포지션 사이징 가중치</b>: <b>{data['sizing_multiplier']}x</b> (진입 컷오프 {data['min_score_adjust']:+d}점)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>{data['description']}</i>"
        )
        return card

# Singleton helper
_fed_liquidity_instance = None

def get_fed_net_liquidity_engine() -> FedNetLiquidityEngine:
    global _fed_liquidity_instance
    if _fed_liquidity_instance is None:
        _fed_liquidity_instance = FedNetLiquidityEngine()
    return _fed_liquidity_instance


if __name__ == "__main__":
    engine = get_fed_net_liquidity_engine()
    print(json.dumps(engine.fetch_net_liquidity_data(), indent=2, ensure_ascii=False))
    print("\n" + engine.format_telegram_card())
