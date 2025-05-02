import pandas as pd
import numpy as np

def detect_bullish_weak_leg(df):
    # Higher lows, weak follow-through in highs
    conditions = (
        (df['low'] > df['low'].shift(1)) &  # higher low
        (df['close'] < df['high']) &  # not closing strong
        (df['close'] < df['close'].shift(1))  # weakness after attempt
    )
    return conditions

def detect_bearish_weak_leg(df):
    conditions = (
        (df['high'] < df['high'].shift(1)) &  # lower high
        (df['close'] > df['low']) &  # not closing at lows
        (df['close'] > df['close'].shift(1))  # weakness after attempt
    )
    return conditions

def detect_buyers_absorption(df):
    # Long wicks to downside with increasing volume and small body
    body = abs(df['close'] - df['open'])
    wick = df['low'].shift(1) - df['low']
    conditions = (
        (wick > body * 1.5) &
        (df['volume'] > df['volume'].rolling(3).mean()) &
        (df['close'] > df['open'])  # bullish close
    )
    return conditions

def detect_sellers_absorption(df):
    body = abs(df['close'] - df['open'])
    wick = df['high'] - df['high'].shift(1)
    conditions = (
        (wick > body * 1.5) &
        (df['volume'] > df['volume'].rolling(3).mean()) &
        (df['close'] < df['open'])  # bearish close
    )
    return conditions

def detect_aggressive_buyers(df):
    # Strong green candles with increasing volume
    conditions = (
        (df['close'] > df['open']) &
        (df['close'] - df['open'] > df['range'].rolling(3).mean()) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )
    return conditions

def detect_aggressive_sellers(df):
    # Strong red candles with increasing volume
    conditions = (
        (df['close'] < df['open']) &
        (df['open'] - df['close'] > df['range'].rolling(3).mean()) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )
    return conditions

def prepare_dataframe(df):
    df['range'] = df['high'] - df['low']
    return df

def detect_all(df):
    df = prepare_dataframe(df)
    df['bullish_weak_leg'] = detect_bullish_weak_leg(df)
    df['bearish_weak_leg'] = detect_bearish_weak_leg(df)
    df['buyers_absorption'] = detect_buyers_absorption(df)
    df['sellers_absorption'] = detect_sellers_absorption(df)
    df['aggressive_buyers'] = detect_aggressive_buyers(df)
    df['aggressive_sellers'] = detect_aggressive_sellers(df)
    return df

# Example usage
# Load your OHLCV DataFrame from CSV or API
# df = pd.read_csv('data.csv')
# df = detect_all(df)
# print(df[df.any(axis=1)])  # Show rows with any signal

