"""
Enhanced Dynamic Screener (KIS API Native)
============================================
Multi-factor stock screening using KIS API data.
Finviz 의존성 제거 — 한투 API 거래량순위 + OHLCV 기반 스크리닝.

Scoring Factors:
1. Volume Surge (relative volume vs 20-day average)
2. Momentum (5-day, 20-day price change)
3. Gap Analysis (today's open vs yesterday's close)
4. Technical Setup (SMA, RSI, volume trend)
5. 52-Week High Proximity
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import kis_data as yf  # KIS API drop-in replacement
import kis_data
import pandas as pd
from loguru import logger

from macro import MarketRegime
import config
import universe


class ScreenMode(Enum):
    """Screening mode"""
    SHORT_SQUEEZE = "short_squeeze"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    DEFENSIVE = "defensive"
    OVERSOLD = "oversold"


@dataclass
class StockScore:
    """Individual stock scoring result"""
    symbol: str
    total_score: int  # 0-100
    short_squeeze_score: int
    momentum_score: int
    institutional_score: int
    options_score: int
    technical_score: int
    near_52w_high: bool = False
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ScreenResult:
    """Screening result container"""
    tickers: List[str]
    scores: List[StockScore]
    mode: ScreenMode
    regime: MarketRegime
    timestamp: datetime


# ==============================================
# Universe — 거래량 상위 + 인기 종목 풀
# ==============================================

# 확장된 후보 풀 — 실거래 137건 분석 및 나스닥/S&P 대표 250+ 종목 (2026-05)
# Russell 1000 유니버스 전체(1,000+ 종목)를 실시간 후보군 스캐닝 대상으로 로드
BASE_UNIVERSE = universe.get_all_symbols()

# 방어주 별도 풀
DEFENSIVE_UNIVERSE = [
    "PG", "KO", "PEP", "JNJ", "WMT", "COST", "CL", "GIS", "K", "SJM",
    "MO", "PM", "NEE", "DUK", "SO", "ED", "AEP", "XEL", "WEC", "ES",
    "T", "VZ", "CMCSA", "BMY", "ABBV", "MRK", "PFE", "LLY", "ABT",
]


class DynamicScreener:
    """KIS API 기반 동적 스크리너"""
    
    MIN_SCORE = 45  # 유니버스 확장(250+)에 맞춰 기준 강화 (이전: 40)
    MAX_RESULTS = 10
    
    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._multi_source_hits = {}  # symbol -> set of source names
        self._ohlcv_cache = {}        # symbol -> DataFrame (TTL from gather phase)
    
    def screen(self, regime: MarketRegime = MarketRegime.RISK_ON,
               use_short_squeeze: bool = True,
               use_momentum: bool = True,
               exclude_symbols: set = None) -> ScreenResult:
        """
        Run comprehensive screening using KIS API
        
        Args:
            regime: Current market regime
            use_short_squeeze: Include short squeeze filter
            use_momentum: Include momentum filter
            exclude_symbols: 현재 보유 + 최근 거래 종목 제외 (스윙 다양성)
            
        Returns:
            ScreenResult with scored and ranked stocks
        """
        # ============================================================
        # 0. 제외 목록 구성 — 현재 보유 종목만 제외 (단타 찌꺼기 쿨다운 삭제됨)
        # ============================================================
        self._ohlcv_cache.clear()
        _exclude = set(exclude_symbols or [])

        # Determine screening mode
        if regime == MarketRegime.RISK_OFF:
            # During RISK_OFF, prioritize inverse ETFs for hedging/shorting
            mode = ScreenMode.DEFENSIVE
            defensive_cands = self._screen_defensive()
            inverse_cands = self._screen_inverse()
            candidates = inverse_cands + defensive_cands
        elif regime == MarketRegime.NEUTRAL:
            mode = ScreenMode.OVERSOLD
            candidates = self._screen_oversold()
        elif use_momentum:
            mode = ScreenMode.MOMENTUM
            candidates = self._screen_squeeze_leaders()
        elif use_short_squeeze:
            mode = ScreenMode.SHORT_SQUEEZE
            candidates = self._screen_volume_surge()
        else:
            mode = ScreenMode.BREAKOUT
            candidates = self._screen_breakout()

        # ============================================================
        # [RS MOMENTUM ENGINE] 상대강도(Relative Strength) 모멘텀 랭킹
        # ============================================================
        # 30년간 학술적으로 검증된 가장 단순하고 강력한 종목 선정 기준:
        # SPY 대비 3개월 + 6개월 동안 가장 강하게 오른 종목 = 앞으로도 계속 오를 확률 최고
        # (Jegadeesh & Titman 1993 모멘텀 팩터 - 업계 표준)
        rs_top_candidates = []
        if regime != MarketRegime.RISK_OFF:  # 상승/중립장에서만 RS 모멘텀 적용
            try:
                rs_top_candidates = self._rank_by_relative_strength(exclude=_exclude)
                if rs_top_candidates:
                    logger.info("[RS_ENGINE] Relative Strength top {} stocks: {}", len(rs_top_candidates), rs_top_candidates[:10])
                    candidates = list(dict.fromkeys(rs_top_candidates + candidates))
            except Exception as rs_err:
                logger.warning("[RS_ENGINE] RS ranking failed: {}", rs_err)

        # Inject Local Smart Money candidates first (yield maximization)
        try:
            smart_money_cands = self._gather_smart_money_candidates()
            if smart_money_cands:
                logger.info("Local Smart Money Screener: Found {} candidates. Injecting.", len(smart_money_cands))
                candidates = list(dict.fromkeys(smart_money_cands + candidates))
        except Exception as sm_err:
            logger.error("Failed to inject local smart money candidates: {}", sm_err)


        # 🎯 Inject Theme Radar recommended candidates (Top picks)
        try:
            from theme_radar_adapter import ThemeRadarAdapter
            adapter = ThemeRadarAdapter()
            recs = adapter.get_recommendations()
            if recs:
                theme_cands = list(recs.keys())
                logger.info("🎯 Theme Radar: Found {} recommended candidates. Injecting at top.", len(theme_cands))
                candidates = list(dict.fromkeys(theme_cands + candidates))
        except Exception as tr_err:
            logger.error("Failed to inject theme radar candidates: {}", tr_err)

        # Dynamic Downtrend Ticker Injection (Relative Strength & Hedging)
        try:
            import kis_data as _kd
            _spy_df = _kd.get_daily_ohlcv("SPY", days=25)
            if _spy_df is not None and len(_spy_df) >= 22:
                _spy_close = _spy_df['Close']
                _spy_sma20 = float(_spy_close.rolling(20).mean().iloc[-1])
                _spy_current = float(_spy_close.iloc[-1])
                if _spy_current < _spy_sma20:
                    inverse_cands = self._screen_inverse()
                    defensive_cands = self._screen_defensive()
                    candidates = list(set(candidates + inverse_cands + defensive_cands))
                    logger.info("Downtrend detected in screener (SPY < SMA20). Injected {} inverse/defensive candidates.", len(inverse_cands) + len(defensive_cands))
        except Exception as e:
            logger.debug("Failed to inject downtrend candidates in screener: {}", e)

        # 제외 목록 적용 — 보유/최근 거래 종목 제거
        candidates = [c for c in candidates if c not in _exclude]
        if not candidates:
            # 제외 후 후보 없으면 전체 유니버스에서 제외 목록만 빼고 랜덤 선택
            import random
            fallback = [s for s in BASE_UNIVERSE if s not in _exclude]
            random.shuffle(fallback)
            candidates = fallback[:30]
            logger.warning("All candidates excluded — using shuffled fallback ({} stocks)", len(candidates))

        if not candidates:
            logger.warning("No candidates found in initial screen")
            return ScreenResult([], [], mode, regime, datetime.now())
        
        # Score each candidate using a two-pass architecture for extreme speed
        # Pass 1: Quick preliminary pass (OHLCV factors only, no slow Finnhub APIs)
        import concurrent.futures
        preliminary_scored = []
        def _safe_prelim_score(sym):
            try:
                return self._score_stock(sym, mode, preliminary=True)
            except Exception as e:
                logger.debug("Preliminary scoring failed for {}: {}", sym, e)
                return None

        # Preliminary pass workers: 8 (was 16). The Oracle VPS has 2 CPUs.
        # OHLCV downloads are I/O-bound but KIS API enforces rate limits;
        # 16 concurrent threads cause 429 bursts. 8 workers is the sweet spot.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_safe_prelim_score, sym): sym for sym in candidates[:100]}
            try:
                # Increased timeout 90s→150s: 100 candidates × KIS download.
                # Each KIS call can take up to 2-3s; at 8 workers, 100 symbols = ~37s min.
                # 150s gives 4× headroom for slow API responses on VPS.
                for future in concurrent.futures.as_completed(futures, timeout=150):
                    try:
                        result = future.result()
                        if result:
                            preliminary_scored.append(result)
                    except Exception as e:
                        logger.debug("Preliminary scoring future failed: {}", e)
            except concurrent.futures.TimeoutError:
                logger.warning("Preliminary screener scoring timed out (150s limit)")

        # Sort by preliminary score and take the top 20 for full scoring
        preliminary_scored.sort(key=lambda x: x.total_score, reverse=True)
        top_candidates = [s.symbol for s in preliminary_scored[:20]]
        
        # Pass 2: Full event-driven scoring (calls Finnhub APIs) on top 20 candidates only
        scored = []
        def _safe_full_score(sym):
            try:
                return self._score_stock(sym, mode, preliminary=False)
            except Exception as e:
                logger.debug("Full scoring failed for {}: {}", sym, e)
                return None

        if top_candidates:
            # Full scoring: max_workers=4 (was 8). Each symbol calls Finnhub (news, insider, earnings)
            # Finnhub read timeout=10s × 3 retries = up to 30s/symbol. With 8 workers, 20 symbols
            # could spike to 240 concurrent Finnhub connections causing mass timeouts.
            # 4 workers × 20 symbols = 5 batches × ~30s max = ~150s worst case.
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures2 = {executor.submit(_safe_full_score, sym): sym for sym in top_candidates}
                try:
                    # Increased timeout 120s→180s: Finnhub retries can take 30s/symbol.
                    # 4 workers × 20 symbols = ~150s max. 180s gives safe headroom.
                    for future in concurrent.futures.as_completed(futures2, timeout=180):
                        try:
                            result = future.result()
                            if result:
                                scored.append(result)
                        except Exception as e:
                            logger.debug("Full scoring future failed: {}", e)
                except concurrent.futures.TimeoutError:
                    unfinished = [futures2[f] for f in futures2 if not f.done()]
                    logger.warning("Full screener scoring timed out (180s limit). Unfinished: {}", unfinished)

        # Flush Finnhub cache to disk after batch completion
        try:
            from finnhub_client import get_finnhub_client
            get_finnhub_client().flush_cache()
        except Exception:
            pass

        # Filter candidates above MIN_SCORE
        above_min = [s for s in scored if s.total_score >= self.MIN_SCORE]
        above_min.sort(key=lambda x: x.total_score, reverse=True)

        if len(above_min) < self.MAX_RESULTS:
            # Fallback: if not enough candidates exceed MIN_SCORE, take the best fully-scored ones
            scored.sort(key=lambda x: x.total_score, reverse=True)
            top_picks = scored[:self.MAX_RESULTS]
        else:
            top_picks = above_min[:self.MAX_RESULTS]
        
        tickers = [s.symbol for s in top_picks]
        logger.info("Screen returned {} stocks (mode: {})", len(tickers), mode.value)
        
        return ScreenResult(
            tickers=tickers,
            scores=top_picks,
            mode=mode,
            regime=regime,
            timestamp=datetime.now()
        )
    
    def _rank_by_relative_strength(self, top_n: int = 30, exclude: set = None) -> List[str]:
        """
        [핵심] 상대강도(RS) 모멘텀 랭킹 엔진
        
        Jegadeesh & Titman(1993) 모멘텀 팩터 구현:
        - 3개월 + 6개월 수익률 기준 SPY 대비 상대강도 계산
        - 상위 종목 = 계속 오를 확률 가장 높음
        - 50일선 위 + 거래량 확인 필터 추가
        
        Args:
            top_n: 반환할 상위 종목 수
            exclude: 제외할 종목 집합 (현재 보유 종목 등)
        
        Returns:
            RS 상위 종목 티커 리스트 (점수 높은 순)
        """
        import kis_data
        import concurrent.futures
        import threading
        import random
        
        exclude = exclude or set()
        
        # SPY 기준 데이터 로드
        spy_ret_3m = 0.0
        spy_ret_6m = 0.0
        try:
            spy_df = kis_data.get_daily_ohlcv("SPY", days=135)
            if spy_df is not None and len(spy_df) >= 65:
                spy_ret_3m = (float(spy_df['Close'].iloc[-1]) / float(spy_df['Close'].iloc[-65]) - 1) * 100
                spy_ret_6m = (float(spy_df['Close'].iloc[-1]) / float(spy_df['Close'].iloc[0]) - 1) * 100
        except Exception:
            pass
        
        # 유니버스에서 방어주/인버스ETF 제외 (RS 모멘텀은 성장/시클리컬 섹터가 대상)
        defensive_set = {
            "KO", "PEP", "WMT", "PG", "JNJ", "MO", "PM", "SJM", "K", "GIS", "CL",
            "NEE", "DUK", "SO", "ED", "AEP", "XEL", "WEC", "ES", "EXC", "D",
            "T", "VZ", "CMCSA", "MRK", "PFE", "BMY", "ABBV",
            "SQQQ", "PSQ", "SPXU", "SH", "SDS", "SOXS", "TZA", "TECS", "FAZ"
        }
        all_symbols = [s for s in list(BASE_UNIVERSE) if s not in exclude and s not in defensive_set]
        
        # 샘플링: 최대 400종목 (API 부하 방지)
        import config as _cfg
        max_scan = min(400, getattr(_cfg, 'SCREENER_MAX_CANDIDATES', 330))
        random.shuffle(all_symbols)
        symbols_to_scan = all_symbols[:max_scan]
        
        rs_scores = []  # (symbol, rs_score)
        _lock = threading.Lock()
        
        def _compute_rs(sym: str):
            try:
                df = kis_data.get_daily_ohlcv(sym, days=135)
                if df is None or len(df) < 25:
                    return
                
                close = df['Close']
                curr = float(close.iloc[-1])
                
                # 50일 이동평균선 위에 있어야 함 (추세 확인)
                ma50 = close.rolling(50).mean()
                if len(ma50.dropna()) > 0 and curr < float(ma50.dropna().iloc[-1]):
                    return
                
                # ── [GUARD 1] RSI 과열 방지 ─────────────────────────────
                # RSI > 72면 이미 꼭대기 구간 → 진입하면 꼭대기 매수
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs_raw = gain / (loss + 1e-9)
                rsi = 100 - (100 / (1 + rs_raw))
                curr_rsi = float(rsi.iloc[-1]) if len(rsi) >= 14 else 50.0
                if curr_rsi > 72:
                    return  # 과매수 구간 — 꼭대기 매수 방지
                
                # ── [GUARD 2] 52주 고점 대비 괴리율 필터 ────────────────
                # 꼭대기(52주 고점 5% 이내) = 이미 너무 오른 것
                # 너무 내린(52주 고점 40% 이하) = 모멘텀 소멸
                # 스윗스팟: 52주 고점 대비 5~35% 아래 (오르는 중이지만 공간 있음)
                high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
                dist_from_high = (high_52w - curr) / high_52w * 100  # % below 52w high
                if dist_from_high < 3.0:
                    # 52주 신고가 3% 이내 = 완전 과열, 리스크 너무 높음
                    return
                
                # ── [GUARD 3] 어닝 블랙아웃 (7일 이내 실적발표 종목 제외) ──
                # 실적발표 전 7일은 갭하락 리스크가 가장 높은 구간
                try:
                    from finnhub_client import get_finnhub_client
                    fh = get_finnhub_client()
                    if fh.is_enabled():
                        from datetime import datetime as _dt, timedelta as _td
                        _today = _dt.now().date()
                        earnings = fh.get_earnings_calendar(sym)
                        if earnings:
                            for e in earnings:
                                edate_str = e.get('date', '')
                                if edate_str:
                                    try:
                                        edate = _dt.strptime(edate_str, '%Y-%m-%d').date()
                                        days_to_earnings = (edate - _today).days
                                        if 0 <= days_to_earnings <= 7:
                                            return  # 7일 이내 어닝 → 제외
                                    except Exception:
                                        pass
                except Exception:
                    pass  # Finnhub 없으면 생략
                
                # 3개월(약 65거래일) 수익률
                ret_3m = 0.0
                if len(close) >= 65:
                    ret_3m = (curr / float(close.iloc[-65]) - 1) * 100
                elif len(close) >= 20:
                    ret_3m = (curr / float(close.iloc[0]) - 1) * 100
                else:
                    return
                
                # 6개월(약 130거래일) 수익률
                ret_6m = 0.0
                if len(close) >= 130:
                    ret_6m = (curr / float(close.iloc[-130]) - 1) * 100
                else:
                    ret_6m = ret_3m
                
                # 거래량 확인 (20일 평균 대비 현재 거래량)
                if 'Volume' in df.columns and len(df) >= 20:
                    avg_vol = float(df['Volume'].iloc[-20:].mean())
                    curr_vol = float(df['Volume'].iloc[-1])
                    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
                    if vol_ratio < 0.5:
                        return
                
                # SPY 대비 상대강도 점수 (3M 가중치 0.6, 6M 가중치 0.4)
                rs_score = (ret_3m - spy_ret_3m) * 0.6 + (ret_6m - spy_ret_6m) * 0.4
                
                # [보너스] 52주 고점 대비 10~25% 조정된 종목에 RS 보너스 (최적 진입 구간)
                if 10 <= dist_from_high <= 25:
                    rs_score += 3.0  # 조정 후 반등 스윗스팟 보너스
                
                # SPY보다 못한 종목 제외
                if rs_score < -2.0:
                    return
                
                with _lock:
                    rs_scores.append((sym, rs_score, ret_3m, ret_6m))
                    
            except Exception:
                pass

        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            try:
                list(concurrent.futures.as_completed(
                    {executor.submit(_compute_rs, sym): sym for sym in symbols_to_scan},
                    timeout=90
                ))
            except concurrent.futures.TimeoutError:
                pass
        
        # RS 점수 기준 내림차순 정렬
        rs_scores.sort(key=lambda x: x[1], reverse=True)
        
        if rs_scores:
            top = rs_scores[:5]
            logger.info("[RS_ENGINE] Top RS stocks: " + 
                       " | ".join(f"{s}(RS:{r:.1f}, 3M:{m:.1f}%, 6M:{n:.1f}%)" 
                                  for s, r, m, n in top))
        
        return [s for s, *_ in rs_scores[:top_n]]

    # ==============================================
    # Screening Methods (KIS API 기반)
    # ==============================================
    
    def _gather_smart_money_candidates(self) -> List[str]:
        """
        [QUANT EMBEDDED] 스마트 머니 수급 스크리너 엔진 로컬 포팅 버전.
        - Russell 1000에서 거래량 급증 + 캔들 윗꼬리 필터 + EMA정배열 + 스퀴즈 충족 종목 검출.
        """
        import kis_data
        import concurrent.futures
        import threading
        import pandas as pd
        import numpy as np
        import config

        # SPY relative strength index 10d pct change
        spy_pct_10d = 0.0
        try:
            spy_df = kis_data.get_daily_ohlcv("SPY", days=20)
            if spy_df is not None and len(spy_df) >= 11:
                spy_pct_10d = ((float(spy_df['Close'].iloc[-1]) - float(spy_df['Close'].iloc[-11])) / float(spy_df['Close'].iloc[-11])) * 100
        except Exception:
            pass

        # Rolling Round-Robin scanning of the entire universe across multiple cycles to avoid KIS/Finnhub API 429
        if not hasattr(self, '_screener_offset'):
            self._screener_offset = 0
            
        all_symbols = list(BASE_UNIVERSE)
        total_count = len(all_symbols)
        max_cands = getattr(config, 'SCREENER_MAX_CANDIDATES', 330)
        
        start_idx = self._screener_offset % total_count if total_count > 0 else 0
        end_idx = start_idx + max_cands
        
        if end_idx > total_count:
            symbols_to_scan = all_symbols[start_idx:] + all_symbols[:(end_idx % total_count)]
        else:
            symbols_to_scan = all_symbols[start_idx:end_idx]
            
        self._screener_offset = (start_idx + max_cands) % total_count if total_count > 0 else 0
        logger.info("📐 Screener Rolling Scan: offset {} to {}, scanning {} symbols out of {} total universe", 
                    start_idx, end_idx % total_count if end_idx > total_count else end_idx, len(symbols_to_scan), total_count)

        passed_candidates = []
        _lock = threading.Lock()

        def _scan_symbol_smart(sym: str):
            try:
                # [ANTI-OVERLOAD] Oracle VM CPU/Network Shield
                # Staggered random start delay (0 to 0.4s) to spread CPU spikes and avoid API 429 burst limits
                import time as _time
                import random as _rand
                _time.sleep(_rand.random() * 0.4)

                # 240 days required to compute 200 SMA and weekly indicators
                df = kis_data.get_daily_ohlcv(sym, days=240)
                if df is None or len(df) < 50:
                    return

                # Cache it for score_stock step
                with _lock:
                    self._ohlcv_cache[sym] = df

                # 1. Historical data preparation
                prior_history = df.iloc[:-1]
                today_row = df.iloc[-1]
                
                # Prior average volume (20 trading days)
                prior_vol_20d = prior_history["Volume"].tail(20)
                avg_vol_20d = prior_vol_20d.mean()
                if avg_vol_20d == 0:
                    return
                    
                today_vol = float(today_row["Volume"])
                volume_ratio = today_vol / avg_vol_20d
                
                # Minimum volume ratio filter (Default 2.0x)
                if volume_ratio < 2.0:
                    return
                    
                today_close = float(today_row["Close"])
                today_open = float(today_row["Open"])
                today_high = float(today_row["High"])
                today_low = float(today_row["Low"])
                
                # Price check (minimum 2.0$, max 500$)
                if not (2.0 <= today_close <= 500.0):
                    return

                # Price Change (must be +1.5% to +15.0% to capture explosive breakout leaders)
                yesterday_close = float(prior_history["Close"].iloc[-1])
                pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
                
                # Churning/Distribution Filter:
                # Reject if volume is high (>=3x) but price progress is flat (<1.5%)
                if volume_ratio >= 3.0 and pct_change < 1.5:
                    return

                if not (1.5 <= pct_change <= 15.0):
                    return

                # Transaction value check (min $3M)
                trans_value = today_close * today_vol
                if trans_value < 3000000:
                    return

                # Closing range (Close-to-High Ratio: >= 0.60, top 40% of bar)
                high_low_range = today_high - today_low
                closing_range = (today_close - today_low) / high_low_range if high_low_range != 0 else 0.5
                if closing_range < 0.60:
                    return

                # Faded Gap-Up Filter:
                # If gap-up > 3.0% but closed lower than open
                gap_pct = ((today_open - yesterday_close) / yesterday_close) * 100
                if gap_pct > 3.0 and today_close < today_open:
                    return

                # Relative Strength vs SPY (10-day):
                stock_close_10d = float(df["Close"].iloc[-11]) if len(df) >= 11 else float(df["Close"].iloc[0])
                stock_pct_10d = ((today_close - stock_close_10d) / stock_close_10d) * 100
                rs_10d = stock_pct_10d - spy_pct_10d
                if rs_10d < -5.0:
                    return

                # 2. Moving Average Calculations (5-EMA, 20-EMA, 200-SMA)
                full_close = df["Close"]
                ema5 = full_close.ewm(span=5, adjust=False).mean()
                ema20 = full_close.ewm(span=20, adjust=False).mean()
                sma200 = full_close.rolling(window=200).mean()
                
                today_ema5 = float(ema5.iloc[-1])
                today_ema20 = float(ema20.iloc[-1])
                today_sma200 = float(sma200.iloc[-1]) if len(sma200) >= 200 else today_ema20 * 0.9  # fallback

                # [Quant-Regime Tuning] Perfect Trend alignment constraint relaxed for Early Breakout Alpha
                # Traditional: today_ema5 > today_ema20 > today_sma200
                # Eased: Require perfect alignment OR active bull breakout (ema5 > ema20 AND close > sma200)
                is_aligned = today_ema5 > today_ema20 > today_sma200
                is_early_breakout = (today_ema5 > today_ema20) and (today_close > today_sma200)
                if not (is_aligned or is_early_breakout):
                    return
                
                # Close price relative to 20-EMA
                if today_close <= today_ema20:
                    return
                    
                dist_from_ema20 = ((today_close - today_ema20) / today_ema20) * 100
                if dist_from_ema20 > 12.0:  # [FIX] 5% -> 12%: 모멘텀이 강한 성장주는 EMA20 위 8~12%도 정상
                    return
                
                # 3. Consolidation Squeeze Volatility
                # [CRITICAL FIX] 1.8% 제한 삭제 → 성장주(NVDA, META 등) ATR 2~4% 정상 진동폭 허용
                # 구) 1.8% 제한 = 담배, 코카콜라, 유틸리티 자연선택 -> 폼프/잡주 주식만 5% 이상으로 차단
                prior_close = prior_history["Close"].tail(20)
                daily_returns = prior_close.pct_change().dropna()
                prior_volatility = float(daily_returns.std() * 100)
                if prior_volatility > 5.0:  # 극단적 포지/턌니주식만 제외, 일반 성장주 수용
                    return
                
                # 4. Breakouts & Crosses
                prior_high_20d = float(prior_history["High"].tail(20).max())
                is_breakout_20d = today_close > prior_high_20d
                
                # 5/20 EMA Golden Cross (within last 3 days)
                is_golden_cross = False
                for i in range(-1, -4, -1):
                    if i >= -len(ema5):
                        past_ema5 = ema5.iloc[i]
                        past_ema20 = ema20.iloc[i]
                        prev_ema5 = ema5.iloc[i-1] if i-1 >= -len(ema5) else past_ema5
                        prev_ema20 = ema20.iloc[i-1] if i-1 >= -len(ema20) else past_ema20
                        if past_ema5 > past_ema20 and prev_ema5 <= prev_ema20:
                            is_golden_cross = True
                            break

                # 5. Early Influx Scoring (100 points maximum)
                # A. Volume Breakout (30 pts)
                vol_pts = 0
                if 2.0 <= volume_ratio < 3.0:
                    vol_pts = 15 + (volume_ratio - 2.0) * 15
                elif 3.0 <= volume_ratio <= 6.0:
                    vol_pts = 30
                elif volume_ratio > 6.0:
                    vol_pts = max(20, 30 - (volume_ratio - 6.0) * 2)
                    
                # B. Price Sweet Spot (20 pts)
                price_pts = 0
                if 1.5 <= pct_change <= 5.0:
                    price_pts = 20
                elif 5.0 < pct_change <= 8.0:
                    price_pts = 20 - (pct_change - 5.0) * 2
                else:
                    price_pts = 10
                    
                # C. Squeeze Volatility (25 pts)
                squeeze_pts = 0
                if prior_volatility < 1.5:
                    squeeze_pts = 25
                elif 1.5 <= prior_volatility < 2.5:
                    squeeze_pts = 25 - (prior_volatility - 1.5) * 25
                    
                # D. Technical Setup (25 pts)
                tech_pts = 0
                if dist_from_ema20 <= 3.0:
                    tech_pts += 15
                elif 3.0 < dist_from_ema20 <= 8.0:
                    tech_pts += max(5, 15 - int(dist_from_ema20 - 3.0) * 2)
                else:
                    tech_pts += 3
                    
                breakout_pts = 0
                if is_golden_cross:
                    breakout_pts = 10
                elif is_breakout_20d:
                    breakout_pts = 5
                    
                tech_pts += breakout_pts
                tech_pts = min(25, tech_pts)
                
                total_score = vol_pts + price_pts + squeeze_pts + tech_pts
                
                # Minimum 70 points to pass as high confidence Smart Money target
                if total_score >= 70:
                    with _lock:
                        passed_candidates.append((sym, total_score))
            except Exception:
                pass

        # Concurrent scan using 8 threads (VM safe)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(_scan_symbol_smart, symbols_to_scan)
            
        passed_candidates.sort(key=lambda x: x[1], reverse=True)
        results = [x[0] for x in passed_candidates]
        return results

    def _gather_squeeze_candidates(self) -> List[str]:
        """
        BB Squeeze + SPY 상대강도 기반 후보 종목 수집 (병렬 처리 v2).
        '이미 올라간 종목'이 아닌 '아직 안 올라간 종목' 중 컨디션 좋은 것을 선별.
        """
        import kis_data
        from indicators import calculate_bb_squeeze, calculate_relative_strength
        import config
        import concurrent.futures
        import threading

        squeeze_scores = []  # (symbol, score)
        _lock = threading.Lock()

        # SPY 일봉 데이터 (상대강도 계산용)
        spy_close = None
        try:
            spy_df = kis_data.get_daily_ohlcv("SPY", days=30)
            if spy_df is not None and len(spy_df) >= 6:
                spy_close = spy_df['Close']
        except Exception:
            pass

        # 후보 풀: BASE_UNIVERSE 전체 (최대 SCREENER_MAX_CANDIDATES개 — API 과부하 방지)
        # ⚠️ 반드시 shuffle! 알파벳 정렬이면 항상 A~D만 스캔됨
        import random
        all_symbols = list(BASE_UNIVERSE)
        random.shuffle(all_symbols)
        candidates = all_symbols[:config.SCREENER_MAX_CANDIDATES]

        def _scan_symbol(sym: str):
            """단일 종목 BB Squeeze 스캔 (스레드 워커)"""
            try:
                df = kis_data.get_daily_ohlcv(sym, days=120)  # 120d: squeeze + score 모두 활용
                if df is None or len(df) < 25:
                    return

                # 캐시에 저장 (scoring 단계에서 재사용 → 중복 API 호출 제거)
                with _lock:
                    self._ohlcv_cache[sym] = df

                # BB Squeeze 계산
                sq = calculate_bb_squeeze(
                    df,
                    lookback=config.SQUEEZE_LOOKBACK,
                    threshold=config.SQUEEZE_THRESHOLD
                )

                # 스퀴즈 상태가 아니면 스킵
                if not sq['is_squeezing']:
                    return

                score = 0

                # 스퀴즈 해제 시작 → 강한 진입 신호
                if sq['is_releasing']:
                    score += 40
                else:
                    score += 20  # 응축 중 (대기)

                # 방향이 UP이면 보너스
                if sq['direction'] == 'UP':
                    score += 15

                # 밴드폭 분위가 낮을수록 더 강한 스퀴즈 → 보너스
                score += int((1 - sq['bandwidth_pct']) * 20)

                # SPY 상대강도 (최근 5일)
                if spy_close is not None:
                    rs = calculate_relative_strength(df['Close'], spy_close, period=5)
                    if rs > 2.0:
                        score += 15   # SPY 대비 강세
                    elif rs > 0:
                        score += 7
                    elif rs < -3.0:
                        score -= 10   # 약세

                # 일봉 상승추세 확인 (SMA20 > SMA50)
                sma20 = df['Close'].rolling(20).mean().iloc[-1]
                sma50 = df['Close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else sma20
                if sma20 > sma50:
                    score += 10

                # 현재 RSI 적정 범위 (30~65: 과매도/과매수 아닌 것)
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs_val = gain / loss.replace(0, 1)
                rsi = float((100 - (100 / (1 + rs_val))).iloc[-1])
                if 30 <= rsi <= 65:
                    score += 10
                elif rsi > 75 or rsi < 20:
                    score -= 15  # 극단적 RSI → 제외

                with _lock:
                    squeeze_scores.append((sym, score))

            except Exception as e:
                logger.debug("Squeeze scan failed for {}: {}", sym, e)

        # 병렬 실행 (8 workers — VPS 2 CPU 기준 최적값, KIS API rate limit 고려)
        import sys
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        try:
            futures = {executor.submit(_scan_symbol, sym): sym for sym in candidates}
            concurrent.futures.wait(futures, timeout=150)  # 최대 2.5분
        finally:
            if sys.version_info >= (3, 9):
                executor.shutdown(wait=False, cancel_futures=True)
            else:
                executor.shutdown(wait=False)

        # 점수 높은 순 정렬
        squeeze_scores.sort(key=lambda x: x[1], reverse=True)

        result = [s[0] for s in squeeze_scores]
        if squeeze_scores:
            top5 = squeeze_scores[:5]
            logger.info("Squeeze candidates top5 (parallel scan {}): {}",
                        len(candidates), [(s, sc) for s, sc in top5])

        return result

    def _gather_multi_source_candidates(self) -> List[str]:
        """5개 KIS API 멀티소스 후보 수집 + 멀티소스 카운트"""
        self._multi_source_hits = {}
        
        def _add_from_source(items: List[Dict], source_name: str):
            for item in items:
                sym = item.get("symbol", "")
                if sym:
                    if sym not in self._multi_source_hits:
                        self._multi_source_hits[sym] = set()
                    self._multi_source_hits[sym].add(source_name)
        
        # Source 1: 거래량순위
        try:
            vol_rank = kis_data.get_volume_rank("NAS", min_price=5.0, top_n=50) # increased
            _add_from_source(vol_rank, "volume_rank")
            for ex in ["NYS", "AMS"]:
                extra = kis_data.get_volume_rank(ex, min_price=5.0, top_n=20) # increased
                _add_from_source(extra, "volume_rank")
        except Exception as e:
            logger.debug("Volume rank API error: {}", e)
        
        # Source 2: 가격급등
        try:
            surge = kis_data.get_price_surge("NAS", sort="1", top_n=30) # increased
            _add_from_source(surge, "price_surge")
        except Exception as e:
            logger.debug("Price surge API error: {}", e)
        
        # Source 3: 거래량급증
        try:
            vol_surge = kis_data.get_volume_surge("NAS", top_n=30) # increased
            _add_from_source(vol_surge, "volume_surge")
        except Exception as e:
            logger.debug("Volume surge API error: {}", e)
        
        # Source 4: 체결강도
        try:
            buy_str = kis_data.get_buy_strength_rank("NAS", top_n=30) # increased
            _add_from_source(buy_str, "buy_strength")
        except Exception as e:
            logger.debug("Buy strength API error: {}", e)
        
        # Source 5: 신고가
        try:
            new_highs = kis_data.get_new_highs_lows("NAS", sort="1", top_n=30) # increased
            _add_from_source(new_highs, "new_high")
        except Exception as e:
            logger.debug("New highs API error: {}", e)
        
        # 멀티소스 히트 카운팅 정렬 (많이 겹칠수록 높은 우선순위)
        ranked = sorted(
            self._multi_source_hits.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        result = [sym for sym, sources in ranked]
        
        multi_hit = [(sym, len(src)) for sym, src in ranked if len(src) >= 2]
        if multi_hit:
            logger.info("Multi-source hits: {}", multi_hit[:10])
        
        return result


    def _screen_volume_surge(self) -> List[str]:
        """거래량 급증 종목 스크리닝 (5개 KIS API 멀티소스)"""
        try:
            candidates = self._gather_multi_source_candidates()
            
            # 1단계 가벼운 가격 필터 (페니 주식 제외)
            filtered = []
            for sym in candidates[:200]: # 검사 풀 엄청나게 확대
                try:
                    p_data = kis_data.get_current_price(sym)
                    if p_data and p_data.get("last", 0) > 3.0:
                        filtered.append(sym)
                except Exception:
                    continue
            
            # 부족할 경우 BASE_UNIVERSE에서 보충
            if len(filtered) < 20:
                more_candidates = [c for c in BASE_UNIVERSE if c not in filtered]
                filtered.extend(more_candidates[:30])
            
            if not filtered:
                logger.info("All APIs returned empty, using base universe")
                filtered = list(BASE_UNIVERSE[:40])
            
            return filtered[:100] # 2단계(OHLCV) 후보 최대 100개 전달
            
        except Exception as e:
            logger.error("Volume surge screen failed: {}", e)
            return list(BASE_UNIVERSE[:30])
    
    def _screen_squeeze_leaders(self) -> List[str]:
        """
        BB Squeeze 기반 모멘텀 스크리닝.
        스퀴즈 상태 or 해제 직후 종목을 우선 선별. 고점 진입 방지.
        """
        try:
            candidates = self._gather_squeeze_candidates()

            # 부족하면 BASE_UNIVERSE를 랜덤 셔플하여 보충 (항상 같은 fallback 방지)
            if len(candidates) < 5:
                import random
                extra = [c for c in BASE_UNIVERSE if c not in candidates]
                random.shuffle(extra)  # 매번 다른 순서 → 다양성
                candidates.extend(extra[:25])
                logger.info("Squeeze candidates insufficient ({}), adding shuffled fallback",
                            len(candidates))

            return candidates[:50]  # 상위 50개를 2단계 스코어링에 전달

        except Exception as e:
            logger.error("Squeeze screen failed: {}", e)
            import random
            shuffled = list(BASE_UNIVERSE)
            random.shuffle(shuffled)
            return shuffled[:30]  # fallback도 랜덤 — 항상 같은 30개 방지
    
    def _screen_breakout(self) -> List[str]:
        """브레이크아웃 후보 -- 최근 고가 돌파 근접 (병렬 처리 v2)"""
        import concurrent.futures
        import threading
        try:
            candidates = list(self._gather_multi_source_candidates()[:150]) + list(BASE_UNIVERSE)
            # 중복 제거, 최대 200개
            candidates = list(dict.fromkeys(candidates))[:200]
            breakout_stocks = []
            _lock = threading.Lock()

            def _check_breakout(symbol: str):
                try:
                    df = kis_data.get_daily_ohlcv(symbol, days=100)
                    if df is None or len(df) < 20:
                        return
                    current = float(df["Close"].iloc[-1])
                    high_period = float(df["High"].max())
                    if high_period > 0 and (current / high_period) >= 0.92:
                        with _lock:
                            breakout_stocks.append((symbol, current / high_period))
                except Exception:
                    pass

            import sys
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            try:
                futures = {executor.submit(_check_breakout, sym): sym for sym in candidates}
                concurrent.futures.wait(futures, timeout=120)
            finally:
                if sys.version_info >= (3, 9):
                    executor.shutdown(wait=False, cancel_futures=True)
                else:
                    executor.shutdown(wait=False)

            breakout_stocks.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in breakout_stocks[:30]]

        except Exception as e:
            logger.error("Breakout screen failed: {}", e)
            return list(BASE_UNIVERSE[:30])


    def _screen_defensive(self) -> List[str]:
        """방어주 스크리닝 — RISK_OFF 시 안정적 종목"""
        try:
            candidates = list(DEFENSIVE_UNIVERSE)
            
            # Filter by positive change or small drawdown
            safe_stocks = []
            for symbol in candidates[:30]: # 풀 확장
                try:
                    price = kis_data.get_current_price(symbol)
                    if price and price.get("last", 0) > 5:
                        # 하락폭이 작은 종목 선호 (절대값)
                        safe_stocks.append((symbol, abs(price.get("rate", 0))))
                except Exception:
                    continue
            
            # Sort by lowest volatility (least price distance from 0)
            safe_stocks.sort(key=lambda x: x[1])
            return [s[0] for s in safe_stocks[:30]] # 전달 최대 30개
            
        except Exception as e:
            logger.error("Defensive screen failed: {}", e)
            return list(DEFENSIVE_UNIVERSE[:20])

    def _screen_inverse(self) -> List[str]:
        """인버스 ETF 스크리닝 — 하락장에서 자동으로 숏 포지션 탐색"""
        try:
            from config import INVERSE_ETFS
            candidates = list(INVERSE_ETFS)
            inverse_stocks = []
            
            for symbol in candidates:
                try:
                    price = kis_data.get_current_price(symbol)
                    if price and price.get("last", 0) > 5:
                        # 모멘텀이 좋은 인버스 ETF 선호
                        inverse_stocks.append((symbol, price.get("rate", 0)))
                except Exception:
                    continue
            
            inverse_stocks.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in inverse_stocks[:10]]
            
        except Exception as e:
            logger.error("Inverse screen failed: {}", e)
            return list(INVERSE_ETFS)[:5] if 'INVERSE_ETFS' in locals() else []
    
    def _screen_oversold(self) -> List[str]:
        """과매도 우량주 스크리닝 — RSI가 낮고 볼린저 밴드 하단에 위치한 종목 (병렬화 v2)"""
        import concurrent.futures
        import threading
        try:
            candidates = list(set(BASE_UNIVERSE + DEFENSIVE_UNIVERSE))
            oversold_stocks = []
            _lock = threading.Lock()
            
            def _check_oversold(symbol: str):
                try:
                    df = kis_data.get_daily_ohlcv(symbol, days=30)
                    if df is None or len(df) < 14:
                        return
                    
                    close = df['Close']
                    current_price = float(close.iloc[-1])
                    
                    # RSI 14 계산
                    delta = close.diff()
                    gain = delta.where(delta > 0, 0).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss.replace(0, 1)
                    rsi = 100 - (100 / (1 + rs)).iloc[-1]
                    
                    # 볼린저 밴드 하단
                    sma20 = close.rolling(20).mean().iloc[-1]
                    std20 = close.rolling(20).std().iloc[-1]
                    lower_bb = sma20 - (2 * std20)
                    
                    # RSI < 35 이거나 현재가가 BB 하단 근처인 종목
                    if rsi < 35 or current_price <= lower_bb * 1.02:
                        # 과매도 강도 점수 (낮을수록 좋음)
                        oversold_score = rsi + (current_price / lower_bb if lower_bb > 0 else 1) * 10
                        with _lock:
                            oversold_stocks.append((symbol, oversold_score))
                except Exception:
                    pass

            import sys
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            try:
                futures = {executor.submit(_check_oversold, sym): sym for sym in candidates[:100]}
                concurrent.futures.wait(futures, timeout=120)
            finally:
                if sys.version_info >= (3, 9):
                    executor.shutdown(wait=False, cancel_futures=True)
                else:
                    executor.shutdown(wait=False)
            
            # 점수가 낮은 순(더 과매도된 순)으로 정렬
            oversold_stocks.sort(key=lambda x: x[1])
            return [s[0] for s in oversold_stocks[:30]]
            
        except Exception as e:
            logger.error("Oversold screen failed: {}", e)
            return list(DEFENSIVE_UNIVERSE[:20])

    # ==============================================
    # Scoring Methods (KIS API data)
    # ==============================================
    
    def _score_stock(self, symbol: str, mode: ScreenMode, preliminary: bool = False) -> Optional[StockScore]:
        """Calculate comprehensive score for a stock using KIS API data"""
        try:
            # ✅ 캐시 우선 사용 — gather 단계에서 이미 다운로드한 데이터 재활용
            import kis_data
            if symbol in self._ohlcv_cache:
                hist = self._ohlcv_cache[symbol]
            else:
                hist = kis_data.download(symbol, period="1y", progress=False)
            
            if hist is None or hist.empty or len(hist) < 20:
                return None
            
            # ============================================================
            # 🔵 LIQUIDITY FILTER — 유동성 낮은 종목 제거
            # 평균 거래량 200,000 미만 → 스크리너에서 제외 (수수료/스프레드 과다)
            # ============================================================
            avg_volume_20d = float(hist['Volume'].tail(20).mean())
            if avg_volume_20d < 200_000:
                logger.debug("LIQUIDITY_FILTER: {} avg vol {:.0f} < 200k — skipped",
                             symbol, avg_volume_20d)
                return None
            
            # ============================================================
            # 📅 EARNINGS FILTER — 실적 발표 3일 이내 종목 제거
            # ============================================================
            try:
                from earnings_calendar import get_earnings_calendar
                e_info = get_earnings_calendar().check(symbol)
                if e_info.recommendation == "AVOID":
                    logger.debug("EARNINGS_FILTER: {} 실적 {}일 후 — 스크리너 제외",
                                 symbol, e_info.days_until)
                    return None
            except Exception:
                pass
            
            # Build info dict from OHLCV data (proxy for yf.Ticker.info)
            last_close = float(hist['Close'].iloc[-1])
            avg_volume = float(hist['Volume'].mean())
            current_volume = float(hist['Volume'].iloc[-1])
            price_data = kis_data.get_current_price(symbol)
            
            info = {
                'regularMarketPrice': last_close,
                'averageVolume': avg_volume,
                'volume': current_volume,
                'shortPercentOfFloat': 0,  # Not available from KIS
                'marketCap': last_close * avg_volume * 20,  # Rough estimate
            }
            if price_data:
                info['regularMarketPrice'] = price_data.get('last', last_close)
            
            details = {}
            
            # 1. Short Squeeze Score (25 pts)
            # KIS API doesn't provide short data, so score based on volatility proxy
            short_score = self._calc_short_squeeze_score(info)
            details['short_float'] = info.get('shortPercentOfFloat', 0)
            
            # 2. Momentum Score (25 pts)
            momentum_score = self._calc_momentum_score(info, hist)
            avg_vol = info.get('averageVolume', 1)
            avg_vol_10d = info.get('volume', 0)  # Use current volume as proxy
            details['rel_volume'] = avg_vol_10d / max(avg_vol, 1)
            
            # 3. Institutional Score (20 pts) — proxy via volume/price stability
            inst_score = self._calc_institutional_score(info, hist)
            details['inst_own'] = 0  # Not available from KIS
            
            # 4. Options Activity Score (15 pts) — proxy via volume spike
            options_score = self._calc_options_score(info, hist)
            details['implied_vol'] = 0  # Not available from KIS
            
            # 5. Technical Score (15 pts)
            tech_score = self._calc_technical_score(hist)
            
            # 52-week high check (approximate from available data)
            current = hist['Close'].iloc[-1]
            high_period = hist['High'].max() if len(hist) > 0 else current
            near_high = (current / high_period) >= 0.95 if high_period > 0 else False
            details['dist_from_period_high'] = (high_period - current) / high_period if high_period > 0 else 0
            
            # Bonus for mode-specific attributes
            mode_bonus = self._calc_mode_bonus(mode, short_score, momentum_score, near_high)
            
            # ★ Multi-source bonus: 여러 API 랭킹에 동시 등장
            source_count = len(self._multi_source_hits.get(symbol, set()))
            if source_count >= 4:
                multi_bonus = 15
            elif source_count >= 3:
                multi_bonus = 10
            elif source_count >= 2:
                multi_bonus = 5
            else:
                multi_bonus = 0
            
            # ============================================================
            # ============================================================
            # 📰 NEWS SENTIMENT BONUS/PENALTY (Dynamic Event-Driven Filter)
            # ============================================================
            news_bonus = 0
            news_blacklist = False
            if not preliminary:
                try:
                    from news_analyzer import get_news_analyzer
                    news_result = get_news_analyzer().analyze(symbol)
                    if news_result.sentiment_score > 80:
                        news_bonus = 25  # Blockbuster news momentum (e.g. key contract or breakthrough)
                        logger.info("🔥 [NEWS_MOMENTUM_BONUS] {} blockbuster news sentiment ({:.1f})! Applying +25 bonus.", 
                                    symbol, news_result.sentiment_score)
                    elif news_result.sentiment_score > 50:
                        news_bonus = 10
                    elif news_result.sentiment_score < -70:
                        news_blacklist = True  # Catastrophic news shock (e.g. SEC probe, FDA fail, or fraud)
                    elif news_result.sentiment_score < -40:
                        news_bonus = -15
                except Exception:
                    pass
            
            # ============================================================
            # 👔 INSIDER BUYING BONUS (+15) / SELLING PENALTY (-10)
            # ============================================================
            insider_bonus = 0
            if not preliminary:
                try:
                    from insider_tracker import get_insider_tracker
                    ins_result = get_insider_tracker().analyze(symbol)
                    if ins_result.insider_sentiment == "BUYING" and ins_result.insider_net_value > 500_000:
                        insider_bonus = 15
                    elif ins_result.insider_sentiment == "SELLING" and ins_result.insider_net_value < -2_000_000:
                        insider_bonus = -10
                except Exception:
                    pass
            
            # ============================================================
            # 📈 52주 신고가 돌파 BONUS (+20) — 가장 강한 모멘텀 알파
            # 학술 연구: 52주 신고가 돌파 후 3개월 평균 +12% 추가 상승
            # ============================================================
            high52w_bonus = 0
            try:
                _52w_high_val = float(hist['High'].max()) if len(hist) > 0 else current
                _dist = (current - _52w_high_val) / _52w_high_val if _52w_high_val > 0 else -1
                if _dist >= 0:  # 신고가 돌파
                    high52w_bonus = 20
                    logger.debug("52W_HIGH: {} 신고가 돌파 +{:.1%}", symbol, _dist)
                elif _dist >= -0.02:  # 2% 이내
                    high52w_bonus = 10
                elif _dist >= -0.05:  # 5% 이내
                    high52w_bonus = 5
            except Exception:
                pass

            # ============================================================
            # 🚀 PEAD BONUS (+15) / PEAD PANIC PENALTY (-25) — 실적 서프라이즈 vs 미스
            # earnings_analyzer.analyze() 실제 API 사용
            # ============================================================
            pead_bonus = 0
            pead_blacklist = False
            if not preliminary:
                try:
                    from earnings_analyzer import get_earnings_analyzer
                    _ea2 = get_earnings_analyzer()
                    _er = _ea2.analyze(symbol)
                    if _er is not None:
                        if isinstance(_er, dict):
                            _beat2 = (_er.get('beat_surprise', 0) or _er.get('eps_surprise_pct', 0) or
                                      _er.get('surprise_pct', 0))
                            _days2 = _er.get('days_since_earnings', 99)
                            _shock2 = _er.get('has_earnings_shock', False)
                            _shock_reason2 = _er.get('earnings_shock_reason', '')
                        else:
                            # It is an EarningsSignal dataclass object!
                            _beat2 = getattr(_er, 'last_eps_surprise', 0.0)
                            _days2 = getattr(_er, 'days_since_earnings', 99)
                            _shock2 = getattr(_er, 'has_earnings_shock', False)
                            _shock_reason2 = getattr(_er, 'earnings_shock_reason', '')
                            
                        if _shock2:
                            pead_blacklist = True
                            logger.warning("🚨 [AI_EARNINGS_SHOCK_BLACKLIST] {} completely blacklisted due to Gemini AI earnings/guidance/management shock! Reason: {}",
                                           symbol, _shock_reason2)
                        elif _beat2 > 5 and _days2 <= 30:
                            pead_bonus = 15
                            logger.debug("PEAD_BONUS screener: {} EPS beat {:.0f}%", symbol, _beat2)
                        elif _beat2 < -15 and _days2 <= 30:
                            pead_blacklist = True  # Severe PEAD earnings crash blacklist
                            logger.warning("🚨 [PEAD_SHOCK_BLACKLIST] {} catastrophic recent earnings miss of {:.1f}%! Blacklisting stock.",
                                           symbol, _beat2)
                        elif _beat2 < -5 and _days2 <= 30:
                            pead_bonus = -25  # Severe penalty for recent earnings misses
                            logger.warning("🚨 [PEAD_PANIC_PENALTY] {} recent earnings miss of {:.1f}%! Applying -25 penalty.", 
                                           symbol, _beat2)
                except Exception as e:
                    logger.error("PEAD analyzer failed for {}: {}", symbol, e)

            # ============================================================
            # 🔄 섹터 로테이션 보너스/페널티 (실시간 동적 반영)
            # 선도 섹터 종목: +15, 하락 섹터 종목: -20
            # ============================================================
            sector_bonus = 0
            try:
                from sector_rotator import get_sector_rotator as _gsr
                _sr2 = _gsr()
                _sym_etf2 = _sr2.get_sector_for_stock(symbol)
                if _sym_etf2:
                    _rankings = _sr2.analyze()
                    _rec_map = {r.etf: r.recommendation for r in _rankings}
                    _rec = _rec_map.get(_sym_etf2, 'NEUTRAL')
                    if _rec == 'OVERWEIGHT':
                        sector_bonus = 15
                    elif _rec == 'EARLY_ACCELERATION':
                        sector_bonus = 15  # Early rotation capture bonus!
                    elif _rec == 'UNDERWEIGHT':
                        sector_bonus = -20
            except Exception:
                pass

            # Theme Radar Bonus
            theme_radar_bonus = 0
            try:
                from theme_radar_adapter import ThemeRadarAdapter
                adapter = ThemeRadarAdapter()
                recs = adapter.get_recommendations()
                if symbol in recs:
                    # 탑픽 추천 종목이면 가중치 부여 (Leader Pick = +15, Setup Pick = +8)
                    theme_radar_bonus = 15 if recs[symbol]["pick_type"] == "LEADER" else 8
                    logger.info("🎯 [THEME_RADAR_BONUS] {} is a Theme Radar {}! Bonus: +{}", 
                                symbol, recs[symbol]["pick_type"], theme_radar_bonus)
            except Exception as tr_err:
                logger.debug("Failed to calculate Theme Radar bonus for {}: {}", symbol, tr_err)

            # Clamp total score between 0 and 100
            total = min(100, max(0, short_score + momentum_score + inst_score + options_score + 
                       tech_score + mode_bonus + multi_bonus + news_bonus + insider_bonus +
                       high52w_bonus + pead_bonus + sector_bonus + theme_radar_bonus))
            
            # Apply absolute News-Shock Blacklist & PEAD Shock Blacklist
            if news_blacklist or pead_blacklist:
                total = 0
                logger.warning("🚨 [BLACKLIST_FILTER] {} completely blacklisted (news_blacklist: {}, pead_blacklist: {})!",
                               symbol, news_blacklist, pead_blacklist)
            
            return StockScore(
                symbol=symbol,
                total_score=int(total),
                short_squeeze_score=short_score,
                momentum_score=momentum_score,
                institutional_score=inst_score,
                options_score=options_score,
                technical_score=tech_score,
                near_52w_high=near_high,
                details=details
            )
            
        except Exception as e:
            logger.debug("Score calculation failed for {}: {}", symbol, e)
            return None
    
    def _calc_short_squeeze_score(self, info: dict) -> int:
        """Trend Quality Score (0-25) - Repurposed for Swing
        Returns 0 since short interest is unavailable in KIS API."""
        return 0

    
    def _calc_momentum_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Swing Momentum Score (0-25)
        Rewards Relative Strength (RS), Trend Alignment, and steady momentum."""
        score = 0
        
        if len(hist) < 50:
            return 0
            
        close = hist['Close']
        
        # 1. Structural Uptrend (SMA20 > SMA50)
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        if sma20 > sma50:
            score += 10
            
            # Is SMA20 sloping up?
            if sma20 > close.rolling(20).mean().iloc[-5]:
                score += 5
                
        # 2. Medium-term momentum (20-day vs 50-day return)
        ret_20d = (close.iloc[-1] / close.iloc[-20]) - 1
        ret_50d = (close.iloc[-1] / close.iloc[-50]) - 1
        
        if ret_20d > 0.05 and ret_50d > 0.10:
            score += 10
        elif ret_20d > 0 and ret_50d > 0:
            score += 5
            
        return min(25, score)
    
    def _calc_institutional_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Institutional Accumulation Score (0-20)
        Rewards stocks where UP days have higher volume than DOWN days."""
        score = 0
        
        if len(hist) < 20:
            return 5
            
        # Accumulation / Distribution Profile over last 20 days
        recent = hist.tail(20)
        up_days = recent[recent['Close'] > recent['Open']]
        down_days = recent[recent['Close'] < recent['Open']]
        
        avg_up_vol = up_days['Volume'].mean() if not up_days.empty else 0
        avg_down_vol = down_days['Volume'].mean() if not down_days.empty else 0
        
        if avg_down_vol > 0:
            acc_ratio = avg_up_vol / avg_down_vol
            if acc_ratio > 1.5:
                score += 20
            elif acc_ratio > 1.2:
                score += 15
            elif acc_ratio > 1.05:
                score += 10
            elif acc_ratio < 0.8:
                score -= 10 # Distribution warning
                
        return min(20, max(0, score))
    
    def _calc_options_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Volatility Contraction (VCP) Score (0-15)
        Rewards tightening price action (decreasing ATR or BB width)."""
        score = 0
        
        if len(hist) < 20:
            return 0
            
        close = hist['Close']
        sma20 = close.rolling(20).mean().iloc[-1]
        std20 = close.rolling(20).std().iloc[-1]
        
        if sma20 > 0 and std20 > 0:
            bb_width = (4 * std20) / sma20
            
            # Tight BB width indicates contraction before expansion
            if bb_width < 0.05: # Very tight (<5% range)
                score += 15
            elif bb_width < 0.10:
                score += 10
            elif bb_width < 0.15:
                score += 5
                
        return min(15, score)
    
    def _calc_technical_score(self, hist: pd.DataFrame) -> int:
        """Technical setup score (0-15)"""
        score = 0
        
        if len(hist) < 20:
            return 0
        
        close = hist['Close']
        
        # Price above 20-day SMA
        sma_20 = close.rolling(20).mean().iloc[-1]
        if close.iloc[-1] > sma_20:
            score += 5
        
        # RSI in good range (40-70)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        if 40 <= rsi <= 65:
            score += 5
        elif 30 <= rsi <= 70:
            score += 3
        
        # Volume trend (increasing)
        vol_sma_5 = hist['Volume'].rolling(5).mean().iloc[-1]
        vol_sma_20 = hist['Volume'].rolling(20).mean().iloc[-1]
        if vol_sma_5 > vol_sma_20:
            score += 5
        
        return min(15, score)
    
    def _calc_mode_bonus(self, mode: ScreenMode, short_score: int, 
                         momentum_score: int, near_high: bool) -> int:
        """Bonus points based on screening mode"""
        if mode == ScreenMode.SHORT_SQUEEZE and short_score >= 15:
            return 10
        elif mode == ScreenMode.MOMENTUM and momentum_score >= 15:
            return 10
        elif mode == ScreenMode.BREAKOUT and near_high:
            return 10
        return 0


# Global instance
_screener = None

def get_screener() -> DynamicScreener:
    global _screener
    if _screener is None:
        _screener = DynamicScreener()
    return _screener


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing KIS-Native Screener...")
    
    screener = DynamicScreener()
    result = screener.screen(MarketRegime.RISK_ON, use_short_squeeze=True)
    
    print(f"\nMode: {result.mode.value}")
    print(f"Regime: {result.regime.value}")
    print(f"Found: {len(result.tickers)} stocks")
    
    print("\n" + "="*60)
    for score in result.scores:
        print(f"{score.symbol}: {score.total_score}/100")
        print(f"  Short: {score.short_squeeze_score}, Mom: {score.momentum_score}")
        print(f"  Inst: {score.institutional_score}, Opt: {score.options_score}")
        print(f"  Tech: {score.technical_score}, Near High: {score.near_52w_high}")
        print()
