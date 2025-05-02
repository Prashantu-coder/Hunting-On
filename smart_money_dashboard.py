import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import io
from datetime import timedelta
from google.oauth2 import service_account
from gsheetsdb import connect

# --- Page Setup ---
st.set_page_config(page_title="Quantexo Trading Signals", layout="wide")
st.title("📈 Advanced Smart Money Signals")

# --- Load Google Sheets Credentials ---
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
conn = connect(credentials=credentials)

# --- Company Symbol Search ---
company_symbol = st.text_input("🔍 Search Company Symbol (e.g., AAPL, TSLA)", "").strip().upper()

if company_symbol:
    # --- Fetch Data from Google Sheets ---
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_data(symbol):
        query = f"""
        SELECT 
            A as date, 
            C as open, 
            D as high, 
            E as low, 
            F as close, 
            G as volume 
        FROM "{st.secrets['private_gsheets_url']}"
        WHERE B = '{symbol}'
        ORDER BY A ASC
        """
        rows = conn.execute(query, headers=1)
        return pd.DataFrame(rows)

    df = fetch_data(company_symbol)

    if df.empty:
        st.error(f"No data found for symbol: {company_symbol}")
        st.stop()

    # --- Data Processing ---
    try:
        # Convert and validate data types
        df['date'] = pd.to_datetime(df['date'])
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        if df[numeric_cols].isnull().values.any():
            st.error("Invalid numeric data detected")
            st.stop()

        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)
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
        st.subheader(f"Smart Money Signals for {company_symbol}")
        
        # Tag filter
        tags_available = [tag for tag in df['tag'].unique() if tag]
        selected_tags = st.multiselect(
            "Filter Signals", 
            options=tags_available, 
            default=tags_available
        )

        # Interactive Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'],
            mode='lines', name='Price',
            line=dict(color='#1f77b4', width=2)
        ))

        # Add signals
        for tag in selected_tags:
            subset = df[df['tag'] == tag]
            fig.add_trace(go.Scatter(
                x=subset['date'], y=subset['close'],
                mode='markers+text',
                name=tag,
                marker=dict(size=12, symbol="diamond", line=dict(width=2)),
                textposition='top center'
            ))

        fig.update_layout(
            hovermode='x unified',
            template='plotly_dark',
            height=700
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Recent Signals Table ---
        st.subheader("📋 Recent Signals")
        last_date = df['date'].max()
        recent_df = df[(df['date'] > last_date - timedelta(days=30)) & (df['tag'] != '')]
        st.dataframe(
            recent_df[['date', 'open', 'high', 'low', 'close', 'volume', 'tag']]
            .sort_values('date', ascending=False)
            .style.format({
                'open': '{:.2f}', 'high': '{:.2f}', 
                'low': '{:.2f}', 'close': '{:.2f}'
            })
        )

        # --- Download Option ---
        csv = recent_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Recent Signals (CSV)",
            data=csv,
            file_name=f'{company_symbol}_signals.csv',
            mime='text/csv'
        )

    except Exception as e:
        st.error(f"Error processing data: {str(e)}")

else:
    st.info("ℹ️ Enter a company symbol to analyze trading signals")