import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Signal tag map
signal_tags = {
    'aggressive_buyers': '🟢',
    'aggressive_sellers': '🔴',
    'buyers_absorption': '⛔',
    'sellers_absorption': '🚀',
    'bullish_por': '💥',
    'bearish_por': '💣',
    'bullish_poi': '🐂',
    'bearish_poi': '🐻',
    'bullish_weak_leg': '📉',
    'bearish_weak_leg': '📈'
}

# File loader
def load_csv(file):
    df = pd.read_csv(file, parse_dates=['Date'])
    df.rename(columns={
        'Date': 'time',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }, inplace=True)
    df.set_index('time', inplace=True)
    df['range'] = df['high'] - df['low']
    return df

# Signal Detection Logic
def detect_bullish_weak_leg(df):
    return (
        (df['low'] > df['low'].shift(1)) &
        (df['close'] < df['high']) &
        (df['close'] < df['close'].shift(1))
    )

def detect_bearish_weak_leg(df):
    return (
        (df['high'] < df['high'].shift(1)) &
        (df['close'] > df['low']) &
        (df['close'] > df['close'].shift(1))
    )

def detect_buyers_absorption(df):
    body = abs(df['close'] - df['open'])
    wick = df['low'].shift(1) - df['low']
    return (
        (wick > body * 1.5) &
        (df['volume'] > df['volume'].rolling(3).mean()) &
        (df['close'] > df['open'])
    )

def detect_sellers_absorption(df):
    body = abs(df['close'] - df['open'])
    wick = df['high'] - df['high'].shift(1)
    return (
        (wick > body * 1.5) &
        (df['volume'] > df['volume'].rolling(3).mean()) &
        (df['close'] < df['open'])
    )

def detect_aggressive_buyers(df):
    return (
        (df['close'] > df['open']) &
        (df['close'] - df['open'] > df['range'].rolling(3).mean()) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )

def detect_aggressive_sellers(df):
    return (
        (df['close'] < df['open']) &
        (df['open'] - df['close'] > df['range'].rolling(3).mean()) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )

def detect_bullish_por(df):
    body = df['close'] - df['open']
    prev_body = df['close'].shift(1) - df['open'].shift(1)
    engulfing = (df['open'] < df['close'].shift(1)) & (df['close'] > df['open'].shift(1))
    return (
        engulfing &
        (body > prev_body.abs()) &
        (df['low'] < df['low'].shift(1)) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )

def detect_bearish_por(df):
    body = df['open'] - df['close']
    prev_body = df['open'].shift(1) - df['close'].shift(1)
    engulfing = (df['open'] > df['close'].shift(1)) & (df['close'] < df['open'].shift(1))
    return (
        engulfing &
        (body > prev_body.abs()) &
        (df['high'] > df['high'].shift(1)) &
        (df['volume'] > df['volume'].rolling(3).mean())
    )

def detect_bullish_poi(df):
    body = abs(df['close'] - df['open'])
    small_range = df['range'].rolling(3).mean() < df['range'].rolling(7).mean() * 0.8
    breakout = (df['close'] > df['high'].shift(1)) & (body > df['range'].rolling(3).mean())
    return small_range & breakout

def detect_bearish_poi(df):
    body = abs(df['open'] - df['close'])
    small_range = df['range'].rolling(3).mean() < df['range'].rolling(7).mean() * 0.8
    breakout = (df['close'] < df['low'].shift(1)) & (body > df['range'].rolling(3).mean())
    return small_range & breakout

def detect_all(df):
    df['bullish_weak_leg'] = detect_bullish_weak_leg(df)
    df['bearish_weak_leg'] = detect_bearish_weak_leg(df)
    df['buyers_absorption'] = detect_buyers_absorption(df)
    df['sellers_absorption'] = detect_sellers_absorption(df)
    df['aggressive_buyers'] = detect_aggressive_buyers(df)
    df['aggressive_sellers'] = detect_aggressive_sellers(df)
    df['bullish_por'] = detect_bullish_por(df)
    df['bearish_por'] = detect_bearish_por(df)
    df['bullish_poi'] = detect_bullish_poi(df)
    df['bearish_poi'] = detect_bearish_poi(df)
    return df

# Streamlit UI
st.title("📊 Price Action Signal Detector")
uploaded_file = st.file_uploader("Upload CSV file with OHLCV data", type=["csv"])

if uploaded_file is not None:
    df = load_csv(uploaded_file)
    df = detect_all(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name='Close Price'))

    for col, tag in signal_tags.items():
        if col in df.columns:
            signal_points = df[df[col]]
            fig.add_trace(go.Scatter(
                x=signal_points.index,
                y=signal_points['close'],
                mode='markers+text',
                name=tag,
                text=[tag] * len(signal_points),
                textposition="top center",
                marker=dict(size=10)
            ))

    fig.update_layout(title="Price Line Chart with Signals",
                      xaxis_title="Time",
                      yaxis_title="Price",
                      template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df.tail(20))