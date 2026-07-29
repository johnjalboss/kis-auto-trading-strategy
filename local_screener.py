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

# 기본 후보 풀 (대형 모멘텀 + 인기 유망 종목 + AI 인프라)
BASE_UNIVERSE = [
    # 대형 기술주 (유동성/안정성 검증)
    "AAPL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "AMD", "AVGO",
    "CRM", "ORCL", "ADBE", "NFLX", "SHOP", "SNOW", "INTC", "TXN", "NXPI",
    # 반도체 및 하드웨어
    "MU", "LRCX", "KLAC", "ASML", "QCOM", "ARM", "ON", "WDC", "STX", "SMCI", "ANET",
    # AI/Software/Cloud
    "PLTR", "MSTR", "COIN", "IONQ", "RGTI", "RKLB", "SOFI", "HOOD",
    "CELH", "DUOL", "DDOG", "CRWD", "ZS", "NET", "MDB", "PANW", "VRT",
    "VST", "DELL", "HPE", "AI", "NOW", "WDAY", "SNPS", "CDNS", "FTNT",
    # 바이오/헬스케어 (변동성 관리)
    "MRNA", "GILD", "AMGN", "VRTX", "ISRG", "DXCM", "PODD", "REGN", "ABBV", "BMY",
    # 금융/핀테크
    "JPM", "GS", "V", "MA", "AFRM", "UPST", "NU", "AXP", "BAC", "WFC", "C", "MS", "COF", "SQ",
    # 에너지/원자재
    "XOM", "CVX", "FANG", "BKR", "COP", "SLB",
    # 경기소비재/여행
    "NKE", "SBUX", "MCD", "DIS", "ABNB", "UBER", "LULU", "RCL", "CCL", "DKNG", "HD", "LOW",
    # 산업재/우주항공
    "FSLR", "ENPH", "GE", "CAT", "BA", "LMT", "RTX", "HON", "MMM",
    # 방어주/필수소비재
    "PG", "KO", "PEP", "JNJ", "WMT", "COST",
    # 리츠 (Real Estate 선도 섹터)
    "AMT", "PLD", "EQIX", "VTR",
    # 인버스 ETF (하락장 대비)
    "SQQQ", "SOXS", "SPXU",
]

# 방어주 별도 풀
DEFENSIVE_UNIVERSE = [
    "PG", "KO", "PEP", "JNJ", "WMT", "COST", "CL", "GIS", "K", "SJM",
    "MO", "PM", "NEE", "DUK", "SO", "ED", "AEP", "XEL", "WEC", "ES",
    "T", "VZ", "CMCSA", "BMY", "ABBV", "MRK", "PFE", "LLY", "ABT",
    # 인버스 ETF
    "SQQQ", "SOXS", "SPXU", "PSQ", "SH",
]


