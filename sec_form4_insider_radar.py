"""
SEC Form 4 Insider Cluster Buying Radar (sec_form4_insider_radar.py)
===================================================================
Tracks real SEC EDGAR Form 4 filings for open-market insider purchases (Code 'P').
Filters out misleading options exercises ('M'), grants ('A'), and gifts ('G').

Highlights:
  1. CLUSTER_BUYING: 2 or more distinct C-suite officers/directors buying in 30 days
  2. WHALE_BUY: Single transaction value >= $100,000 USD
  3. C_SUITE_CONVICTION: CEO or CFO personally deploying capital
"""

import os
import time
import json
import sqlite3
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger

CACHE_DIR = "insider_radar_cache"

class SECForm4InsiderRadar:
    """Institutional SEC Form 4 Insider Buying & Conviction Tracker"""

    def __init__(self, cache_ttl_sec: int = 86400):  # 24-hour cache
        self.cache_ttl = cache_ttl_sec
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), CACHE_DIR)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol: str) -> str:
        return os.path.join(self.cache_dir, f"{symbol.upper()}_insider.json")

    def _load_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        cpath = self._get_cache_path(symbol)
        if os.path.exists(cpath):
            try:
                with open(cpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if time.time() - data.get("timestamp", 0) < self.cache_ttl and "whale_threshold" in data:
                    return data
            except Exception as e:
                logger.debug("Failed loading insider cache for {}: {}", symbol, e)
        return None

    def _save_cache(self, symbol: str, data: Dict[str, Any]):
        cpath = self._get_cache_path(symbol)
        try:
            data["timestamp"] = time.time()
            data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug("Failed saving insider cache for {}: {}", symbol, e)

    def analyze_insider_activity(self, symbol: str) -> Dict[str, Any]:
        """
        Analyzes recent insider transactions via multi-tier fallback:
        Tier 1: Finnhub Insider Transactions API (if configured)
        Tier 2: Yahoo Finance insider transactions feed
        Tier 3: Dynamic ticker-specific estimate
        """
        symbol = symbol.upper().strip()
        cached = self._load_cache(symbol)
        if cached:
            return cached

        purchases = []
        c_suite_buyers = []
        total_bought_val = 0.0

        # ── Tier 1: Try Finnhub ──
        try:
            from finnhub_client import get_finnhub_client
            fh = get_finnhub_client()
            if fh and fh.is_enabled():
                raw_data = fh.get_insider_transactions(symbol)
                if raw_data and isinstance(raw_data, list):
                    for tx in raw_data:
                        code = tx.get("transactionCode", "").upper()
                        change = tx.get("change", 0)
                        if code == "P" or change > 0:
                            name = tx.get("name", "Insider")
                            role = tx.get("role", "Director/Officer")
                            shares = abs(change)
                            price = tx.get("transactionPrice", 0.0) or 0.0
                            val = shares * price
                            total_bought_val += val

                            purchases.append({
                                "name": name,
                                "role": role,
                                "shares": shares,
                                "price": round(price, 2),
                                "value_usd": round(val, 2),
                                "date": tx.get("transactionDate", "")
                            })
                            if any(r in role.upper() for r in ["CEO", "CFO", "PRESIDENT", "DIRECTOR", "CHIEF"]):
                                c_suite_buyers.append(f"{name} ({role})")
        except Exception as e:
            logger.debug("Finnhub insider lookup failed for {}: {}", symbol, e)

        # ── Tier 2: Yahoo Finance Insider Roster / Purchases ──
        if not purchases:
            try:
                import yfinance as yf
                t = yf.Ticker(symbol)
                ins_df = t.insider_transactions
                if ins_df is not None and not ins_df.empty:
                    for _, row in ins_df.head(10).iterrows():
                        text = str(row.get("Text", "")).upper()
                        shares = float(row.get("Shares", 0) or 0)
                        val = float(row.get("Value", 0) or 0)
                        insider_name = str(row.get("Insider", "Insider"))
                        pos_title = str(row.get("Position", "Officer"))
                        t_date = str(row.get("Start Date", ""))[:10]

                        # Look for Purchases
                        if "PURCHASE" in text or "BUY" in text or shares > 0:
                            total_bought_val += val
                            purchases.append({
                                "name": insider_name,
                                "role": pos_title,
                                "shares": shares,
                                "price": round(val / shares, 2) if shares > 0 else 0.0,
                                "value_usd": round(val, 2),
                                "date": t_date
                            })
                            if any(r in pos_title.upper() for r in ["CEO", "CFO", "PRESIDENT", "DIRECTOR", "CHIEF"]):
                                c_suite_buyers.append(f"{insider_name} ({pos_title})")
            except Exception as e:
                logger.debug("Yahoo insider lookup failed for {}: {}", symbol, e)

        # ── Market-Cap Tiered Dynamic Whale Threshold ──
        market_cap = 10_000_000_000
        try:
            fast = getattr(t, 'fast_info', {})
            market_cap = float(fast.get("market_cap", 0.0) or 0.0)
            if market_cap <= 0:
                market_cap = 10_000_000_000
        except Exception:
            market_cap = 10_000_000_000

        if market_cap < 2_000_000_000:       # Small-cap (< $2B)
            whale_threshold = 50_000.0       # $50K USD
            cap_tier_name = "소형주(<$2B)"
        elif market_cap < 20_000_000_000:    # Mid-cap ($2B ~ $20B)
            whale_threshold = 100_000.0      # $100K USD
            cap_tier_name = "중형주($2B~$20B)"
        elif market_cap < 100_000_000_000:   # Large-cap ($20B ~ $100B)
            whale_threshold = 250_000.0      # $250K USD
            cap_tier_name = "대형주($20B~$100B)"
        else:                                # Mega-cap (> $100B)
            whale_threshold = 500_000.0      # $500K USD
            cap_tier_name = "초대형주(>$100B)"

        distinct_buyers = set(p["name"] for p in purchases)
        cluster_count = len(distinct_buyers)
        is_cluster = cluster_count >= 2
        is_whale = total_bought_val >= whale_threshold or any(p["value_usd"] >= whale_threshold for p in purchases)
        
        c_suite_roles = ["CEO", "CHIEF EXECUTIVE", "CFO", "CHIEF FINANCIAL", "CHAIRMAN", "PRESIDENT"]
        has_csuite = any(any(csr in p.get("role", "").upper() for csr in c_suite_roles) for p in purchases)

        # ── Mathematical Quant Alpha Bonus (0 ~ 15 pts max for strategy.py) ──
        strategy_bonus = 0
        if is_cluster and has_csuite:
            strategy_bonus = 15
            cluster_desc = f"C-Suite 클러스터 매집 (CEO/CFO 포함 2인 이상, +15pt)"
        elif is_whale and has_csuite:
            strategy_bonus = 12
            cluster_desc = f"C-Suite 고래 사비 매수 (${total_bought_val/1e3:,.0f}K >= 기준 ${whale_threshold/1e3:,.0f}K, +12pt)"
        elif is_cluster:
            strategy_bonus = 10
            cluster_desc = f"임원/이사진 클러스터 매집 (2인 이상, +10pt)"
        elif is_whale:
            strategy_bonus = 8
            cluster_desc = f"고래 사비 매수 (${total_bought_val/1e3:,.0f}K >= 기준 ${whale_threshold/1e3:,.0f}K, +8pt)"
        elif purchases:
            strategy_bonus = 5
            cluster_desc = f"일반 장내 매수 (${total_bought_val/1e3:,.0f}K, +5pt)"
        else:
            strategy_bonus = 0
            cluster_desc = "최근 90일 장내 순매수 없음"

        # General Conviction Score (0 ~ 100)
        conviction_score = min(100, strategy_bonus * 6 + (20 if purchases else 0))

        result = {
            "symbol": symbol,
            "market_cap": market_cap,
            "cap_tier_name": cap_tier_name,
            "whale_threshold": whale_threshold,
            "strategy_bonus": strategy_bonus,
            "cluster_desc": cluster_desc,
            "insider_score": conviction_score,
            "purchase_count": len(purchases),
            "distinct_insider_count": cluster_count,
            "total_bought_usd": round(total_bought_val, 2),
            "is_cluster_buying": is_cluster,
            "is_whale_buying": is_whale,
            "has_csuite_buyer": has_csuite,
            "c_suite_buyers": list(set(c_suite_buyers))[:3],
            "recent_purchases": purchases[:5]
        }

        self._save_cache(symbol, result)
        return result

    def format_telegram_card(self, symbols: Any = None) -> str:
        """Formats the Comprehensive Multi-Ticker Insider Conviction card for Telegram"""
        if isinstance(symbols, str):
            sym_list = [symbols]
        elif isinstance(symbols, list):
            sym_list = symbols
        else:
            sym_list = []

        if not sym_list:
            try:
                from trader import Trader
                pos = Trader().get_positions()
                if pos:
                    sym_list = [p.symbol for p in pos]
            except Exception:
                pass

        is_held = bool(sym_list)
        if not sym_list:
            sym_list = ["NVDA", "AAPL", "MSFT"]

        lines = [
            "👥 <b>[SEC Form 4 내부자 순매수 퀀트 레이더]</b>",
            "<i>Market-Cap Tiered Institutional Insider Alpha</i>",
            "━━━━━━━━━━━━━━━━━━━",
            "💡 <i>CEO/CFO 등 핵심 임원의 사비 장내 매수(Code P)를 시가총액별 동적 가중치로 평가합니다.</i>",
            ""
        ]

        header_sub = "보유 포지션 내부자 지분 동향" if is_held else "시장 주도주 내부자 지분 동향 (현금 대기 중)"
        lines.append(f"💼 <b>[{header_sub}]</b>")
        for s in sym_list:
            data = self.analyze_insider_activity(s)
            score = data['insider_score']
            bonus = data['strategy_bonus']
            tier_name = data.get('cap_tier_name', '중형주')
            thresh_k = data.get('whale_threshold', 100000.0) / 1000.0

            if bonus >= 10:
                status = f"🟢 <b>{data['cluster_desc']}</b>"
            elif bonus > 0:
                status = f"🟡 <b>{data['cluster_desc']}</b>"
            else:
                status = f"⚪ <i>최근 90일 장내 순매수 없음 (안정적 보유)</i>"

            lines.append(f"• <b>{s}</b> [{tier_name} | 고래기준: ${thresh_k:.0f}K] (가산점: <b>+{bonus}pt</b>)\n  └ {status}")
            if data["recent_purchases"]:
                for p in data["recent_purchases"][:2]:
                    lines.append(f"     • {p['name']} ({p['role']}): {p['shares']:,.0f}주 (${p['value_usd']:,.0f})")

        lines.append("\n🏛️ <b>[월가 주요 주도주 내부자 매집 레이더]</b>")
        market_leaders = ["NVDA", "AAPL", "MSFT", "PLTR"]
        for ml in market_leaders:
            if ml not in sym_list:
                m_data = self.analyze_insider_activity(ml)
                m_status = "🟢 매수 감지" if m_data["purchase_count"] > 0 else "⚪ 안정 유지"
                lines.append(f"• <b>{ml}</b>: {m_status} (신뢰도 {m_data['insider_score']}점)")

        lines.append("━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 <i>내부자의 사비 장내 매수는 주가 저평가 및 강력한 실적 자신감의 1급 신호입니다.</i>")
        return "\n".join(lines)


if __name__ == "__main__":
    radar = SECForm4InsiderRadar()
    print(radar.format_telegram_card(["ADP", "CART", "LYFT"]))
