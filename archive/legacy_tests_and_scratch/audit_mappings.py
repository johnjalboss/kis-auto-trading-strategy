import sys
import os
import yfinance as yf
from loguru import logger

# Add current dir to path
sys.path.append(os.getcwd())

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from trader import ExchangeMapper

def audit_mappings():
    mappings = ExchangeMapper.SYMBOL_EXCHANGE
    results = []
    
    print(f"Auditing {len(mappings)} mappings...")
    
    for symbol, mapped_exch in mappings.items():
        try:
            ticker = yf.Ticker(symbol)
            # Use fast_info if possible, or info
            real_exch = ticker.info.get('exchange')
            
            # KIS NASD -> NASDAQ, NGM, NMS
            # KIS NYSE -> NYQ, NYSE
            # KIS AMEX -> ASE, AMEX
            
            is_correct = False
            if mapped_exch == "NASD":
                if real_exch in ['NGM', 'NMS', 'NAS', 'NASDAQ', 'BTS', 'BATS', 'BATE']:
                    is_correct = True
            elif mapped_exch == "NYSE":
                if real_exch in ['NYQ', 'NYS', 'NYSE', 'PCX', 'ARCA', 'ASE', 'AMS', 'AMEX']:
                    is_correct = True
            elif mapped_exch == "AMEX":
                if real_exch in ['ASE', 'AMS', 'AMEX', 'PCX']:
                    is_correct = True
            
            if not is_correct:
                results.append(f"❌ {symbol}: Mapped to {mapped_exch}, but yfinance says {real_exch}")
            else:
                pass # Correct
                
        except Exception as e:
            results.append(f"⚠️ {symbol}: Error checking - {e}")
            
    if not results:
        print("✅ All mappings look correct!")
    else:
        for r in results:
            print(r)

if __name__ == "__main__":
    audit_mappings()
    
    universe = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NFLX",
        "NVDA", "AMD", "AVGO", "INTC", "MU", "QCOM", "TXN",
        "CRM", "ADBE", "NOW", "PANW", "CRWD", "PLTR",
        "JPM", "BAC", "GS", "V", "MA", "PYPL",
        "UNH", "LLY", "JNJ", "ABBV", "PFE",
        "WMT", "COST", "HD", "MCD", "SBUX",
        "XOM", "CVX", "CAT", "BA", "LMT",
        "SPY", "QQQ", "TQQQ", "SQQQ", "SOXL", "SOXS",
        "GLD", "TLT", "XLU"
    ]
    
    print("\n--- Checking FALLBACK_UNIVERSE coverage ---")
    mappings = ExchangeMapper.SYMBOL_EXCHANGE
    for s in universe:
        if s not in mappings:
            print(f"⚠️ {s} missing from ExchangeMapper")
