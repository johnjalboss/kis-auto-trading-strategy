"""
Backtesting Engine
==================
Test trading strategies against historical data.

Features:
1. Historical data simulation
2. Trade execution simulation
3. Performance metrics (Sharpe, Sortino, Max Drawdown)
4. Strategy comparison
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger


@dataclass
class Trade:
    """Simulated trade"""
    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: int = 100
    side: str = "LONG"
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    """Backtest result summary"""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # Returns
    total_return: float
    annual_return: float
    
    # Risk Metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # days
    
    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Trades
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class Backtester:
    """
    Strategy Backtesting Engine
    
    Usage:
        backtester = Backtester(initial_capital=10000)
        result = backtester.run(
            symbols=['AAPL', 'TSLA'],
            start_date='2024-01-01',
            end_date='2024-12-31',
            strategy=my_strategy_func
        )
    """
    
    def __init__(self, initial_capital: float = 10000, 
                 commission: float = 0.001):  # 0.1% commission
        self.initial_capital = initial_capital
        self.commission = commission
        self.capital = initial_capital
        self.positions: Dict[str, Trade] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
    
    def run(self, symbols: List[str], 
            start_date: str, end_date: str,
            take_profit: float = 0.03,
            stop_loss: float = 0.02,
            max_holding_days: int = 5) -> BacktestResult:
        """
        Run backtest with simple momentum strategy
        
        Args:
            symbols: List of symbols to trade
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            take_profit: Take profit percentage
            stop_loss: Stop loss percentage
            max_holding_days: Maximum days to hold position
        """
        self._reset()
        
        # Fetch historical data
        data = self._fetch_data(symbols, start_date, end_date)
        
        if not data:
            logger.error("No data fetched for backtest")
            return self._empty_result(start_date, end_date)
        
        # Get trading days
        first_symbol = list(data.keys())[0]
        trading_days = data[first_symbol].index.tolist()
        
        logger.info("Running backtest from {} to {} ({} days)",
                   start_date, end_date, len(trading_days))
        
        # Simulate each day
        for i, current_date in enumerate(trading_days):
            if i < 20:  # Need 20 days for indicators
                continue
            
            # Check exits first
            self._check_exits(data, current_date, take_profit, stop_loss, max_holding_days)
            
            # Check entries
            if len(self.positions) < 3:  # Max 3 concurrent positions
                self._check_entries(data, symbols, i, current_date)
            
            # Record equity
            equity = self._calculate_equity(data, current_date)
            self.equity_curve.append(equity)
        
        # Close all remaining positions
        self._close_all_positions(data, trading_days[-1])
        
        return self._calculate_result(start_date, end_date)
    
    def _reset(self):
        """Reset backtester state"""
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.initial_capital]
    
    def _fetch_data(self, symbols: List[str], 
                    start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for all symbols"""
        data = {}
        
        for symbol in symbols:
            try:
                df = yf.download(symbol, start=start_date, end=end_date,
                                progress=False, auto_adjust=True)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    data[symbol] = df
            except Exception as e:
                logger.debug("Failed to fetch {}: {}", symbol, e)
        
        return data
    
    def _check_entries(self, data: Dict[str, pd.DataFrame], 
                      symbols: List[str], day_idx: int, current_date):
        """Check for entry signals"""
        for symbol in symbols:
            if symbol in self.positions:
                continue
            
            if symbol not in data:
                continue
            
            df = data[symbol]
            if current_date not in df.index:
                continue
            
            # Get data up to current date
            hist = df.loc[:current_date].tail(20)
            
            if len(hist) < 20:
                continue
            
            # Simple momentum entry: RSI < 40 and price above 20-day SMA
            close = hist['Close']
            sma_20 = close.mean()
            current_price = close.iloc[-1]
            
            # Calculate RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Entry condition: RSI oversold + above SMA
            if rsi < 45 and current_price > sma_20:
                # Calculate position size
                risk_amount = self.capital * 0.02  # 2% risk per trade
                quantity = int(risk_amount / (current_price * 0.02))  # Based on 2% stop
                
                if quantity > 0 and self.capital >= current_price * quantity:
                    trade = Trade(
                        symbol=symbol,
                        entry_time=current_date,
                        entry_price=current_price,
                        quantity=quantity,
                        side="LONG"
                    )
                    self.positions[symbol] = trade
                    self.capital -= current_price * quantity * (1 + self.commission)
    
    def _check_exits(self, data: Dict[str, pd.DataFrame], 
                    current_date, take_profit: float, 
                    stop_loss: float, max_holding_days: int):
        """Check for exit signals"""
        symbols_to_close = []
        
        for symbol, trade in self.positions.items():
            if symbol not in data:
                continue
            
            df = data[symbol]
            if current_date not in df.index:
                continue
            
            current_price = df.loc[current_date, 'Close']
            pnl_pct = (current_price - trade.entry_price) / trade.entry_price
            
            # Check holding period
            if isinstance(current_date, pd.Timestamp):
                holding_days = (current_date - trade.entry_time).days
            else:
                holding_days = 0
            
            exit_reason = None
            
            # Take profit
            if pnl_pct >= take_profit:
                exit_reason = f"TP:{pnl_pct:+.1%}"
            # Stop loss
            elif pnl_pct <= -stop_loss:
                exit_reason = f"SL:{pnl_pct:+.1%}"
            # Max holding period
            elif holding_days >= max_holding_days:
                exit_reason = f"TIME:{holding_days}d"
            
            if exit_reason:
                trade.exit_time = current_date
                trade.exit_price = current_price
                trade.pnl_pct = pnl_pct
                trade.pnl = (current_price - trade.entry_price) * trade.quantity
                trade.exit_reason = exit_reason
                
                self.capital += current_price * trade.quantity * (1 - self.commission)
                self.trades.append(trade)
                symbols_to_close.append(symbol)
        
        for symbol in symbols_to_close:
            del self.positions[symbol]
    
    def _close_all_positions(self, data: Dict[str, pd.DataFrame], final_date):
        """Close all remaining positions"""
        for symbol, trade in list(self.positions.items()):
            if symbol in data and final_date in data[symbol].index:
                current_price = data[symbol].loc[final_date, 'Close']
                trade.exit_time = final_date
                trade.exit_price = current_price
                trade.pnl_pct = (current_price - trade.entry_price) / trade.entry_price
                trade.pnl = (current_price - trade.entry_price) * trade.quantity
                trade.exit_reason = "END"
                
                self.capital += current_price * trade.quantity * (1 - self.commission)
                self.trades.append(trade)
        
        self.positions = {}
    
    def _calculate_equity(self, data: Dict[str, pd.DataFrame], current_date) -> float:
        """Calculate current equity"""
        equity = self.capital
        
        for symbol, trade in self.positions.items():
            if symbol in data and current_date in data[symbol].index:
                current_price = data[symbol].loc[current_date, 'Close']
                equity += current_price * trade.quantity
        
        return equity
    
    def _calculate_result(self, start_date: str, end_date: str) -> BacktestResult:
        """Calculate backtest metrics"""
        final_capital = self.capital
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # Calculate annual return
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        years = (end - start).days / 365.25
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Calculate returns for Sharpe/Sortino
        equity_series = pd.Series(self.equity_curve)
        returns = equity_series.pct_change().dropna()
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Sortino Ratio (downside deviation)
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() if len(negative_returns) > 0 else 0.001
        sortino = returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Max Drawdown
        peak = equity_series.expanding(min_periods=1).max()
        drawdown = (equity_series - peak) / peak
        max_dd = abs(drawdown.min())
        
        # Trade statistics
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = len(winning) / len(self.trades) if self.trades else 0
        avg_win = np.mean([t.pnl for t in winning]) if winning else 0
        avg_loss = abs(np.mean([t.pnl for t in losing])) if losing else 0
        
        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return BacktestResult(
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=0,
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
    
    def _empty_result(self, start_date: str, end_date: str) -> BacktestResult:
        """Return empty result"""
        return BacktestResult(
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d'),
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return=0, annual_return=0, sharpe_ratio=0, sortino_ratio=0,
            max_drawdown=0, max_drawdown_duration=0, total_trades=0,
            winning_trades=0, losing_trades=0, win_rate=0, avg_win=0,
            avg_loss=0, profit_factor=0
        )


if __name__ == "__main__":
    import sys
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    print("Running Backtest...")
    
    backtester = Backtester(initial_capital=10000)
    
    result = backtester.run(
        symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'],
        start_date='2024-01-01',
        end_date='2024-12-31',
        take_profit=0.03,
        stop_loss=0.02,
        max_holding_days=5
    )
    
    print(f"\n{'='*50}")
    print("BACKTEST RESULTS")
    print('='*50)
    print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
    print(f"Initial: ${result.initial_capital:,.0f}")
    print(f"Final: ${result.final_capital:,.0f}")
    print(f"{'='*50}")
    print(f"Total Return: {result.total_return:+.1%}")
    print(f"Annual Return: {result.annual_return:+.1%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio: {result.sortino_ratio:.2f}")
    print(f"Max Drawdown: {result.max_drawdown:.1%}")
    print(f"{'='*50}")
    print(f"Total Trades: {result.total_trades}")
    print(f"Win Rate: {result.win_rate:.1%}")
    print(f"Avg Win: ${result.avg_win:.2f}")
    print(f"Avg Loss: ${result.avg_loss:.2f}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
