import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')

def get_market_data():
    """Fetches 5 years of SPY and VIX data"""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=5*365)
    
    spy = yf.download("SPY", start=start_date, end=end_date, progress=False)
    vix = yf.download("^VIX", start=start_date, end=end_date, progress=False)
    
    # Flatten multi-index columns if yfinance returns them
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
        
    spy.columns = [c.lower() for c in spy.columns]
    vix.columns = [c.lower() for c in vix.columns]
    
    return spy, vix

def engineer_features(df_spy, df_vix):
    """Engineers the features based on the Jupyter notebook logic"""
    df = df_spy.copy()
    
    # 1. Target (for training)
    df['Target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # 2. Daily Return
    df['Daily_Return'] = df['close'].pct_change()
    
    # 3. High-Low Spread
    df['HL_Spread'] = (df['high'] - df['low']) / df['close']
    
    # 4. True Range (TR)
    df['TR'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                     abs(df['low'] - df['close'].shift(1))))
    df['TR_Norm'] = df['TR'] / df['close']
    
    # 5. On-Balance Volume (OBV)
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv
    df['OBV_ROC'] = df['OBV'].pct_change(5)
    
    # 6. Money Flow Multiplier (MFM) Proxy
    mfm_denom = df['high'] - df['low']
    mfm_denom = mfm_denom.replace(0, np.nan)
    df['MFM'] = ((df['close'] - df['low']) - (df['high'] - df['close'])) / mfm_denom
    df['MFM'].fillna(0, inplace=True)
    df['MFV'] = df['MFM'] * df['volume']
    
    # 7. VIX
    df_vix_close = df_vix[['close']].rename(columns={'close': 'VIX_Close'})
    df = df.join(df_vix_close)
    df['VIX_Change'] = df['VIX_Close'].pct_change()
    
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    
    return df

def train_and_predict(df):
    """Trains the RandomForest model and predicts the next day's trend"""
    feature_cols = ['Daily_Return', 'HL_Spread', 'TR_Norm', 'OBV_ROC', 'MFM', 'MFV', 'VIX_Close', 'VIX_Change']
    
    # We use all data EXCEPT the very last row for training
    # because the last row's "Target" (tomorrow's close) is unknown
    train_df = df.iloc[:-1]
    predict_row = df.iloc[-1:]
    
    X_train = train_df[feature_cols]
    y_train = train_df['Target']
    X_pred = predict_row[feature_cols]
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_pred_scaled = scaler.transform(X_pred)
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    prediction = model.predict(X_pred_scaled)[0]
    probabilities = model.predict_proba(X_pred_scaled)[0]
    
    # Ensure current_price is scalar by extracting the value
    current_price = predict_row['close'].iloc[0]
    if isinstance(current_price, pd.Series):
        current_price = current_price.iloc[0]
        
    return {
        "trend": "Up" if prediction == 1 else "Down",
        "confidence": probabilities[prediction] * 100,
        "current_price": current_price
    }

def run_engine():
    print("Fetching market data...")
    spy, vix = get_market_data()
    print("Engineering features...")
    df = engineer_features(spy, vix)
    print("Running model prediction...")
    result = train_and_predict(df)
    return result

if __name__ == "__main__":
    res = run_engine()
    print(f"\n--- SPY PREDICTION ---")
    print(f"Current Price: ${float(res['current_price']):.2f}")
    print(f"Predicted Trend: {res['trend']}")
    print(f"Confidence: {res['confidence']:.1f}%")
