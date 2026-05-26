"""
Optimal Position Sizer
========================
Calculate optimal position sizes using advanced methods.

Methods:
1. Kelly Criterion
2. Volatility-Based Sizing
3. Risk Parity
4. Max Drawdown Limit
5. VaR-Based Limits
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

import data_proxy
import yfinance as yf
from loguru import logger


@dataclass
class PositionSizeResult:
    """Position sizing result"""
    symbol: str
    
    # Position sizes (% of portfolio)
    kelly_pct: float
    half_kelly_pct: float
    volatility_pct: float
    risk_parity_pct: float
    
    # Recommended
    optimal_pct: float
    max_position_pct: float
    
    # Risk metrics
    expected_return: float
    volatility: float
    sharpe: float
    win_rate: float
    
    # Dollar amounts (for $100K portfolio)
    position_dollars: float
    stop_loss_dollars: float
    
    sizing_score: int
    details: List[str]


class PositionSizer:
    """
    Optimal Position Sizing Engine
    
    Methods:
    
    1. KELLY CRITERION
       f* = (p*b - q) / b
       where p = win rate, b = win/loss ratio, q = 1-p
       
    2. VOLATILITY SIZING
       Position = Risk% / Volatility
       
    3. RISK PARITY
       Equal risk contribution from each position
       
    4. MAX DRAWDOWN
       Limit size to cap drawdown at X%
    
    Rules:
    - Never use full Kelly (too aggressive)
    - Half-Kelly is standard
    - Cap at 10% of portfolio for single stock
    - Reduce in high volatility
    """
    
    DEFAULT_PORTFOLIO = 100000  # $100K
    MAX_SINGLE_POSITION = 0.20  # 20% max in one stock for high conviction swing trades
    RISK_PER_TRADE = 0.02       # Risk 2% per trade
    
    def __init__(self, portfolio_value: float = 100000):
        self.portfolio = portfolio_value
    
    def calculate(self, symbol: str, 
                  win_rate: float = 0.55,
                  avg_win: float = 0.08,
                  avg_loss: float = 0.04) -> PositionSizeResult:
        """Calculate optimal position size"""
        details = []
        
        df = self._fetch_data(symbol)
        
        if df is None or len(df) < 30:
            return self._default_result(symbol)
        
        returns = df['Close'].pct_change().dropna()
        
        # Calculate metrics
        expected_return = returns.mean() * 252
        volatility = returns.std() * np.sqrt(252)
        sharpe = expected_return / volatility if volatility > 0 else 0
        
        # 1. Kelly Criterion
        if avg_loss > 0:
            b = avg_win / avg_loss  # Win/loss ratio
            q = 1 - win_rate
            kelly = (win_rate * b - q) / b
            kelly = max(0, min(1, kelly))
        else:
            kelly = 0.10
        
        half_kelly = kelly / 2
        
        # 2. Volatility-Based Sizing (Inverse Volatility Scaling)
        # Target an annualized volatility of 15% for the portfolio
        target_vol = 0.15
        
        daily_vol = returns.std()
        ann_vol = daily_vol * np.sqrt(252)
        
        if ann_vol > 0:
            # Scale position inversely to its volatility
            vol_position = (target_vol / ann_vol) * self.RISK_PER_TRADE * 10 
            vol_position = min(0.25, vol_position)  # Cap at 25%
        else:
            vol_position = 0.05
        
        # 3. Risk Parity (simplified)
        if volatility > 0:
            risk_parity = target_vol / volatility
            risk_parity = min(0.15, risk_parity)
        else:
            risk_parity = 0.05
        
        # 4. Calculate Optimal (blend)
        # Shifted away from pure Kelly to favor Volatility Parity
        optimal = (half_kelly * 0.2 + vol_position * 0.5 + risk_parity * 0.3)
        
        # Apply max position limit
        max_pos = self.MAX_SINGLE_POSITION
        
        # Adjust for volatility regime
        if volatility > 0.40:  # High vol stock
            optimal *= 0.5
            max_pos *= 0.5
            details.append("HIGH_VOL_REDUCED")
        elif volatility > 0.30:
            optimal *= 0.75
            max_pos *= 0.75
        
        # Adjust for Sharpe
        if sharpe < 0:
            optimal *= 0.5
            details.append("NEGATIVE_SHARPE")
        elif sharpe > 1:
            optimal *= 1.2
            details.append("HIGH_SHARPE")
        
        optimal = min(optimal, max_pos)
        
        # Dollar amounts
        position_dollars = self.portfolio * optimal
        stop_loss = position_dollars * 0.05  # 5% stop loss
        
        # Scoring
        if sharpe > 1 and win_rate > 0.55:
            score = 80
        elif sharpe > 0.5 and win_rate > 0.50:
            score = 60
        elif sharpe > 0:
            score = 40
        else:
            score = 20
        
        details.append(f"KELLY:{kelly:.1%}_HALF:{half_kelly:.1%}")
        
        return PositionSizeResult(
            symbol=symbol,
            kelly_pct=kelly,
            half_kelly_pct=half_kelly,
            volatility_pct=vol_position,
            risk_parity_pct=risk_parity,
            optimal_pct=optimal,
            max_position_pct=max_pos,
            expected_return=expected_return,
            volatility=volatility,
            sharpe=sharpe,
            win_rate=win_rate,
            position_dollars=position_dollars,
            stop_loss_dollars=stop_loss,
            sizing_score=score,
            details=details
        )
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _default_result(self, symbol: str) -> PositionSizeResult:
        """Default result"""
        return PositionSizeResult(
            symbol=symbol, kelly_pct=0.05, half_kelly_pct=0.025,
            volatility_pct=0.05, risk_parity_pct=0.05,
            optimal_pct=0.05, max_position_pct=0.10,
            expected_return=0.10, volatility=0.25, sharpe=0.4, win_rate=0.50,
            position_dollars=5000, stop_loss_dollars=250,
            sizing_score=50, details=[]
        )


# Global
_sizer = None

def get_position_sizer(portfolio: float = 100000) -> PositionSizer:
    global _sizer
    if _sizer is None:
        _sizer = PositionSizer(portfolio)
    return _sizer


def calculate_optimal_size(symbol: str, raw_qty: int, kelly_pct: float, max_exposure_pct: float) -> int:
    """
    Scale down raw quantity using the macro max_exposure_pct parameter.
    If max_exposure_pct is e.g. 0.5 (50%), the quantity is strictly clamped.
    """
    # Scaling
    adjusted_qty = raw_qty * max_exposure_pct
    
    # Kelly constraint (less aggressive penalty for low conviction)
    if kelly_pct < 0.05:
        adjusted_qty *= 0.5
    elif kelly_pct < 0.1:
        adjusted_qty *= 0.8 # 20% reduction instead of 50%
        
    # Rounding: if > 0.4 shares, round up to 1 to ensure small accounts still trade
    if adjusted_qty > 0.4 and adjusted_qty < 1:
        final_qty = 1
    else:
        final_qty = int(round(adjusted_qty))
    
    logger.debug("Sizer: scaled {} qty from {} -> {} (max_exp={:.0f}%, kelly={:.1%})",
                 symbol, raw_qty, final_qty, max_exposure_pct*100, kelly_pct)
    return max(0, final_qty)



if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Testing PositionSizer...")
    
    sizer = PositionSizer(portfolio_value=100000)
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'='*60}")
        print(f"{symbol} ($100K Portfolio)")
        print('='*60)
        
        result = sizer.calculate(symbol)
        
        print(f"Expected Return: {result.expected_return:.1%}")
        print(f"Volatility: {result.volatility:.1%}")
        print(f"Sharpe: {result.sharpe:.2f}")
        print()
        print(f"Kelly: {result.kelly_pct:.1%}")
        print(f"Half-Kelly: {result.half_kelly_pct:.1%}")
        print(f"Volatility-Based: {result.volatility_pct:.1%}")
        print(f"Risk Parity: {result.risk_parity_pct:.1%}")
        print()
        print(f"✅ Optimal: {result.optimal_pct:.1%}")
        print(f"📐 Position: ${result.position_dollars:,.0f}")
        print(f"🛑 Stop Loss: ${result.stop_loss_dollars:,.0f}")
        print(f"Details: {result.details}")
