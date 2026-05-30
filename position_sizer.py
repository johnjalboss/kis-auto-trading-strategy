"""
Optimal Position Sizer (v1.0.8)
================================
Calculate optimal position sizes using advanced quantitative methods:
1. Live Performance Feedback (trades.db Win Rate / Profit Factor tracking)
2. Dynamic Fractional Kelly Criterion
3. Volatility-Based Inverse Scaling
4. Regime-Aware Portfolio Risk Scaling (BULL 1.2x | BEAR 0.5x | CHOPPY 0.4x)
5. Risk Parity Allocation
"""

import os
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

import config

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
    profit_factor: float
    
    # Dollar amounts
    position_dollars: float
    stop_loss_dollars: float
    
    sizing_score: int
    details: List[str]


def get_live_performance_metrics(db_path: str = "trades.db") -> Tuple[float, float, float, str]:
    """
    [QUANT FEEDBACK L1]
    trades.db에 접속하여 최근 30~50회 매매 성과를 백트래킹 연산하여 
    실시간 실제 승률(Win Rate) 및 평균 손익비(Profit Factor / Avg Win to Loss)를 산출.
    """
    default_win_rate = 0.53
    default_avg_win = 0.06
    default_avg_loss = 0.03
    
    if not os.path.exists(db_path):
        return default_win_rate, default_avg_win, default_avg_loss, "DEFAULT_FALLBACK (No DB)"
        
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # exit_time이 존재하고 손익(pnl_pct)이 확정된 최근 40건의 거래 조회
        query = """
            SELECT pnl_pct FROM trades 
            WHERE exit_time IS NOT NULL AND pnl_pct != 0
            ORDER BY exit_time DESC LIMIT 40
        """
        df = pd.read_sql_query(query, conn)
        
        if df.empty or len(df) < 5:
            return default_win_rate, default_avg_win, default_avg_loss, f"DEFAULT_FALLBACK (Insufficient trades: {len(df)})"
            
        # Filter out NaN values to prevent win rate deflation
        pnl_list = df['pnl_pct'].dropna().astype(float).tolist()
        
        wins = [x for x in pnl_list if x > 0]
        losses = [x for x in pnl_list if x <= 0]
        
        win_rate = len(wins) / len(pnl_list)
        avg_win = np.mean(wins) if wins else default_avg_win
        avg_loss = abs(np.mean(losses)) if losses else default_avg_loss
        
        # zero division guard
        if avg_loss == 0:
            avg_loss = 0.01
            
        status_msg = f"LIVE_FEEDBACK_ACTIVE (Trades: {len(pnl_list)} | WinRate: {win_rate:.1%} | Win/Loss Ratio: {avg_win/avg_loss:.2f})"
        return win_rate, avg_win, avg_loss, status_msg
        
    except Exception as e:
        logger.error("Failed to query live performance metrics: {}", e)
        return default_win_rate, default_avg_win, default_avg_loss, f"ERROR_FALLBACK ({str(e)})"
    finally:
        if conn:
            conn.close()


