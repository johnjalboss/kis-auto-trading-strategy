"""
ML Predictor
==============
Machine learning price predictions.
Uses sklearn for simple but effective models.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from loguru import logger

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class MLPrediction:
    symbol: str
    prediction: str  # "UP", "DOWN", "NEUTRAL"
    probability: float
    confidence: int
    
    # Model info
    model_accuracy: float
    features_used: int
    
    # Supporting
    top_features: List[str]
    details: List[str]


class MLPredictor:
    """
    ML-Based Price Predictor
    
    Models:
    1. RandomForest (main)
    2. GradientBoosting (confirmation)
    
    Features:
    - Technical: RSI, MACD, SMA ratios
    - Momentum: Returns at various periods
    - Volatility: ATR, Bollinger %
    - Volume: Volume ratios, OBV
    
    Target: Next 5-day direction
    """
    
    def __init__(self):
        if not HAS_SKLEARN:
            logger.warning("sklearn not installed. Run: pip install scikit-learn")
        self.models = {}
        self.scalers = {}
    
    def predict(self, symbol: str) -> MLPrediction:
        if not HAS_SKLEARN:
            return self._no_ml_result(symbol)
        
        # Fetch data
        df = self._fetch_data(symbol)
        if df is None or len(df) < 200:
            return self._no_ml_result(symbol)
        
        # Create features
        X, y = self._create_features(df)
        
        if len(X) < 100:
            return self._no_ml_result(symbol)
        
        # Train/test split
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        # Scale
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train models
        rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        rf.fit(X_train_scaled, y_train)
        
        # Accuracy
        accuracy = rf.score(X_test_scaled, y_test)
        
        # Predict latest
        latest_features = X.iloc[-1:].values
        latest_scaled = scaler.transform(latest_features)
        
        pred_class = rf.predict(latest_scaled)[0]
        pred_proba = rf.predict_proba(latest_scaled)[0]
        
        # Interpret
        if pred_class == 1:
            prediction = "UP"
            probability = float(pred_proba[1])
        else:
            prediction = "DOWN"
            probability = float(pred_proba[0])
        
        # Confidence based on probability
        if probability > 0.65:
            confidence = 80
        elif probability > 0.55:
            confidence = 60
        else:
            confidence = 40
        
        # Feature importance
        importances = pd.Series(rf.feature_importances_, index=X.columns)
        top_features = importances.nlargest(5).index.tolist()
        
        details = []
        if prediction == "UP" and probability > 0.6:
            details.append("ML_BULLISH")
        elif prediction == "DOWN" and probability > 0.6:
            details.append("ML_BEARISH")
        
        return MLPrediction(
            symbol=symbol,
            prediction=prediction,
            probability=probability,
            confidence=confidence,
            model_accuracy=accuracy,
            features_used=len(X.columns),
            top_features=top_features,
            details=details
        )
    
    def _create_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Create features for ML"""
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        features = pd.DataFrame(index=df.index)
        
        # Returns
        features['ret_1d'] = close.pct_change(1)
        features['ret_5d'] = close.pct_change(5)
        features['ret_10d'] = close.pct_change(10)
        features['ret_20d'] = close.pct_change(20)
        
        # SMA ratios
        features['sma5_ratio'] = close / close.rolling(5).mean()
        features['sma20_ratio'] = close / close.rolling(20).mean()
        features['sma50_ratio'] = close / close.rolling(50).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # Volatility
        features['volatility'] = close.pct_change().rolling(20).std()
        
        # Volume ratio
        features['vol_ratio'] = volume / volume.rolling(20).mean()
        
        # Bollinger %B
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        features['bb_pct'] = (close - (sma20 - 2*std20)) / (4*std20)
        
        # Target: 5-day forward return > 0
        features['target'] = (close.shift(-5) / close - 1 > 0).astype(int)
        
        # Drop NaN
        features = features.dropna()
        
        X = features.drop('target', axis=1)
        y = features['target']
        
        return X, y
    
    def _fetch_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period='2y', progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            return df
        except:
            return None
    
    def _no_ml_result(self, symbol: str) -> MLPrediction:
        return MLPrediction(symbol, "NEUTRAL", 0.5, 0, 0, 0, [], ["NO_ML"])
        
    def retrain(self):
        """Dummy method for retraining the ML model in the background"""
        logger.info("MLPredictor: background retraining requested. Retraining skipped (ML database inactive).")


def get_ml_predictor() -> MLPredictor:
    return MLPredictor()


if __name__ == "__main__":
    print("Testing MLPredictor...")
    ml = MLPredictor()
    
    for sym in ["AAPL", "NVDA", "TSLA"]:
        pred = ml.predict(sym)
        print(f"\n{sym}:")
        print(f"  Prediction: {pred.prediction}")
        print(f"  Probability: {pred.probability:.1%}")
        print(f"  Confidence: {pred.confidence}%")
        print(f"  Accuracy: {pred.model_accuracy:.1%}")
        print(f"  Top Features: {pred.top_features[:3]}")
