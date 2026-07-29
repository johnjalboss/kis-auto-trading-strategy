import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import os

warnings.filterwarnings('ignore')

from ultimate_backtest import UltimateIntegratedBacktester

def run_realistic_backtest(days=30, initial_capital=1500000):
    print(f"============================================================")
    print(f"🚀 실전 매매 기반 포트폴리오 1개월(30일) 백테스트 시작")
    print(f"============================================================")
    
    # 봇이 주로 타겟팅하는 변동성/모멘텀/빅테크 중심의 유니버스
    universe = [
        'NVDA', 'TSLA', 'AMD', 'PLTR', 'SOFI', 'COIN', 'MSTR', 'MARA', 
        'AAPL', 'MSFT', 'META', 'AMZN', 'GOOGL', 'UBER', 'RBLX', 'ARM',
        'TQQQ', 'SQQQ', 'UPRO', 'SOXL', 'SMCI', 'GME', 'AMC', 'INTC'
    ]
    
    end_date = datetime.now()
    # YFinance requires string formats, fetch extra 380 days for moving averages (trading days conversion)
    start_date = end_date - timedelta(days=days + 380)
    
    print(f"-> {len(universe)}개 핵심 모멘텀 종목들의 일봉 데이터 다운로드 중...")
    
    # Download all data
    data = yf.download(universe, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    
    # Check if download succeeded
    if data.empty:
        print("데이터 다운로드 실패!")
        return

    # Use ultimate backtester's scoring logic
    bt = UltimateIntegratedBacktester(initial_capital=initial_capital)
    
    # We will just get a static global macro score for the simulation
    global_signals = bt._get_global_signals()
    
    # Find the eval start index for the actual 'days' period
    # Since trading days are ~252/year
    eval_period_bars = int(days * (252 / 365.25))
    
    actual_dates = data.index.tolist()
    if len(actual_dates) < eval_period_bars + 200:
        print("데이터가 충분하지 않습니다 (최소 200일 MA 계산을 위한 과거 데이터 부족).")
        return
        
    eval_start_idx = len(actual_dates) - eval_period_bars
    
    # Portfolio tracking
    capital = initial_capital
    portfolio_equity_curve = []
    trade_log = []
    
    # For every day in the evaluation period
    for i in range(eval_start_idx, len(actual_dates)):
        current_date_dt = actual_dates[i]
        
        # 1. 시뮬레이션: 그날의 '거래량 급증' + '모멘텀' 스크리닝 (Top 3 종목 선정)
        daily_candidates = []
        for ticker in universe:
            try:
                # Get close prices up to today
                close_prices = data['Close'][ticker].values[:i+1]
                high_prices = data['High'][ticker].values[:i+1]
                low_prices = data['Low'][ticker].values[:i+1]
                volumes = data['Volume'][ticker].values[:i+1]
                
                # Skip if data is NaN
                if np.isnan(close_prices[-1]) or np.isnan(volumes[-1]):
                    continue
                
                # Volume surge calculation (current vol / 20d avg)
                avg_vol = np.nanmean(volumes[-21:-1])
                if avg_vol == 0 or np.isnan(avg_vol):
                    continue
                
                vol_surge = volumes[-1] / avg_vol
                
                # Trend calculation
                sma20 = pd.Series(close_prices).rolling(20).mean().values
                sma50 = pd.Series(close_prices).rolling(50).mean().values
                sma200 = pd.Series(close_prices).rolling(200).mean().values
                
                # RSI
                delta = pd.Series(close_prices).diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss.replace(0, 1)
                rsi = (100 - (100 / (1 + rs))).values
                
                # MACD
                ema12 = pd.Series(close_prices).ewm(span=12).mean().values
                ema26 = pd.Series(close_prices).ewm(span=26).mean().values
                macd = ema12 - ema26
                macd_signal = pd.Series(macd).ewm(span=9).mean().values
                
                bb_mid = pd.Series(close_prices).rolling(20).mean().values
                bb_std = pd.Series(close_prices).rolling(20).std().values
                bb_upper = bb_mid + 2 * bb_std
                bb_lower = bb_mid - 2 * bb_std
                
                # Calculate composite score just like the Ultimate Backtester
                score, confidence, risk_flags = bt._calculate_composite_score(
                    len(close_prices)-1, close_prices, sma20, sma50, sma200, 
                    rsi, macd, macd_signal, bb_upper, bb_lower, volumes, global_signals
                )
                
                daily_candidates.append({
                    'ticker': ticker,
                    'surge': vol_surge,
                    'score': score,
                    'confidence': confidence,
                    'price': close_prices[-1],
                    'risk': risk_flags
                })
            except Exception as e:
                continue
                
        # 2. 거래량 급증 + 점수 높은 상위 3개 타겟 추출
        daily_candidates.sort(key=lambda x: (x['score'], x['surge']), reverse=True)
        targets = daily_candidates[:3]
        
        # 3. 매수/매도 로직 시뮬레이션
        # 아주 단순화: 65점 이상이면 당일 매수해서 익일 종가 매도 (또는 손절가 터치 시 매도)
        day_pnl = 0
        allocated_capital_per_trade = capital * 0.25 # 한 종목당 자본금 25% 투입
        
        day_trades = []
        for t in targets:
            if t['score'] >= 60 and len(t['risk']) <= 1:
                # Buy!
                shares = allocated_capital_per_trade / t['price']
                
                # Next day simulate (Look ahead 1 step, but safely handled at end of arrays)
                if i + 1 < len(actual_dates):
                    next_open = data['Open'][t['ticker']].values[i+1]
                    next_close = data['Close'][t['ticker']].values[i+1]
                    next_low = data['Low'][t['ticker']].values[i+1]
                    
                    # Stop loss hit intraday? (-3%)
                    buy_price = t['price'] # Bought at close for simplicity
                    stop_price = buy_price * 0.97
                    
                    if next_low <= stop_price:
                        # Stopped out!
                        exit_price = stop_price
                        reason = "STOP_LOSS(-3%)"
                    else:
                        # Sold at next close
                        exit_price = next_close
                        reason = "TAKE_PROFIT/END_OF_DAY"
                        
                    profit = shares * (exit_price - buy_price)
                    capital += profit
                    day_pnl += profit
                    
                    trade_log.append({
                        'Date': current_date_dt.strftime('%Y-%m-%d'),
                        'Ticker': t['ticker'],
                        'Regime': 'RISK_ON' if global_signals['macro_score'] > 50 else 'RISK_OFF',
                        'Score': round(t['score'], 1),
                        'Buy': round(buy_price, 2),
                        'Sell': round(exit_price, 2),
                        'PnL': round(profit, 2),
                        'Result': 'WIN 📈' if profit > 0 else 'LOSS 📉',
                        'Reason': reason
                    })
        
        portfolio_equity_curve.append({
            'Date': current_date_dt.strftime('%Y-%m-%d'),
            'Equity': capital
        })
    
    # Results Analysis
    print(f"\n[ 시뮬레이션 완료. 결과 분석 ]")
    print(f"------------------------------------------------------------")
    if len(trade_log) == 0:
        print("시장 상황이 불안정하여 (점수 60 초과 종목 없음) 1달간 매매가 발생하지 않았습니다.")
        print("전략 방어력: 매우 우수 (원금 100% 보존)")
        return
        
    wins = [t for t in trade_log if t['PnL'] > 0]
    losses = [t for t in trade_log if t['PnL'] <= 0]
    
    win_rate = len(wins) / len(trade_log) * 100
    total_return_pct = ((capital - initial_capital) / initial_capital) * 100
    
    # Save log to DataFrame
    df_trades = pd.DataFrame(trade_log)
    print(df_trades.tail(15).to_string(index=False)) # 최근 15개 매매내역 요약
    print(f"------------------------------------------------------------")
    print(f"초기 자본:   {initial_capital:,.0f} KRW")
    print(f"최종 자본:   {capital:,.0f} KRW")
    print(f"총 수익률:   {total_return_pct:.2f}%")
    print(f"총 매매횟수: {len(trade_log)} 번")
    print(f"승    률:   {win_rate:.1f}%")
    
    # Max Drawdown
    equity_series = pd.Series([e['Equity'] for e in portfolio_equity_curve])
    peak = equity_series.expanding(min_periods=1).max()
    drawdown = (equity_series - peak) / peak * 100
    max_dd = drawdown.min()
    print(f"최대 손실폭(MDD): {max_dd:.2f}%")
    print(f"------------------------------------------------------------")
    print(f"실제 봇이 타겟을 스크리닝하고 단기 진입/손절하는 로직(오버나이트)을 반영한 결과입니다.")
    print(f"내역은 'realistic_backtest_trades.csv' 파일로 저장되었습니다.")
    
    df_trades.to_csv('realistic_backtest_trades.csv', index=False)
    
if __name__ == "__main__":
    run_realistic_backtest(days=30)
