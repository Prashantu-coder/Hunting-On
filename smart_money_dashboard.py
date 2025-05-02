import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import io
from datetime import timedelta
import gspread
from google.oauth2 import service_account

# --- Page Setup ---
st.set_page_config(page_title="Quantexo Trading Signals", layout="wide")
st.title("📈 Advanced Smart Money Signals")

# --- Load Google Sheets Credentials ---
try:
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sheet_url = st.secrets["private_gsheets_url"]
except Exception as e:
    st.error(f"🔴 Failed to authenticate: {str(e)}")
    st.stop()

# --- Company Search ---
company_symbol = st.text_input("🔍 Search Company Symbol", "").strip().upper()

if company_symbol:
    # --- Fetch Data ---
    @st.cache_data(ttl=3600)
    def get_sheet_data(symbol):
        try:
            sheet = gc.open_by_url(sheet_url).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            return df[df['Symbol'] == symbol]  # Assuming column B is named 'Symbol'
        except Exception as e:
            st.error(f"🔴 Error fetching data: {str(e)}")
            return pd.DataFrame()

    df = get_sheet_data(company_symbol)

    if df.empty:
        st.warning(f"No data found for {company_symbol}")
        st.stop()

    # --- Data Processing ---
    try:
        # Rename columns to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Convert datatypes
        df['date'] = pd.to_datetime(df['date'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
        
        # Sort and calculate changes
        df = df.sort_values('date').reset_index(drop=True)
        df['point_change'] = df['close'].diff().fillna(0)

        # --- Signal Detection Algorithm ---
        df['tag'] = ''
        avg_volume = df['volume'].rolling(window=10).mean()

        for i in range(3, len(df) - 6):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            next_candles = df.iloc[i + 1:i + 6]
            body = abs(row['close'] - row['open'])
            prev_body = abs(prev['close'] - prev['open'])
            recent_tags = df['tag'].iloc[max(0, i-4):i]

            # Signal Logic (same as your original)
            if (row['close'] > row['open']
                and row['close'] >= row['high'] - (row['high'] - row['low']) * 0.1
                and row['volume'] > avg_volume[i]
                and body > prev_body
                and '🟢' not in recent_tags.values):
                df.at[i, 'tag'] = '🟢'
                
            elif (row['open'] > row['close']
                  and row['close'] <= row['low'] + (row['high'] - row['low']) * 0.1
                  and row['volume'] > avg_volume[i]
                  and body > prev_body
                  and '🔴' not in recent_tags.values):
                df.at[i, 'tag'] = '🔴'
            
            # ⛔ Buyer Absorption
            elif (
                row['close'] > row['open']
                and body > (row['high'] - row['low']) * 0.6
                and row['volume'] > avg_volume[i] * 1.2
            ):
                if all(candle['close'] < row['open'] for _, candle in next_candles.iterrows()):
                    df.at[i, 'tag'] = '⛔'

            # 🚀 Seller Absorption
            elif (
                row['open'] > row['close']
                and body > (row['high'] - row['low']) * 0.6
                and row['volume'] > avg_volume[i] * 1.2
                and all(candle['close'] > row['open'] for _, candle in next_candles.iterrows())
            ):
                    df.at[i, 'tag'] = '🚀'


            # 💥 Bullish POR
            elif (
                i >= 10 and
                row['high'] > max(df['high'].iloc[i - 10:i])
                and row['volume'] > avg_volume[i] * 1.8
            ):
                if not (df['tag'].iloc[i - 3:i] == '💥').any():
                    df.at[i, 'tag'] = '💥'

            # 💣 Bearish POR
            elif (
                i >= 10 and
                row['low'] < min(df['low'].iloc[i - 10:i])
                and row['volume'] > avg_volume[i] * 1.8
            ):
                if not (df['tag'].iloc[i - 3:i] == '💣').any():
                    df.at[i, 'tag'] = '💣'

            # 🐂 Bullish POI
            elif (
                row['close'] > row['open']
                and body > (row['high'] - row['low']) * 0.7
                and row['volume'] > avg_volume[i] * 2
            ):
                df.at[i, 'tag'] = '🐂'

            # 🐻 Bearish POI
            elif (
                row['open'] > row['close']
                and body > (row['high'] - row['low']) * 0.7
                and row['volume'] > avg_volume[i] * 2
            ):
                df.at[i, 'tag'] = '🐻'

            # 📉 Bullish Weak Legs (updated)
            elif (
                df['point_change'].iloc[i] > 0
                and row['close'] > row['open']
                and body < 0.3 * prev_body
                and row['volume'] < avg_volume[i] * 1.1
            ):
                df.at[i, 'tag'] = '📉'

            # 📈 Bearish Weak Legs (updated)
            elif (
                df['point_change'].iloc[i] < 0
                and row['open'] > row['close']
                and body < 0.3 * prev_body
                and row['volume'] < avg_volume[i] * 1.1
            ):
                df.at[i, 'tag'] = '📈'
            
            # ⚠️ Fake Drop - Large bearish candle but weak volume
            elif ( 
                row['open'] > row['close']
                and body >= 0.3 * prev_body
                and row['volume'] < avg_volume[i] * 1.1
                and prev['close'] > prev['open']
                and '⚠️ D' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '⚠️ D'

            # ⚠️ Fake Rise - Large bullish candle but weak volume
            elif (
                row['close'] > row['open']
                and body >= 0.3 * prev_body
                and row['volume'] < avg_volume[i] *1.1
                and prev['open'] > prev['close']
                and '⚠️ R' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '⚠️ R'
        
        # --- Visualization ---
        st.subheader(f"{company_symbol} Trading Signals")
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ))
        
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")

else:
    st.info("ℹ️ Enter a company symbol to begin analysis")