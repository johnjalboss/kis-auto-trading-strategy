import sys
import os
import pandas as pd
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

from strategy import StrategyEngine, Position, MarketPhase
import config

def diag_pltd():
    engine = StrategyEngine()
    
    # Mock position based on pltd_dump.txt
    # entry_time 2026-02-28 03:50:11.469997, price 8.36
    from datetime import datetime
    entry_time = datetime.strptime("2026-02-28 03:50:11", "%Y-%m-%d %H:%M:%S")
    
    # We need ATR at entry. Let's fetch some data to estimate it.
    df = engine.fetch_data("PLTD")
    if df is None:
        print("Could not fetch data for PLTD")
        return
    
    from indicators import calculate_atr
    atr_series = calculate_atr(df)
    atr_at_entry = atr_series.loc[:"2026-02-28"].iloc[-1] if not atr_series.loc[:"2026-02-28"].empty else atr_series.iloc[0]
    
    print(f"Estimated ATR at entry: {atr_at_entry}")
    
    pos = Position(
        symbol="PLTD",
        entry_price=8.36,
        quantity=1,
        entry_time=entry_time,
        atr_at_entry=atr_at_entry,
        high_since_entry=8.36, # Start with entry price
        phase_at_entry=MarketPhase.MIDDAY
    )
    
    engine._positions["PLTD"] = pos
    
    # Check current price
    import yfinance as yf_raw
    ticker = yf_raw.Ticker("PLTD")
    curr_price = ticker.fast_info['last_price']
    print(f"Current Price: {curr_price}")
    
    signal = engine.check_exit("PLTD", realtime_price=curr_price)
    print(f"Exit Signal: {signal}")
    
    # Check stop price calculation
    stop_price = pos.entry_price - (pos.atr_at_entry * config.ATR_STOP_MULTIPLIER)
    print(f"Stop Price (Midday): {stop_price}")
    
    # Check if it was Opening
    stop_price_opening = pos.entry_price - (pos.atr_at_entry * max(config.ATR_STOP_MULTIPLIER * 1.2, 2.0))
    print(f"Stop Price (Opening): {stop_price_opening}")

if __name__ == "__main__":
    diag_pltd()
