"""
Crypto Sentiment Indicator
=============================
Bitcoin as risk sentiment gauge.
"""

from dataclasses import dataclass
from typing import Optional
import yfinance as yf
from loguru import logger
import time
import requests

# Module level cache for Fear & Greed index
_fng_cache = None
_fng_last_time = 0.0


@dataclass
class CryptoSentiment:
    btc_price: float
    btc_change_24h: float
    btc_change_7d: float
    
    # Sentiment
    sentiment: str  # "EXTREME_FEAR", "FEAR", "NEUTRAL", "GREED", "EXTREME_GREED"
    sentiment_score: int  # 0-100
    
    # Correlation to stocks
    correlation_signal: str  # "LEADING_DOWN", "LEADING_UP", "NEUTRAL"
    
    # Trading implication
    risk_indicator: str
    stock_impact: str
    recommendation: str


class CryptoSentimentIndicator:
    """
    Crypto as Risk Sentiment
    
    Why Bitcoin matters:
    1. Risk-on asset - leads stock moves
    2. Liquidity proxy - when BTC drops, liquidity leaving
    3. Tech correlation - especially Nasdaq
    4. Weekend indicator - crypto trades 24/7
    
    Signals:
    - BTC -10% in 24h → Stock trouble coming
    - BTC breaking ATH → Risk-on
    - BTC diverging from stocks → warning
    """
    
    def __init__(self):
        pass
    
    def analyze(self) -> CryptoSentiment:
        """Analyze crypto sentiment combining price action with live Fear & Greed Index"""
        global _fng_cache, _fng_last_time
        
        # 1. Fetch Alternative.me Fear & Greed Index
        fng_value = 50
        fng_classification = "NEUTRAL"
        now = time.time()
        
        if _fng_cache is not None and now - _fng_last_time < 7200:
            fng_value, fng_classification = _fng_cache
        else:
            try:
                resp = requests.get("https://api.alternative.me/fng/", timeout=5)
                if resp.status_code == 200:
                    res_json = resp.json()
                    if res_json.get("data"):
                        first = res_json["data"][0]
                        fng_value = int(first.get("value", 50))
                        fng_classification = first.get("value_classification", "NEUTRAL").upper()
                        _fng_cache = (fng_value, fng_classification)
                        _fng_last_time = now
            except Exception as e:
                logger.debug(f"Failed to fetch Alternative.me F&G index: {e}")
                if _fng_cache is not None:
                    # Fallback to expired cache if API fails
                    fng_value, fng_classification = _fng_cache
        
        try:
            # Download QQQ and BTC data (2mo to ensure we have enough data for 30-day correlation)
            qqq = yf.download('QQQ', period='2mo', progress=False)
            btc = yf.download('BTC-USD', period='2mo', progress=False)
            
            if hasattr(qqq.columns, 'get_level_values'):
                qqq.columns = qqq.columns.get_level_values(0)
            if hasattr(btc.columns, 'get_level_values'):
                btc.columns = btc.columns.get_level_values(0)
            
            if btc.empty:
                return self._default()
            
            # Calculate daily returns and rolling correlation
            correlation = 0.5
            is_decoupled = False
            if not qqq.empty:
                try:
                    import pandas as pd
                    qqq_close = qqq['Close']
                    btc_close = btc['Close']
                    if isinstance(qqq_close, pd.DataFrame):
                        qqq_close = qqq_close.iloc[:, 0]
                    if isinstance(btc_close, pd.DataFrame):
                        btc_close = btc_close.iloc[:, 0]
                        
                    df_aligned = pd.DataFrame({'QQQ': qqq_close, 'BTC': btc_close}).dropna()
                    returns = df_aligned.pct_change().dropna()
                    if len(returns) >= 15:
                        correlation = float(returns['QQQ'].corr(returns['BTC']))
                        # If correlation is weak (< 0.3) or negative, we treat it as decoupled
                        if correlation < 0.3:
                            is_decoupled = True
                except Exception as corr_err:
                    logger.debug(f"Correlation calculation failed: {corr_err}")
            
            current = float(btc['Close'].iloc[-1])
            day_ago = float(btc['Close'].iloc[-2]) if len(btc) > 1 else current
            week_ago = float(btc['Close'].iloc[-7]) if len(btc) > 7 else current
            
            change_24h = (current / day_ago - 1) * 100
            change_7d = (current / week_ago - 1) * 100
            
            # Sentiment based on price action
            if change_7d < -20:
                price_score = 10
            elif change_7d < -10:
                price_score = 30
            elif change_7d > 20:
                price_score = 90
            elif change_7d > 10:
                price_score = 70
            else:
                price_score = 50
                
            # Combine 50% price action score and 50% Fear & Greed index
            if is_decoupled:
                combined_score = 50  # Neutralized
                sentiment = "NEUTRAL"
            else:
                combined_score = int(price_score * 0.5 + fng_value * 0.5)
                
                if combined_score < 25:
                    sentiment = "EXTREME_FEAR"
                elif combined_score < 45:
                    sentiment = "FEAR"
                elif combined_score < 65:
                    sentiment = "NEUTRAL"
                elif combined_score < 85:
                    sentiment = "GREED"
                else:
                    sentiment = "EXTREME_GREED"
            
            # Correlation signal
            if change_24h < -5:
                corr = "LEADING_DOWN"
                risk = "HIGH"
                impact = "Crypto selling → stocks may follow"
            elif change_24h > 5:
                corr = "LEADING_UP"
                risk = "LOW"
                impact = "Crypto rallying → risk-on sentiment"
            else:
                corr = "NEUTRAL"
                risk = "NORMAL"
                impact = "No strong crypto signal"
            
            # Recommendation
            if is_decoupled:
                rec = f"F&G Index: {fng_value} ({fng_classification}) (IGNORED - decoupled, corr={correlation:.2f}) | Crypto decoupled from Nasdaq"
            else:
                if sentiment == "EXTREME_FEAR":
                    rec = "🚨 Crypto fear → expect stock volatility, reduce risk"
                elif sentiment == "FEAR":
                    rec = "⚠️ Crypto weak → caution on stock longs"
                elif sentiment == "EXTREME_GREED":
                    rec = "📈 Crypto euphoria → risk-on, but watch for reversal"
                elif sentiment == "GREED":
                    rec = "✅ Crypto strong → favorable for tech stocks"
                else:
                    rec = "Crypto neutral, no strong signal"
                
                # Prepend active index value and correlation to recommendation
                rec = f"F&G Index: {fng_value} ({fng_classification}) (corr={correlation:.2f}) | {rec}"
            
            return CryptoSentiment(
                btc_price=current,
                btc_change_24h=change_24h,
                btc_change_7d=change_7d,
                sentiment=sentiment,
                sentiment_score=combined_score,
                correlation_signal=corr,
                risk_indicator=risk,
                stock_impact=impact,
                recommendation=rec
            )
            
        except Exception as e:
            logger.debug(f"Crypto analysis error: {e}")
            return self._default()
    
    def _default(self) -> CryptoSentiment:
        return CryptoSentiment(
            0, 0, 0, "NEUTRAL", 50, "NEUTRAL", "UNKNOWN", "No data", "No crypto data"
        )


def get_crypto_sentiment() -> CryptoSentimentIndicator:
    return CryptoSentimentIndicator()


if __name__ == "__main__":
    print("Testing CryptoSentimentIndicator...")
    cs = CryptoSentimentIndicator()
    
    sig = cs.analyze()
    
    print(f"\n{'='*50}")
    print("CRYPTO SENTIMENT")
    print('='*50)
    print(f"BTC: ${sig.btc_price:,.0f}")
    print(f"24h: {sig.btc_change_24h:+.1f}%")
    print(f"7d: {sig.btc_change_7d:+.1f}%")
    print(f"\nSentiment: {sig.sentiment} ({sig.sentiment_score}/100)")
    print(f"Correlation: {sig.correlation_signal}")
    print(f"Risk: {sig.risk_indicator}")
    print(f"Impact: {sig.stock_impact}")
    print(f"\nRecommendation: {sig.recommendation}")
