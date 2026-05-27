"""
Crypto Sentiment Indicator
=============================
Bitcoin as risk sentiment gauge.
"""

from dataclasses import dataclass
from typing import Optional
import yfinance as yf
from loguru import logger


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
        """Analyze crypto sentiment"""
        
        try:
            # Get BTC data
            btc = yf.download('BTC-USD', period='1mo', progress=False)
            if hasattr(btc.columns, 'get_level_values'):
                btc.columns = btc.columns.get_level_values(0)
            
            if btc.empty:
                return self._default()
            
            current = float(btc['Close'].iloc[-1])
            day_ago = float(btc['Close'].iloc[-2]) if len(btc) > 1 else current
            week_ago = float(btc['Close'].iloc[-7]) if len(btc) > 7 else current
            
            change_24h = (current / day_ago - 1) * 100
            change_7d = (current / week_ago - 1) * 100
            
            # Sentiment based on price action
            if change_7d < -20:
                sentiment = "EXTREME_FEAR"
                score = 10
            elif change_7d < -10:
                sentiment = "FEAR"
                score = 30
            elif change_7d > 20:
                sentiment = "EXTREME_GREED"
                score = 90
            elif change_7d > 10:
                sentiment = "GREED"
                score = 70
            else:
                sentiment = "NEUTRAL"
                score = 50
            
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
            
            return CryptoSentiment(
                btc_price=current,
                btc_change_24h=change_24h,
                btc_change_7d=change_7d,
                sentiment=sentiment,
                sentiment_score=score,
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
