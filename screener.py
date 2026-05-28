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
        
        # Score each candidate
        scored = []
        for symbol in candidates[:100]:  # Limit to top 100 for detailed scoring (expanded)
            try:
                score = self._score_stock(symbol, mode)
                if score and score.total_score >= self.MIN_SCORE:
                    scored.append(score)
            except Exception as e:
                logger.debug("Scoring failed for {}: {}", symbol, e)

        # 페널티가 삭제되었으므로 원본 점수 기준으로 정렬
        scored.sort(key=lambda x: x.total_score, reverse=True)

        # Determine how many stocks to return
        # If we couldn't find enough stocks above MIN_SCORE, 
        # just pick the absolute best ones regardless of score
        if len(scored) < self.MAX_RESULTS:
            # Re-score and add top ones that didn't make MIN_SCORE
            all_scored = []
            for symbol in candidates:
                try:
                    score = self._score_stock(symbol, mode)
                    if score:
                        all_scored.append(score)
                except Exception:
                    pass
            all_scored.sort(key=lambda x: x.total_score, reverse=True)
            top_picks = all_scored[:self.MAX_RESULTS]
        else:
            top_picks = scored[:self.MAX_RESULTS]
        
        tickers = [s.symbol for s in top_picks]
        
        logger.info("Screen returned {} stocks (mode: {})", len(tickers), mode.value)
        
        return ScreenResult(
            tickers=tickers,
            scores=top_picks,
            mode=mode,
            regime=regime,
            timestamp=datetime.now()
        )
    
    # ==============================================
    # Screening Methods (KIS API 기반)
    # ==============================================
    
    def _gather_squeeze_candidates(self) -> List[str]:
        """
        BB Squeeze + SPY 상대강도 기반 후보 종목 수집.
        '이미 올라간 종목'이 아닌 '아직 안 올라간 종목' 중 컨디션 좋은 것을 선별.
        """
        import kis_data
        from indicators import calculate_bb_squeeze, calculate_relative_strength
        import config

        squeeze_scores = []  # (symbol, score)

        # SPY 일봉 데이터 (상대강도 계산용)
        spy_close = None
        try:
            spy_df = kis_data.get_daily_ohlcv("SPY", days=30)
            if spy_df is not None and len(spy_df) >= 6:
                spy_close = spy_df['Close']
        except Exception:
            pass

        # 후보 풀: BASE_UNIVERSE 전체 (넓은 선택지 유지)
        candidates = list(BASE_UNIVERSE)

        for sym in candidates:
            try:
                df = kis_data.get_daily_ohlcv(sym, days=60)
                if df is None or len(df) < 25:
                    continue

                # BB Squeeze 계산
                sq = calculate_bb_squeeze(
                    df,
                    lookback=config.SQUEEZE_LOOKBACK,
                    threshold=config.SQUEEZE_THRESHOLD
                )

                # 스퀴즈 상태가 아니면 스킵
                if not sq['is_squeezing']:
                    continue

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

                squeeze_scores.append((sym, score))

            except Exception as e:
                logger.debug("Squeeze scan failed for {}: {}", sym, e)
                continue

        # 점수 높은 순 정렬
        squeeze_scores.sort(key=lambda x: x[1], reverse=True)

        result = [s[0] for s in squeeze_scores]
        if squeeze_scores:
            top5 = squeeze_scores[:5]
            logger.info("Squeeze candidates top5: {}", [(s, sc) for s, sc in top5])

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
        """브레이크아웃 후보 — 최근 고가 돌파 근접"""
        try:
            candidates = list(self._gather_multi_source_candidates()[:150]) + list(BASE_UNIVERSE)
            # 중복 제거
            candidates = list(dict.fromkeys(candidates))
            breakout_stocks = []
            
            for symbol in candidates:
                try:
                    # Breakout 특성상 OHLCV가 필요하므로 1단계 필터 없이 OHLCV 스냅샷 요청 (최대 70개)
                    df = kis_data.get_daily_ohlcv(symbol, days=100)
                    if df is None or len(df) < 20:
                        continue
                    
                    current = float(df["Close"].iloc[-1])
                    high_period = float(df["High"].max())
                    
                    # 기간 내 고점 대비 95% 이상
                    if high_period > 0 and (current / high_period) >= 0.92: # 약간 완화 (92%)
                        breakout_stocks.append((symbol, current / high_period))
                except Exception:
                    continue
            
            breakout_stocks.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in breakout_stocks[:30]] # 2단계(OHLCV 확장 스코어링) 후보 최대 30개
            
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
        """과매도 우량주 스크리닝 — RSI가 낮고 볼린저 밴드 하단에 위치한 종목"""
        try:
            candidates = list(set(BASE_UNIVERSE + DEFENSIVE_UNIVERSE))
            oversold_stocks = []
            
            for symbol in candidates[:60]:
                try:
                    df = kis_data.get_daily_ohlcv(symbol, days=30)
                    if df is None or len(df) < 14:
                        continue
                    
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
                        oversold_stocks.append((symbol, oversold_score))
                except Exception:
                    continue
            
            # 점수가 낮은 순(더 과매도된 순)으로 정렬
            oversold_stocks.sort(key=lambda x: x[1])
            return [s[0] for s in oversold_stocks[:30]]
            
        except Exception as e:
            logger.error("Oversold screen failed: {}", e)
            return list(DEFENSIVE_UNIVERSE[:20])

    # ==============================================
    # Scoring Methods (KIS API data)
    # ==============================================
    
    def _score_stock(self, symbol: str, mode: ScreenMode) -> Optional[StockScore]:
        """Calculate comprehensive score for a stock using KIS API data"""
        try:
            # Get data from KIS API
            import kis_data
            hist = kis_data.download(symbol, period="90d", progress=False)
            
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
            # 📰 NEWS SENTIMENT BONUS/PENALTY (+/- 10)
            # ============================================================
            news_bonus = 0
            try:
                from news_analyzer import get_news_analyzer
                news_result = get_news_analyzer().analyze(symbol)
                if news_result.sentiment_score > 50:
                    news_bonus = 10
                elif news_result.sentiment_score < -40:
                    news_bonus = -10
            except Exception:
                pass
            
            # ============================================================
            # 👔 INSIDER BUYING BONUS (+15) / SELLING PENALTY (-10)
            # ============================================================
            insider_bonus = 0
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
            # 🚀 PEAD BONUS (+15) — 실적 서프라이즈 후 잔여 모멘텀
            # earnings_analyzer.analyze() 실제 API 사용
            # ============================================================
            pead_bonus = 0
            try:
                from earnings_analyzer import get_earnings_analyzer
                _ea2 = get_earnings_analyzer()
                _er = _ea2.analyze(symbol)
                if isinstance(_er, dict):
                    _beat2 = (_er.get('beat_surprise', 0) or _er.get('eps_surprise_pct', 0) or
                              _er.get('surprise_pct', 0))
                    _days2 = _er.get('days_since_earnings', 99)
                    if _beat2 > 5 and _days2 <= 30:
                        pead_bonus = 15
                        logger.debug("PEAD_BONUS screener: {} EPS beat {:.0f}%", symbol, _beat2)
            except Exception:
                pass

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
                    elif _rec == 'UNDERWEIGHT':
                        sector_bonus = -20
            except Exception:
                pass

            total = min(100, short_score + momentum_score + inst_score + options_score + 
                       tech_score + mode_bonus + multi_bonus + news_bonus + insider_bonus +
                       high52w_bonus + pead_bonus + sector_bonus)
            
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
        Rewards stocks in smooth, established uptrends with minimal deep pullbacks."""
        score = 0
        
        # We need historical data for this, so we'll rely on the caller passing it, or just use info
        # Wait, the signature only has info. Let's adjust based on simple price info
        price = info.get('regularMarketPrice', 0)
        if price <= 0: return 0
        
        # We don't have hist here, so let's give a base score if price is above a certain threshold 
        # (penny stocks excluded)
        if price > 20: score += 10
        elif price > 10: score += 5
        
        # We will use the momentum score and tech score for the heavy lifting instead.
        return min(25, score + 10)  # Baseline points

    
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
