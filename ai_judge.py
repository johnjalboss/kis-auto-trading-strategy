"""
AI 매매 판단 모듈
ATR 트레일링 스탑 전략 + 이동평균/거래량 기반 매수 조건
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


# ==============================================
# 전략 설정값
# ==============================================

@dataclass
class StrategyConfig:
    """매매 전략 설정"""
    # 이동평균선 설정
    MA_PERIOD: int = 20                    # 20일 이동평균선
    
    # 거래량 설정
    VOLUME_AVG_PERIOD: int = 20            # 거래량 평균 기간
    VOLUME_SURGE_THRESHOLD: float = 1.5    # 거래량 급증 기준 (150%)
    VOLUME_LOOKBACK_DAYS: int = 3          # 최근 N일 내 거래량 확인
    
    # ATR 설정
    ATR_PERIOD: int = 14                   # ATR 계산 기간
    ATR_MULTIPLIER: float = 3.0            # 트레일링 스탑 배수 (3 * ATR)
    
    # 리스크 관리
    MAX_POSITION_RATIO: float = 0.20       # 종목당 최대 비중 (20%)


# 기본 설정
CONFIG = StrategyConfig()


# ==============================================
# 포지션 추적용 데이터 클래스
# ==============================================

@dataclass
class Position:
    """보유 포지션 정보"""
    symbol: str
    entry_price: float
    quantity: int
    entry_date: datetime
    highest_price: float = 0.0             # 매수 후 최고가
    trailing_stop: float = 0.0             # 트레일링 스탑 가격
    current_atr: float = 0.0               # 현재 ATR 값
    
    def __post_init__(self):
        if self.highest_price == 0.0:
            self.highest_price = self.entry_price
    
    def update_trailing_stop(self, current_price: float, atr: float):
        """트레일링 스탑 업데이트 (가격 상승 시에만)"""
        self.current_atr = atr
        
        # 최고가 갱신
        if current_price > self.highest_price:
            self.highest_price = current_price
        
        # 새로운 스탑 가격 계산 (고점 - 3 * ATR)
        new_stop = self.highest_price - (CONFIG.ATR_MULTIPLIER * atr)
        
        # 스탑은 올라가기만 함 (내려가지 않음)
        if new_stop > self.trailing_stop:
            self.trailing_stop = new_stop
        
        return self.trailing_stop


# 포지션 저장소
positions: dict[str, Position] = {}


# ==============================================
# 기술적 지표 계산 함수
# ==============================================

def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """단순 이동평균선 계산"""
    return prices.rolling(window=period).mean()


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR (Average True Range) 계산
    
    True Range = max(
        High - Low,
        abs(High - Previous Close),
        abs(Low - Previous Close)
    )
    ATR = SMA of True Range
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def check_volume_surge(volumes: pd.Series, lookback: int = 3, threshold: float = 1.5) -> bool:
    """최근 N일 내 거래량 급증 여부 확인
    
    Args:
        volumes: 거래량 시계열 데이터
        lookback: 확인할 최근 일수
        threshold: 평균 대비 비율 (1.5 = 150%)
    
    Returns:
        True if 최근 N일 내 거래량 급증 발생
    """
    if len(volumes) < CONFIG.VOLUME_AVG_PERIOD + lookback:
        return False
    
    # 평균 거래량 (lookback 기간 제외)
    avg_volume = volumes.iloc[:-lookback].tail(CONFIG.VOLUME_AVG_PERIOD).mean()
    
    # 최근 N일 거래량 중 하나라도 평균의 threshold배 이상이면 True
    recent_volumes = volumes.tail(lookback)
    
    return any(vol >= avg_volume * threshold for vol in recent_volumes)


# ==============================================
# 매수 조건 판단
# ==============================================

def should_buy(
    symbol: str,
    current_price: float,
    prices: pd.Series,
    volumes: pd.Series,
    total_equity: float,
    current_positions_value: float = 0.0
) -> Tuple[bool, str, int]:
    """매수 조건 판단
    
    매수 조건:
    1. 현재가가 20일 이동평균선 위에 있음
    2. 최근 3일 내 거래량이 평균의 150% 이상
    3. 해당 종목 비중이 전체 자산의 20% 미만
    
    Args:
        symbol: 종목 코드
        current_price: 현재가
        prices: 가격 시계열 (종가 기준)
        volumes: 거래량 시계열
        total_equity: 전체 자산
        current_positions_value: 현재 해당 종목 보유 가치
    
    Returns:
        (매수 여부, 사유, 추천 수량)
    """
    # 이미 보유 중인 경우
    if symbol in positions:
        return False, "이미 보유 중", 0
    
    # 조건 1: 20일 이동평균선 체크
    if len(prices) < CONFIG.MA_PERIOD:
        return False, f"데이터 부족 ({len(prices)}일 < {CONFIG.MA_PERIOD}일)", 0
    
    sma_20 = calculate_sma(prices, CONFIG.MA_PERIOD).iloc[-1]
    
    if current_price <= sma_20:
        return False, f"20일선 아래 (현재가 ${current_price:.2f} <= MA ${sma_20:.2f})", 0
    
    # 조건 2: 거래량 급증 체크
    if not check_volume_surge(volumes, CONFIG.VOLUME_LOOKBACK_DAYS, CONFIG.VOLUME_SURGE_THRESHOLD):
        return False, "거래량 급증 미발생", 0
    
    # 조건 3: 포지션 사이징 (최대 20% 비중)
    max_position_value = total_equity * CONFIG.MAX_POSITION_RATIO
    available_value = max_position_value - current_positions_value
    
    if available_value <= 0:
        return False, f"비중 초과 (현재 {(current_positions_value/total_equity)*100:.1f}%)", 0
    
    # 추천 수량 계산
    recommended_qty = int(available_value / current_price)
    
    if recommended_qty <= 0:
        return False, "매수 가능 금액 부족", 0
    
    reason = f"✅ 매수 신호! MA20 위 + 거래량 급증 (추천: {recommended_qty}주)"
    return True, reason, recommended_qty


# ==============================================
# 매도 조건 판단 (ATR 트레일링 스탑)
# ==============================================

def should_sell(
    symbol: str,
    current_price: float,
    high_prices: pd.Series,
    low_prices: pd.Series,
    close_prices: pd.Series
) -> Tuple[bool, str]:
    """매도 조건 판단 (ATR 트레일링 스탑)
    
    매도 조건:
    - 매수 후 고점 대비 3 * ATR 만큼 하락 시 전량 매도
    
    Args:
        symbol: 종목 코드
        current_price: 현재가
        high_prices: 고가 시계열
        low_prices: 저가 시계열  
        close_prices: 종가 시계열
    
    Returns:
        (매도 여부, 사유)
    """
    # 보유 중이 아닌 경우
    if symbol not in positions:
        return False, "보유 종목 아님"
    
    position = positions[symbol]
    
    # ATR 계산
    if len(close_prices) < CONFIG.ATR_PERIOD:
        return False, f"ATR 계산 불가 (데이터 부족)"
    
    atr = calculate_atr(high_prices, low_prices, close_prices, CONFIG.ATR_PERIOD).iloc[-1]
    
    # 트레일링 스탑 업데이트
    trailing_stop = position.update_trailing_stop(current_price, atr)
    
    # 손익 계산
    pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
    
    # 매도 조건: 현재가 <= 트레일링 스탑
    if current_price <= trailing_stop:
        pnl_text = f"+{pnl_pct:.1f}%" if pnl_pct >= 0 else f"{pnl_pct:.1f}%"
        return True, f"🔔 트레일링 스탑 발동! (${trailing_stop:.2f}) | 수익률: {pnl_text}"
    
    # 아직 매도 조건 미충족
    return False, f"홀딩 중 | 고점: ${position.highest_price:.2f} | 스탑: ${trailing_stop:.2f} | ATR: ${atr:.2f}"


# ==============================================
# 포지션 관리 함수
# ==============================================

def open_position(symbol: str, entry_price: float, quantity: int, atr: float = 0.0):
    """포지션 오픈 (매수 체결 시 호출)"""
    position = Position(
        symbol=symbol,
        entry_price=entry_price,
        quantity=quantity,
        entry_date=datetime.now(),
        highest_price=entry_price,
        current_atr=atr
    )
    
    # 초기 트레일링 스탑 설정
    if atr > 0:
        position.trailing_stop = entry_price - (CONFIG.ATR_MULTIPLIER * atr)
    
    positions[symbol] = position
    return position


def close_position(symbol: str) -> Optional[Position]:
    """포지션 종료 (매도 체결 시 호출)"""
    return positions.pop(symbol, None)


def get_position(symbol: str) -> Optional[Position]:
    """포지션 조회"""
    return positions.get(symbol)


def get_all_positions() -> dict:
    """전체 포지션 조회"""
    return positions.copy()


def calculate_position_size(
    symbol: str,
    current_price: float,
    total_equity: float,
    existing_value: float = 0.0
) -> int:
    """포지션 사이즈 계산 (최대 20% 비중 제한)
    
    Args:
        symbol: 종목 코드
        current_price: 현재가
        total_equity: 전체 자산
        existing_value: 이미 보유 중인 해당 종목의 가치
    
    Returns:
        매수 가능 수량
    """
    max_value = total_equity * CONFIG.MAX_POSITION_RATIO
    available_value = max_value - existing_value
    
    if available_value <= 0:
        return 0
    
    return int(available_value / current_price)


# ==============================================
# 테스트용 메인 함수
# ==============================================

if __name__ == "__main__":
    print("=" * 60)
    print("📈 AI 매매 판단 모듈 테스트")
    print("=" * 60)
    
    # 설정값 출력
    print("\n📋 전략 설정:")
    print(f"  - 이동평균 기간: {CONFIG.MA_PERIOD}일")
    print(f"  - 거래량 급증 기준: {CONFIG.VOLUME_SURGE_THRESHOLD * 100:.0f}%")
    print(f"  - 거래량 확인 기간: 최근 {CONFIG.VOLUME_LOOKBACK_DAYS}일")
    print(f"  - ATR 기간: {CONFIG.ATR_PERIOD}일")
    print(f"  - 트레일링 스탑: {CONFIG.ATR_MULTIPLIER} × ATR")
    print(f"  - 종목당 최대 비중: {CONFIG.MAX_POSITION_RATIO * 100:.0f}%")
    
    # 테스트 데이터 생성
    print("\n🧪 테스트 시나리오:")
    
    # 가상의 가격/거래량 데이터
    np.random.seed(42)
    test_prices = pd.Series([100 + i + np.random.randn() * 2 for i in range(30)])
    test_volumes = pd.Series([1000000 + np.random.randint(-200000, 200000) for _ in range(30)])
    # 마지막 3일 거래량 급증
    test_volumes.iloc[-3:] = test_volumes.iloc[-3:] * 2
    
    test_high = test_prices * 1.02
    test_low = test_prices * 0.98
    
    # 매수 조건 테스트
    current_price = test_prices.iloc[-1]
    should_buy_result = should_buy(
        symbol="TSLA",
        current_price=current_price,
        prices=test_prices,
        volumes=test_volumes,
        total_equity=100000,
        current_positions_value=0
    )
    print(f"\n[TSLA 매수 판단]")
    print(f"  현재가: ${current_price:.2f}")
    print(f"  결과: {should_buy_result[1]}")
    
    if should_buy_result[0]:
        # 포지션 오픈 시뮬레이션
        atr = calculate_atr(test_high, test_low, test_prices, CONFIG.ATR_PERIOD).iloc[-1]
        pos = open_position("TSLA", current_price, should_buy_result[2], atr)
        print(f"  매수 체결: {pos.quantity}주 @ ${pos.entry_price:.2f}")
        print(f"  초기 스탑: ${pos.trailing_stop:.2f}")
        
        # 가격 상승 시뮬레이션
        new_price = current_price * 1.10  # 10% 상승
        should_sell_result = should_sell(
            symbol="TSLA",
            current_price=new_price,
            high_prices=test_high,
            low_prices=test_low,
            close_prices=test_prices
        )
        print(f"\n[TSLA 매도 판단 - 가격 상승 후]")
        print(f"  현재가: ${new_price:.2f} (+10%)")
        print(f"  결과: {should_sell_result[1]}")
