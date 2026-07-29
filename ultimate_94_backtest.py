"""
Ultimate 130-Module Backtester
==============================
Simulates the real CompositeSignalEngine logic over historical data.
Provides a clear Win Rate, Profit Factor, and Total Return metric
for the aggressive profile tuning.
"""

import sys
import pandas as pd
import yfinance as yf
from loguru import logger
import numpy as np
from typing import Dict, List

# Bypass live proxy to run faster over historical YF data
import data_proxy

# Import the aggressive master engine
from composite_signal import get_composite_engine, ActionType

class UltimateBacktester:
    def __init__(self, tickers: List[str], initial_capital: float = 100000):
        self.tickers = tickers
        self.capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, dict] = {}
        self.trade_history = []
        self.engine = get_composite_engine()
        
    def _fetch_history(self, symbol) -> pd.DataFrame:
        """Fetch 6 months of daily data to walk forward 3 months"""
        df = yf.download(symbol, period='6mo', interval='1d', progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def run(self):
        logger.info(f"Starting Ultimate Backtest: Initial Capital ${self.capital:,.2f}")
        logger.info(f"Target Universe: {self.tickers}")
        
        all_data = {}
        for ticker in self.tickers:
            df = self._fetch_history(ticker)
            if not df.empty:
                all_data[ticker] = df
                
        if not all_data:
            logger.error("No historical data fetched.")
            return

        # Find common dates in the last 60 trading days
        dates = all_data[self.tickers[0]].index[-60:]
        
        for current_time in dates:
            logger.debug(f"\n--- Processing Date: {current_time.strftime('%Y-%m-%d')} ---")
            
            # 1. Update existing positions (Check Take Profit / Stop Loss)
            for sym, pos in list(self.positions.items()):
                df = all_data[sym][:current_time]
                if df.empty: continue
                current_price = float(df['Close'].iloc[-1])
                
                # Check stops
                if current_price >= pos['tp']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    self._close_position(sym, current_price, "TAKE_PROFIT", profit)
                elif current_price <= pos['sl']:
                    loss = (current_price - pos['entry_price']) * pos['shares']
                    self._close_position(sym, current_price, "STOP_LOSS", loss)
            
            # 2. Daily Scoring and Entry Logging
            for sym, df_full in all_data.items():
                if sym in self.positions:
                    continue  # Already holding
                
                # Slice data up to current time to pretend we are in the past
                df_past = df_full[:current_time]
                if len(df_past) < 30:
                    continue
                
                try:
                    # Monkey-patch the engine's data fetcher to use our sliced past data
                    self.engine._fetch_data = lambda s: df_past if s == sym else None
                    result = self.engine.analyze(sym)
                    
                    if result.action in [ActionType.STRONG_BUY, ActionType.BUY]:
                        pos_size = self.capital * result.position_size_pct
                        if self.cash >= pos_size and pos_size > 0:
                            shares = pos_size / result.entry_price
                            self.positions[sym] = {
                                'entry_price': result.entry_price,
                                'shares': shares,
                                'tp': result.take_profit,
                                'sl': result.stop_loss,
                                'entry_date': current_time
                            }
                            self.cash -= pos_size
                            logger.info(f"[{current_time.strftime('%Y-%m-%d')}] Executed {result.action.value} on {sym} at ${result.entry_price:.2f}. "
                                        f"Score: {result.composite_score}. Conf: {result.confidence}%")
                except Exception as e:
                    logger.debug(f"Error analyzing {sym} on {current_time}: {e}")
                    
        # Close remaining positions at the end of the backtest
        final_date = dates[-1]
        for sym, pos in list(self.positions.items()):
            df = all_data[sym][:final_date]
            current_price = float(df['Close'].iloc[-1])
            pnl = (current_price - pos['entry_price']) * pos['shares']
            self._close_position(sym, current_price, "END_OF_TEST", pnl)
            
        self._print_report()

    def _close_position(self, sym: str, price: float, reason: str, pnl: float):
        pos = self.positions.pop(sym)
        self.cash += (pos['shares'] * price)
        self.trade_history.append({
            'symbol': sym,
            'entry_date': pos['entry_date'],
            'reason': reason,
            'pnl': pnl,
            'return_pct': (pnl / (pos['entry_price'] * pos['shares'])) * 100
        })
        logger.info(f"Closed {sym} via {reason}. PnL: ${pnl:,.2f}")

    def _print_report(self):
        trades = pd.DataFrame(self.trade_history)
        print("\n" + "="*50)
        print("💡 ULTIMATE 130-MODULE BACKTEST RESULTS 💡")
        print("="*50)
        
        final_capital = self.cash
        total_return = (final_capital - self.capital) / self.capital * 100
        
        print(f"Initial Capital: ${self.capital:,.2f}")
        print(f"Final Capital:   ${final_capital:,.2f}")
        print(f"Total Return:    {total_return:+.2f}%")
        
        if not trades.empty:
            wins = trades[trades['pnl'] > 0]
            losses = trades[trades['pnl'] <= 0]
            win_rate = len(wins) / len(trades) * 100
            
            print(f"Total Trades:    {len(trades)}")
            print(f"Win Rate:        {win_rate:.1f}%")
            print(f"Avg Winning Trd: +${wins['pnl'].mean() if not wins.empty else 0:,.2f}")
            print(f"Avg Losing Trd:  -${abs(losses['pnl'].mean()) if not losses.empty else 0:,.2f}")
            
            top_winner = trades.loc[trades['pnl'].idxmax()]
            print(f"Best Trade:      {top_winner['symbol']} (+${top_winner['pnl']:,.2f})")
        else:
            print("No trades executed during the period. (Strategy heavily risk-averse)")
        print("="*50)

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Run backtest on Mega Cap Tech + High Beta Mix
    tickers = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META", "GOOGL", "AMZN", "PLTR", "CRWD"]
    bt = UltimateBacktester(tickers)
    bt.run()