class PositionSizer:
    """
    Optimal Position Sizing Engine (v1.0.8)
    
    1. DYNAMIC KELLY CRITERION
       f* = (p*b - q) / b
       where p = live win rate, b = live win/loss ratio, q = 1-p
       
    2. VOLATILITY SIZING
       Position = Risk% / Volatility
       
    3. RISK PARITY
       Equal risk contribution
       
    4. REGIME-AWARE RISK SCALING
       BULL (1.2x) | BEAR (0.5x) | CHOPPY (0.4x)
    """
    
    MAX_SINGLE_POSITION = 0.40  # [v1.1.8] 20% → 40%: small account needs concentration
    RISK_PER_TRADE = 0.02       # Risk 2% per trade
    
    def __init__(self, portfolio_value: float = 100000):
        self.portfolio = portfolio_value
        
    def calculate(self, symbol: str, current_regime: str = "BULL_NORMAL") -> PositionSizeResult:
        """Calculate optimal position size based on Live Feedback and Regime Scaling"""
        details = []
        
        # 1. Fetch Live Performance Feedback from DB
        win_rate, avg_win, avg_loss, feedback_msg = get_live_performance_metrics("trades.db")
        details.append(feedback_msg)
        
        # Fetch historical daily data for volatility calculation
        df = self._fetch_data(symbol)
        if df is None or len(df) < 30:
            return self._default_result(symbol)
            
        returns = df['Close'].pct_change().dropna()
        
        # Basic stats
        expected_return = returns.mean() * 252
        volatility = returns.std() * np.sqrt(252)
        sharpe = expected_return / volatility if volatility > 0 else 0
        
        # 2. Dynamic Kelly Computation
        b = avg_win / avg_loss if avg_loss > 0 else 2.0
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b if b > 0 else 0.10
        kelly = max(0.01, min(0.60, kelly))  # Clamp between 1% and 60%
        
        # We use standard Half-Kelly (Fractional Kelly)
        half_kelly = kelly / 2
        
        # 3. Volatility Sizing (Inverse Volatility Scaling)
        target_vol = 0.15
        ann_vol = volatility
        if ann_vol > 0:
            vol_position = (target_vol / ann_vol) * self.RISK_PER_TRADE * 10
            vol_position = min(0.25, vol_position)
        else:
            vol_position = 0.05
            
        # 4. Risk Parity Allocation (simplified)
        if volatility > 0:
            risk_parity = target_vol / volatility
            risk_parity = min(0.15, risk_parity)
        else:
            risk_parity = 0.05
            
        # 5. Blend & Calculate Optimal Size
        optimal = (half_kelly * 0.25 + vol_position * 0.45 + risk_parity * 0.30)
        
        # 6. Apply REGIME-AWARE Portfolio Risk Scaling (The Quant Shield)
        bear_regimes = {"BEAR_NORMAL", "BEAR_TRENDING", "BEAR_VOLATILE"}
        choppy_regimes = {"CHOPPY", "TRANSITION", "CHOPPY_VOLATILE"}
        
        if current_regime in bear_regimes:
            optimal *= 0.50
            details.append("BEAR_REGIME_SCALE (Risk halved to 50%)")
        elif current_regime in choppy_regimes:
            optimal *= 0.65  # [v1.1.8] 40% → 65%: 40% was too aggressive for small accounts
            details.append("CHOPPY_REGIME_SCALE (Risk clamped to 65%)")
        elif "BULL" in current_regime:
            optimal *= 1.20
            details.append("BULL_REGIME_SCALE (Risk boosted by 1.2x)")
            
        # 6.5 Apply Geopolitical Yen Carry & Systemic Tail Risk Shield (Option 3)
        yen_mult = 1.0
        try:
            from risk_manager import get_risk_manager
            rm = get_risk_manager()
            # This dynamically updates rm.max_positions and returns the systemic risk multiplier
            yen_mult = rm.get_systemic_risk_multiplier()
            if yen_mult < 1.0:
                optimal *= yen_mult
                details.append(f"YEN_SHIELD_SCALE (Risk scaled by {yen_mult:.0%})")
        except Exception as e:
            logger.error("[SIZER] Failed to apply Yen Shield: {}", e)

        # 6.6 Microstructure Order Book Imbalance (OBI) Sizing Filter (Option 1)
        obi_val = 0.0
        try:
            from trader import get_trader
            trader_inst = get_trader()
            obi_val = trader_inst.calculate_obi(symbol)
            if obi_val < -0.2:
                # Scale down position by a factor proportional to sell pressure
                # e.g. OBI = -0.6 -> scale down by 1 + 0.5 * (-0.6) = 0.7x
                obi_mult = max(0.5, 1.0 + 0.5 * obi_val)
                optimal *= obi_mult
                details.append(f"OBI_SIZER_FILTER (OBI: {obi_val:+.2f} | Scaled by {obi_mult:.0%})")
        except Exception as e:
            logger.debug("[SIZER] OBI scaling bypassed or failed: {}", e)
            
        # Apply max single position limits
        max_pos = self.MAX_SINGLE_POSITION
        
        # Adjust limits for asset-level volatility
        if volatility > 0.45:
            optimal *= 0.50
            max_pos *= 0.50
            details.append("ASSET_EXTREME_VOL_CLAMPED")
        elif volatility > 0.30:
            optimal *= 0.75
            max_pos *= 0.75
            details.append("ASSET_HIGH_VOL_CLAMPED")
            
        # Sharpe adjustment
        if sharpe < 0:
            optimal *= 0.50
            details.append("NEGATIVE_SHARPE_CLAMPED")
        elif sharpe > 1.2:
            optimal *= 1.15
            details.append("ULTRA_HIGH_SHARPE_BONUS")
            
        # Clamp to bounds
        optimal = min(optimal, max_pos)
        optimal = max(0.01, optimal)  # Minimum 1% of portfolio
        
        # Dollar amounts
        position_dollars = self.portfolio * optimal
        stop_loss = position_dollars * 0.05  # 5% stop loss target
        
        # Scoring
        if sharpe > 1.0 and win_rate > 0.52:
            score = 85
        elif sharpe > 0.5 and win_rate > 0.48:
            score = 65
        elif sharpe > 0:
            score = 45
        else:
            score = 25
            
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
            profit_factor=b,
            position_dollars=position_dollars,
            stop_loss_dollars=stop_loss,
            sizing_score=score,
            details=details
        )
        
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch daily data"""
        try:
            df = yf.download(symbol, period='1y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except Exception:
            return None
            
    def _default_result(self, symbol: str) -> PositionSizeResult:
        """Default fallback result"""
        return PositionSizeResult(
            symbol=symbol, kelly_pct=0.05, half_kelly_pct=0.025,
            volatility_pct=0.05, risk_parity_pct=0.05,
            optimal_pct=0.05, max_position_pct=0.10,
            expected_return=0.10, volatility=0.25, sharpe=0.4,
            win_rate=0.53, profit_factor=2.0,
            position_dollars=self.portfolio * 0.05,
            stop_loss_dollars=self.portfolio * 0.05 * 0.05,
            sizing_score=50, details=["FALLBACK_DEFAULT"]
        )


def calculate_optimal_size(symbol: str, raw_qty: int, kelly_pct: float, max_exposure_pct: float) -> int:
    """
    [LEGACY COMPATIBILITY HOOK]
    Scale down raw quantity using the macro max_exposure_pct parameter.
    """
    adjusted_qty = raw_qty * max_exposure_pct
    
    # Kelly constraint (less aggressive penalty for low conviction)
    if kelly_pct < 0.05:
        adjusted_qty *= 0.5
    elif kelly_pct < 0.1:
        adjusted_qty *= 0.8
        
    # Rounding
    if adjusted_qty > 0.4 and adjusted_qty < 1:
        final_qty = 1
    else:
        final_qty = int(round(adjusted_qty))
        
    logger.debug("Sizer: scaled {} qty from {} -> {} (max_exp={:.0f}%, kelly={:.1%})",
                 symbol, raw_qty, final_qty, max_exposure_pct*100, kelly_pct)
    return max(0, final_qty)


def get_position_sizer(portfolio: float = 100000) -> PositionSizer:
    """Global sizer factory"""
    return PositionSizer(portfolio)


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
               
    print("=" * 60)
    print("Testing v1.0.8 Quant Sizing Feedback Engine...")
    print("=" * 60)
    
    # Check if trades.db is analyzed
    win, w, l, msg = get_live_performance_metrics("trades.db")
    print(f"trades.db status: {msg}")
    
    sizer = PositionSizer(portfolio_value=10000)
    
    for symbol in ["AAPL", "NVDA", "TSLA"]:
        print(f"\n{'-'*50}\n{symbol} ($10K Portfolio, BULL market)\n{'-'*50}")
        result = sizer.calculate(symbol, current_regime="BULL_NORMAL")
        print(f"Expected Ann. Return: {result.expected_return:.1%}")
        print(f"Annual Volatility   : {result.volatility:.1%}")
        print(f"Sharpe Ratio        : {result.sharpe:.2f}")
        print(f"Kelly Fraction      : {result.kelly_pct:.1%}")
        print(f"Volatility Sizing   : {result.volatility_pct:.1%}")
        print(f"Risk Parity Sizing  : {result.risk_parity_pct:.1%}")
        print(f"--> [OPTIMAL SIZING]: {result.optimal_pct:.1%} (${result.position_dollars:,.2f})")
        print(f"--> [TARGET STOP]  : ${result.stop_loss_dollars:,.2f}")
        print(f"Details             : {result.details}")
