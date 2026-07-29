"""
MULTI-STOCK PORTFOLIO BACKTESTER
=================================
- Full stock screening across multiple universes
- Portfolio rebalancing on each period
- Options metrics (Max Pain, GEX) consideration
- Technical + Fundamental + Options scoring
- NO leverage

Strategy:
1. Screen universe for top stocks
2. Score each stock (Tech + Momentum + Options)  
3. Select top N stocks for portfolio
4. Rebalance periodically
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import json
warnings.filterwarnings('ignore')

# Try imports
try:
    from options_metrics import OptionsAnalyzer
    HAS_OPTIONS = True
except:
    HAS_OPTIONS = False
    print("[WARNING] options_metrics not loaded")


class StockScore:
    """Score for individual stock"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.technical_score = 50
        self.momentum_score = 50
        self.options_score = 50
        self.volume_score = 50
        self.total_score = 50
        self.data = None


class MultiStockBacktester:
    """
    MULTI-STOCK PORTFOLIO BACKTESTER
    
    Features:
    1. Universe screening (SP500, NASDAQ100, etc.)
    2. Multi-factor scoring
    3. Portfolio construction
    4. Regular rebalancing
    5. Options-based signals
    """
    
    # Stock Universe
    SP500_TOP50 = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JPM',
        'JNJ', 'V', 'PG', 'XOM', 'HD', 'MA', 'CVX', 'MRK', 'ABBV', 'PEP',
        'KO', 'COST', 'LLY', 'AVGO', 'MCD', 'WMT', 'CSCO', 'TMO', 'PFE', 'ACN',
        'CRM', 'DHR', 'ABT', 'NKE', 'DIS', 'VZ', 'ADBE', 'TXN', 'NFLX', 'CMCSA',
        'PM', 'INTC', 'NEE', 'HON', 'T', 'UNP', 'RTX', 'ORCL', 'AMD', 'BA'
    ]
    
    GROWTH_STOCKS = [
        'NVDA', 'TSLA', 'META', 'NFLX', 'AMD', 'AVGO', 'CRM', 'NOW', 'ADBE', 'PANW',
        'SNOW', 'CRWD', 'DDOG', 'ZS', 'NET', 'MDB', 'ABNB', 'UBER', 'SQ', 'SHOP'
    ]
    
    MOMENTUM_STOCKS = [
        'NVDA', 'SMCI', 'ARM', 'PLTR', 'CRWD', 'PANW', 'CEG', 'VST', 'AXON', 'FICO',
        'ANET', 'DECK', 'BLDR', 'URI', 'CDNS', 'SNPS', 'LRCX', 'KLAC', 'MRVL', 'ON'
    ]
    
    def __init__(self, initial_capital: float = 1500000, 
                 portfolio_size: int = 10,
                 rebalance_days: int = 5):
        self.initial_capital = initial_capital
        self.portfolio_size = portfolio_size
        self.rebalance_days = rebalance_days
        
        # Options analyzer
        if HAS_OPTIONS:
            self.options_analyzer = OptionsAnalyzer()
        else:
            self.options_analyzer = None
        
        self.trades = []
        self.portfolio_history = []
    
    def run_backtest(self, period_days: int = 365,
                     universe: str = "TOP50") -> Dict:
        """Run multi-stock portfolio backtest"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days + 60)  # Extra for warmup
        
        # Select universe
        if universe == "TOP50":
            symbols = self.SP500_TOP50
        elif universe == "GROWTH":
            symbols = self.GROWTH_STOCKS
        elif universe == "MOMENTUM":
            symbols = self.MOMENTUM_STOCKS
        else:
            symbols = self.SP500_TOP50
        
        print(f"\n{'='*70}")
        print("🚀 MULTI-STOCK PORTFOLIO BACKTEST 🚀")
        print(f"{'='*70}")
        print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: {self.initial_capital:,.0f} KRW")
        print(f"Universe: {universe} ({len(symbols)} stocks)")
        print(f"Portfolio Size: {self.portfolio_size} stocks")
        print(f"Rebalance Every: {self.rebalance_days} days")
        print()
        
        # Download all data
        print("[1/4] Downloading market data...")
        all_data = self._download_data(symbols, start_date, end_date)
        
        if not all_data:
            print("[ERROR] No data downloaded")
            return {}
        
        # Get benchmark (SPY)
        spy = yf.download('SPY', start=start_date.strftime('%Y-%m-%d'),
                         end=end_date.strftime('%Y-%m-%d'), progress=False)
        if hasattr(spy.columns, 'get_level_values'):
            spy.columns = spy.columns.get_level_values(0)
        
        # Run simulation
        print("[2/4] Running simulation...")
        results = self._simulate(all_data, spy)
        
        # Print results
        print("\n[3/4] RESULTS")
        print("-"*70)
        self._print_results(results)
        
        # Save details
        print("\n[4/4] Saving portfolio history...")
        self._save_results()
        
        return results
    
    def _download_data(self, symbols: List[str], 
                       start_date: datetime, 
                       end_date: datetime) -> Dict:
        """Download historical data for all symbols"""
        
        data = {}
        success = 0
        
        for i, sym in enumerate(symbols):
            try:
                df = yf.download(sym, 
                               start=start_date.strftime('%Y-%m-%d'),
                               end=end_date.strftime('%Y-%m-%d'),
                               progress=False)
                if hasattr(df.columns, 'get_level_values'):
                    df.columns = df.columns.get_level_values(0)
                
                if not df.empty and len(df) > 60:
                    data[sym] = df
                    success += 1
            except:
                pass
            
            if (i + 1) % 10 == 0:
                print(f"   Downloaded {i+1}/{len(symbols)}...")
        
        print(f"   Total: {success} stocks with data")
        return data
    
    def _simulate(self, all_data: Dict, spy: pd.DataFrame) -> Dict:
        """Run portfolio simulation with rebalancing"""
        
        # Get common date range
        dates = None
        for sym, df in all_data.items():
            if dates is None:
                dates = set(df.index.tolist())
            else:
                dates = dates.intersection(set(df.index.tolist()))
        
        dates = sorted(list(dates))
        
        # Skip warmup period
        start_idx = 60
        
        # Initialize portfolio
        capital = self.initial_capital
        cash = capital
        holdings = {}  # symbol -> shares
        
        peak = capital
        max_dd = 0
        
        # Track performance
        portfolio_values = [capital]
        benchmark_values = [spy['Close'].iloc[start_idx]]
        
        print(f"   Trading {len(dates) - start_idx} days...")
        
        rebalance_counter = 0
        
        for i in range(start_idx, len(dates)):
            date = dates[i]
            rebalance_counter += 1
            
            # Calculate current portfolio value
            portfolio_value = cash
            for sym, shares in holdings.items():
                if sym in all_data and date in all_data[sym].index:
                    price = all_data[sym].loc[date, 'Close']
                    portfolio_value += shares * price
            
            # Get benchmark
            if date in spy.index:
                bench_price = spy.loc[date, 'Close']
                benchmark_values.append(bench_price)
            
            # REBALANCE if needed
            if rebalance_counter >= self.rebalance_days:
                rebalance_counter = 0
                
                # Score all stocks
                scores = self._score_stocks(all_data, date, i)
                
                # Select top N
                top_stocks = sorted(scores, key=lambda x: x.total_score, reverse=True)[:self.portfolio_size]
                top_symbols = [s.symbol for s in top_stocks]
                
                # Sell stocks not in top N
                for sym in list(holdings.keys()):
                    if sym not in top_symbols:
                        if sym in all_data and date in all_data[sym].index:
                            price = all_data[sym].loc[date, 'Close']
                            proceeds = holdings[sym] * price
                            cash += proceeds
                            self.trades.append({
                                'date': str(date),
                                'symbol': sym,
                                'type': 'SELL',
                                'shares': holdings[sym],
                                'price': price,
                                'reason': 'Rebalance out'
                            })
                            del holdings[sym]
                
                # Recalculate portfolio value
                portfolio_value = cash
                for sym, shares in holdings.items():
                    if sym in all_data and date in all_data[sym].index:
                        portfolio_value += shares * all_data[sym].loc[date, 'Close']
                
                # Target allocation per stock
                target_per_stock = portfolio_value / self.portfolio_size
                
                # Buy/adjust positions
                for stock in top_stocks:
                    sym = stock.symbol
                    if sym not in all_data or date not in all_data[sym].index:
                        continue
                    
                    price = all_data[sym].loc[date, 'Close']
                    target_shares = target_per_stock / price
                    
                    current_shares = holdings.get(sym, 0)
                    
                    if target_shares > current_shares:
                        # Buy more
                        buy_shares = target_shares - current_shares
                        cost = buy_shares * price
                        if cost <= cash:
                            holdings[sym] = target_shares
                            cash -= cost
                            self.trades.append({
                                'date': str(date),
                                'symbol': sym,
                                'type': 'BUY',
                                'shares': buy_shares,
                                'price': price,
                                'score': stock.total_score,
                                'reason': f'Score {stock.total_score:.0f}'
                            })
                    elif target_shares < current_shares * 0.8:
                        # Reduce position
                        sell_shares = current_shares - target_shares
                        proceeds = sell_shares * price
                        holdings[sym] = target_shares
                        cash += proceeds
                        self.trades.append({
                            'date': str(date),
                            'symbol': sym,
                            'type': 'REDUCE',
                            'shares': sell_shares,
                            'price': price,
                            'reason': 'Rebalance'
                        })
                
                # Log rebalance
                self.portfolio_history.append({
                    'date': str(date),
                    'holdings': list(holdings.keys()),
                    'portfolio_value': portfolio_value,
                    'cash': cash
                })
            
            # Track values
            portfolio_values.append(portfolio_value)
            
            # Track drawdown
            peak = max(peak, portfolio_value)
            dd = (peak - portfolio_value) / peak * 100
            max_dd = max(max_dd, dd)
        
        # Final value
        final_value = cash
        for sym, shares in holdings.items():
            if sym in all_data:
                final_value += shares * all_data[sym]['Close'].iloc[-1]
        
        # Calculate returns
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        benchmark_return = (benchmark_values[-1] / benchmark_values[0] - 1) * 100 if benchmark_values else 0
        
        days = len(dates) - start_idx
        annual_return = total_return * (365 / days) if days > 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'benchmark_return': benchmark_return,
            'alpha': total_return - benchmark_return,
            'max_drawdown': max_dd,
            'final_capital': final_value,
            'total_trades': len(self.trades),
            'final_holdings': list(holdings.keys()),
            'rebalances': len(self.portfolio_history),
        }
    
    def _score_stocks(self, all_data: Dict, date, idx: int) -> List[StockScore]:
        """Score all stocks for selection"""
        
        scores = []
        
        for sym, df in all_data.items():
            if date not in df.index:
                continue
            
            score = StockScore(sym)
            
            try:
                # Get index position
                loc = df.index.get_loc(date)
                if loc < 20:
                    continue
                
                prices = df['Close'].values[:loc+1]
                volumes = df['Volume'].values[:loc+1]
                
                # TECHNICAL SCORE (30%)
                tech = 50
                sma20 = np.mean(prices[-20:])
                sma50 = np.mean(prices[-50:]) if len(prices) >= 50 else sma20
                
                current = prices[-1]
                if current > sma20 > sma50:
                    tech = 80
                elif current > sma20:
                    tech = 65
                elif current < sma20 < sma50:
                    tech = 30
                else:
                    tech = 45
                
                score.technical_score = tech
                
                # MOMENTUM SCORE (30%)
                mom = 50
                if len(prices) >= 20:
                    mom_20 = (prices[-1] / prices[-20] - 1) * 100
                    if mom_20 > 10:
                        mom = 90
                    elif mom_20 > 5:
                        mom = 75
                    elif mom_20 > 0:
                        mom = 60
                    elif mom_20 > -5:
                        mom = 40
                    else:
                        mom = 25
                
                score.momentum_score = mom
                
                # VOLUME SCORE (20%)
                vol = 50
                if len(volumes) >= 20:
                    vol_avg = np.mean(volumes[-20:])
                    vol_ratio = volumes[-1] / vol_avg if vol_avg > 0 else 1
                    if vol_ratio > 2 and mom > 50:
                        vol = 80  # High volume + up = bullish
                    elif vol_ratio > 1.5:
                        vol = 65
                    elif vol_ratio < 0.5:
                        vol = 35
                
                score.volume_score = vol
                
                # OPTIONS SCORE (20%) - simplified for backtest
                # In real trading, this would use live options data
                opt = 50
                
                # Use RSI as proxy
                if len(prices) >= 14:
                    delta = np.diff(prices[-15:])
                    gain = np.mean([d for d in delta if d > 0]) if any(d > 0 for d in delta) else 0
                    loss = np.mean([-d for d in delta if d < 0]) if any(d < 0 for d in delta) else 0.01
                    rsi = 100 - (100 / (1 + gain/loss))
                    
                    if 40 < rsi < 60:
                        opt = 70  # Healthy
                    elif rsi < 30:
                        opt = 80  # Oversold
                    elif rsi > 70:
                        opt = 40  # Overbought
                
                score.options_score = opt
                
                # TOTAL SCORE
                score.total_score = (
                    score.technical_score * 0.30 +
                    score.momentum_score * 0.30 +
                    score.volume_score * 0.20 +
                    score.options_score * 0.20
                )
                
                scores.append(score)
                
            except Exception as e:
                pass
        
        return scores
    
    def _print_results(self, results: Dict):
        """Print results"""
        ret = results.get('total_return', 0)
        ann = results.get('annual_return', 0)
        bench = results.get('benchmark_return', 0)
        alpha = results.get('alpha', 0)
        
        print(f"Total Trades:     {results.get('total_trades', 0)}")
        print(f"Rebalances:       {results.get('rebalances', 0)}")
        print(f"Total Return:     {'+' if ret > 0 else ''}{ret:.2f}%")
        print(f"Annual Return:    {'+' if ann > 0 else ''}{ann:.2f}%")
        print(f"Benchmark (SPY):  {'+' if bench > 0 else ''}{bench:.2f}%")
        print()
        
        if alpha > 0:
            print(f"🏆 ALPHA:          +{alpha:.2f}% (BEAT THE MARKET!) 🏆")
        else:
            print(f"Alpha:            {alpha:.2f}%")
        
        print(f"\nMax Drawdown:     {results.get('max_drawdown', 0):.2f}%")
        print(f"Final Capital:    {results.get('final_capital', 0):,.0f} KRW")
        
        print(f"\nFinal Holdings:   {', '.join(results.get('final_holdings', []))}")
    
    def _save_results(self):
        """Save results to files"""
        
        with open('portfolio_trades.json', 'w') as f:
            json.dump(self.trades, f, indent=2)
        print(f"   [✓] Trades saved to portfolio_trades.json")
        
        with open('portfolio_history.json', 'w') as f:
            json.dump(self.portfolio_history, f, indent=2)
        print(f"   [✓] History saved to portfolio_history.json")


def run_multistock_backtest():
    """Run multi-stock backtests"""
    
    results = {}
    
    # 1 Year with TOP50
    print("\n### 1 YEAR - TOP 50 UNIVERSE ###")
    bt = MultiStockBacktester(
        initial_capital=1500000,
        portfolio_size=10,
        rebalance_days=5
    )
    results['1yr_top50'] = bt.run_backtest(period_days=365, universe="TOP50")
    
    # 1 Year with MOMENTUM
    print("\n### 1 YEAR - MOMENTUM UNIVERSE ###")
    bt = MultiStockBacktester(
        initial_capital=1500000,
        portfolio_size=10,
        rebalance_days=5
    )
    results['1yr_momentum'] = bt.run_backtest(period_days=365, universe="MOMENTUM")
    
    # 3 Years with TOP50
    print("\n### 3 YEARS - TOP 50 UNIVERSE ###")
    bt = MultiStockBacktester(
        initial_capital=1500000,
        portfolio_size=10,
        rebalance_days=5
    )
    results['3yr_top50'] = bt.run_backtest(period_days=1095, universe="TOP50")
    
    # Summary
    print(f"\n{'='*70}")
    print("🏆 FINAL SUMMARY - MULTI-STOCK PORTFOLIO 🏆")
    print(f"{'='*70}")
    
    for name, res in results.items():
        if res:
            alpha_icon = "🏆" if res['alpha'] > 0 else "📊"
            print(f"{name}: Return {res['total_return']:+.2f}% | "
                  f"Alpha {res['alpha']:+.2f}% {alpha_icon} | "
                  f"Trades {res['total_trades']} | "
                  f"MDD {res['max_drawdown']:.2f}%")
    
    return results


if __name__ == "__main__":
    run_multistock_backtest()