class DynamicScreener:
    """KIS API 기반 동적 스크리너"""
    
    MIN_SCORE = 40
    MAX_RESULTS = 10
    
    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._multi_source_hits = {}  # symbol -> set of source names
    
    def screen(self, regime: MarketRegime = MarketRegime.RISK_ON,
               use_short_squeeze: bool = True,
               use_momentum: bool = True) -> ScreenResult:
        """
        Run comprehensive screening using KIS API
        
        Args:
            regime: Current market regime
            use_short_squeeze: Include short squeeze filter
            use_momentum: Include momentum filter
            
        Returns:
            ScreenResult with scored and ranked stocks
        """
        # Determine screening mode
        if regime == MarketRegime.RISK_OFF:
            mode = ScreenMode.DEFENSIVE
            candidates = self._screen_defensive()
        elif regime == MarketRegime.NEUTRAL:
            mode = ScreenMode.OVERSOLD
            candidates = self._screen_oversold()
        elif use_momentum:
            mode = ScreenMode.MOMENTUM
            candidates = self._screen_momentum()
        elif use_short_squeeze:
            mode = ScreenMode.SHORT_SQUEEZE
            candidates = self._screen_volume_surge()
        else:
            mode = ScreenMode.BREAKOUT
            candidates = self._screen_breakout()
        
        if not candidates:
            logger.warning("No candidates found in initial screen")
            return ScreenResult([], [], mode, regime, datetime.now())
        
        # Score each candidate
        scored = []
        for symbol in candidates[:30]:  # Limit to top 30 for detailed scoring (expanded)
            try:
                score = self._score_stock(symbol, mode)
                if score and score.total_score >= self.MIN_SCORE:
                    scored.append(score)
            except Exception as e:
                logger.debug("Scoring failed for {}: {}", symbol, e)
        
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
    
    def _gather_multi_source_candidates(self) -> List[str]:
        """5개 KIS API 랭킹 소스에서 후보 종목 수집 + 멀티소스 카운트"""
        self._multi_source_hits = {}
        
        def _add_from_source(items: List[Dict], source_name: str):
            for item in items:
                sym = item.get("symbol", "")
                if sym:
                    if sym not in self._multi_source_hits:
                        self._multi_source_hits[sym] = set()
                    self._multi_source_hits[sym].add(source_name)
        
        # Source 1: 거래량순위 (기존)
        try:
            vol_rank = kis_data.get_volume_rank("NAS", min_price=5.0, top_n=50) # increased
            _add_from_source(vol_rank, "volume_rank")
            for ex in ["NYS", "AMS"]:
                extra = kis_data.get_volume_rank(ex, min_price=5.0, top_n=20) # increased
                _add_from_source(extra, "volume_rank")
        except Exception as e:
            logger.debug("Volume rank API error: {}", e)
        
        # Source 2: 가격급등락
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
        
        # Source 4: 매수체결강도상위
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
        
        # 멀티소스 히트 수로 정렬 (여러 랭킹에 등장 = 높은 확신)
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
            for sym in candidates[:60]: # 검사 풀 확대
                try:
                    p_data = kis_data.get_current_price(sym)
                    if p_data and p_data.get("last", 0) > 5.0:
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
            
            return filtered[:40] # 2단계(OHLCV) 후보 최대 40개 전달
            
        except Exception as e:
            logger.error("Volume surge screen failed: {}", e)
            return list(BASE_UNIVERSE[:30])
    
    def _screen_momentum(self) -> List[str]:
        """모멘텀 종목 스크리닝 — 멀티소스 + 가격 상승 필터"""
        try:
            candidates = self._gather_multi_source_candidates()
            
            # Also add base universe for breadth
            all_candidates = list(set(candidates + list(BASE_UNIVERSE)))
            
            # 1단계 필터: Price > 5, 모멘텀(일반/보너스) 감안
            momentum_stocks = []
            for symbol in all_candidates[:80]: # 검사 풀 크게 확장
                try:
                    price = kis_data.get_current_price(symbol)
                    if price and price.get("rate", 0) > -2 and price.get("last", 0) > 5:
                        # Multi-source 보너스: 더 많은 API에 등장 = 높은 점수
                        source_count = len(self._multi_source_hits.get(symbol, set()))
                        adj_rate = price.get("rate", 0) + source_count * 2.5
                        momentum_stocks.append((symbol, adj_rate, price.get("tvol", 0)))
                except Exception:
                    continue
            
            # Sort by adjusted rate (descending)
            momentum_stocks.sort(key=lambda x: x[1], reverse=True)
            
            return [s[0] for s in momentum_stocks[:40]] # 2단계(OHLCV) 후보 최대 40개
            
        except Exception as e:
            logger.error("Momentum screen failed: {}", e)
            return list(BASE_UNIVERSE[:30])
    
    def _screen_breakout(self) -> List[str]:
        """브레이크아웃 후보 — 최근 고가 돌파 근접"""
        try:
            candidates = list(BASE_UNIVERSE[:70]) # 풀 확장
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
        """방어주 스크리닝 — RISK_OFF 시 안정적 종목 + 인버스 ETF"""
        try:
            import config
            defensive_pool = list(DEFENSIVE_UNIVERSE)
            inverse_pool = list(getattr(config, 'INVERSE_ETFS', []))
            
            scored_stocks = []
            
            # 1. 방어주 채점 (변동성이 적고 안정적인 종목)
            for symbol in defensive_pool:
                try:
                    price = kis_data.get_current_price(symbol)
                    if price and price.get("last", 0) > 10.0:
                        # 방어주는 변동성 낮을수록 좋음 (절대값 작을수록 가산점)
                        score = 100 - min(100, abs(price.get("rate", 0)) * 10)
                        scored_stocks.append((symbol, score))
                except Exception:
                    continue
            
            # [신규] 섹터 모멘텀 분석 (가장 약한 섹터의 인버스 우선)
            sector_scores = {}
            for sector, symbol in [("Nasdaq", "QQQ"), ("Semis", "SOXX"), ("S&P500", "SPY")]:
                try:
                    df_s = kis_data.get_daily_ohlcv(symbol, days=10)
                    if df_s is not None:
                        sector_scores[sector] = (float(df_s['Close'].iloc[-1]) / float(df_s['Close'].iloc[-5]) - 1) * 100
                except: continue
            
            # [신규] 인버스 ETF 채점 (하락장에서 상승 중인 종목 우선 + 섹터 가중치 + 거래량 필터)
            for symbol in inverse_pool:
                try:
                    # 거래대금 필터 (최소 $100M 5일 평균 - 유동성 확보)
                    stats = kis_data.get_current_price(symbol)
                    if stats is None: continue
                    
                    # 5일 평균 거래대금 근사치 계산
                    df_vol = kis_data.get_daily_ohlcv(symbol, days=5)
                    if df_vol is not None:
                        avg_vol_dollar = (df_vol['Close'] * df_vol['Volume']).mean()
                        if avg_vol_dollar < 100_000_000: # $100M 미만 제외
                            logger.debug(f"Skipping {symbol}: Low liquidity (${avg_vol_dollar/1e6:.1f}M)")
                            continue

                    price = stats.get("last", 0)
                    if price > 5.0:
                        rate = stats.get("rate", 0)
                        
                        # 과열 방지: 최근 5일간 이미 10% 이상 급등한 경우 제외
                        if df_vol is not None and len(df_vol) >= 5:
                            ret_5d = (float(df_vol['Close'].iloc[-1]) / float(df_vol['Close'].iloc[-5]) - 1) * 100
                            if ret_5d > 10.0:
                                logger.debug(f"Skipping {symbol}: 5D rally too high ({ret_5d:.1f}%)")
                                continue

                        # 섹터 가중치 적용
                        sector_bonus = 0
                        if "SOXS" in symbol and sector_scores.get("Semis", 0) < -3:
                            sector_bonus = 15
                        elif "SQQQ" in symbol and sector_scores.get("Nasdaq", 0) < -3:
                            sector_bonus = 10
                        
                        # 최종 점수 산출
                        score = 80 + (rate * 5) + sector_bonus if rate > 0 else 40 + rate + sector_bonus
                        scored_stocks.append((symbol, score))
                except Exception:
                    continue
            
            # 점수 높은 순으로 정렬
            scored_stocks.sort(key=lambda x: x[1], reverse=True)
            
            logger.info("Defensive/Inverse screen found {} candidates", len(scored_stocks))
            return [s[0] for s in scored_stocks[:40]]
            
        except Exception as e:
            logger.error("Defensive screen failed: {}", e)
            return list(DEFENSIVE_UNIVERSE[:20])
    
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
            
            total = min(100, short_score + momentum_score + inst_score + options_score + tech_score + mode_bonus + multi_bonus)
            
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
        """Short squeeze potential (0-25)
        KIS API doesn't provide short float data, so we use volume-based proxy"""
        score = 0
        
        # Volume surge as proxy for short squeeze potential
        vol = info.get('volume', 0) or 0
        avg_vol = info.get('averageVolume', 1) or 1
        
        if avg_vol > 0:
            vol_ratio = vol / avg_vol
            if vol_ratio > 5:
                score += 15
            elif vol_ratio > 3:
                score += 10
            elif vol_ratio > 2:
                score += 7
            elif vol_ratio > 1.5:
                score += 4
        
        # Price change as additional signal
        change_pct = abs(info.get('regularMarketChangePercent', 0) or 0)
        if change_pct > 10:
            score += 10
        elif change_pct > 5:
            score += 7
        elif change_pct > 3:
            score += 4
        
        return min(25, score)
    
    def _calc_momentum_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Momentum score (0-25)"""
        score = 0
        
        # Relative volume
        avg_vol = info.get('averageVolume', 1) or 1
        current_vol = info.get('volume', 0) or 0
        if avg_vol > 0:
            rel_vol = current_vol / avg_vol
            if rel_vol > 2:
                score += 10
            elif rel_vol > 1.5:
                score += 7
            elif rel_vol > 1.2:
                score += 4
        
        # Price momentum (5-day)
        if len(hist) >= 5:
            mom_5d = (hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]
            if mom_5d > 0.10:
                score += 10
            elif mom_5d > 0.05:
                score += 7
            elif mom_5d > 0.02:
                score += 4
        
        # Gap check
        if len(hist) >= 2:
            gap = (hist['Open'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]
            if gap > 0.05:
                score += 5
            elif gap > 0.02:
                score += 3
        
        return min(25, score)
    
    def _calc_institutional_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Institutional activity proxy score (0-20)
        KIS doesn't provide institutional data, use volume consistency as proxy"""
        score = 0
        
        if len(hist) < 20:
            return 5  # 기본 점수
        
        # 거래량 안정성 (기관 매매 특성: 일정한 거래량)
        vol_cv = hist["Volume"].std() / max(hist["Volume"].mean(), 1)
        if vol_cv < 0.5:  # Low coefficient of variation = institutional
            score += 12
        elif vol_cv < 1.0:
            score += 8
        elif vol_cv < 1.5:
            score += 4
        
        # 가격 안정성 (큰 변동 없이 상승 = 기관 매집)
        daily_returns = hist["Close"].pct_change().dropna()
        if len(daily_returns) > 0:
            mean_return = daily_returns.mean()
            if mean_return > 0 and daily_returns.std() < 0.03:
                score += 8
            elif mean_return > 0:
                score += 4
        
        return min(20, score)
    
    def _calc_options_score(self, info: dict, hist: pd.DataFrame) -> int:
        """Options activity proxy score (0-15)
        Uses volume spikes as proxy for unusual options activity"""
        score = 0
        
        # High volume days (unusual activity proxy)
        if len(hist) >= 10:
            vol_std = hist['Volume'].std()
            vol_mean = hist['Volume'].mean()
            recent_vol = hist['Volume'].iloc[-1]
            
            if vol_mean > 0 and vol_std > 0:
                z_score = (recent_vol - vol_mean) / vol_std
                if z_score > 2:
                    score += 10
                elif z_score > 1:
                    score += 6
                elif z_score > 0.5:
                    score += 3
        
        # Large intraday range = options-driven move
        if len(hist) >= 1:
            last_range = (hist['High'].iloc[-1] - hist['Low'].iloc[-1]) / max(hist['Low'].iloc[-1], 0.01)
            avg_range = ((hist['High'] - hist['Low']) / hist['Low'].replace(0, 1)).mean()
            if avg_range > 0 and last_range > avg_range * 1.5:
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
