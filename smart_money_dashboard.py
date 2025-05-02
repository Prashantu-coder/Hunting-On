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

# Authenticate using the credentials in the secrets.toml file
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)

# Authenticate and open the Google Sheet
client = gspread.authorize(creds)

# Access the sheet using its URL (from secrets.toml)
spreadsheet_url = st.secrets["gsheet"]["url"]
sheet = client.open_by_url(spreadsheet_url).sheet1

# Example: Print the first 5 rows of the sheet
rows = sheet.get_all_records()
st.write(rows[:5])

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
    @st.cache_data(ttl=3600)
    def get_sheet_data(symbol):
        try:
            sheet = gc.open_by_url(sheet_url).worksheet("OHLCV")
            data = sheet.get_all_records(value_render_option='UNFORMATTED_VALUE')
            df = pd.DataFrame(data)

            col_mapping = {
                'date': ['date', 'Date', 'DATE'],
                'symbol': ['symbol', 'Symbol', 'SYMBOL', 'Ticker'],
                'open': ['open', 'Open', 'OPEN'],
                'high': ['high', 'High', 'HIGH'],
                'low': ['low', 'Low', 'LOW'],
                'close': ['close', 'Close', 'CLOSE'],
                'volume': ['volume', 'Volume', 'VOLUME']
            }

            for standard_name, variants in col_mapping.items():
                for variant in variants:
                    if variant in df.columns:
                        df.rename(columns={variant: standard_name}, inplace=True)

            return df[df['symbol'].str.upper() == symbol.upper()]
        except Exception as e:
            st.error(f"🔴 Error fetching data: {str(e)}")
            return pd.DataFrame()

    df = get_sheet_data(company_symbol)

    if df.empty:
        st.warning(f"No data found for {company_symbol}")
        st.stop()

    try:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        df.dropna(subset=['date'] + numeric_cols, inplace=True)

        if df.empty:
            st.error("No valid data after cleaning")
            st.stop()

        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)

        df['point_change'] = df['close'].diff().fillna(0)
        df['tag'] = ''
        avg_volume = df['volume'].rolling(window=10).mean()

        for i in range(3, len(df) - 6):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            next_candles = df.iloc[i + 1:i + 6]
            body = abs(row['close'] - row['open'])
            prev_body = abs(prev['close'] - prev['open'])
            recent_tags = df['tag'].iloc[max(0, i - 4):i]

            if (
                row['close'] > row['open'] and
                row['close'] >= row['high'] - (row['high'] - row['low']) * 0.1 and
                row['volume'] > avg_volume[i] and
                body > prev_body and
                '🟢' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '🟢'

            elif (
                row['open'] > row['close'] and
                row['close'] <= row['low'] + (row['high'] - row['low']) * 0.1 and
                row['volume'] > avg_volume[i] and
                body > prev_body and
                '🔴' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '🔴'

            elif (
                row['close'] > row['open'] and
                body > (row['high'] - row['low']) * 0.6 and
                row['volume'] > avg_volume[i] * 1.2
            ):
                if all(candle['close'] < row['open'] for _, candle in next_candles.iterrows()):
                    df.at[i, 'tag'] = '⛔'

            elif (
                row['open'] > row['close'] and
                body > (row['high'] - row['low']) * 0.6 and
                row['volume'] > avg_volume[i] * 1.2 and
                all(candle['close'] > row['open'] for _, candle in next_candles.iterrows())
            ):
                df.at[i, 'tag'] = '🚀'

            elif (
                i >= 10 and
                row['high'] > max(df['high'].iloc[i - 10:i]) and
                row['volume'] > avg_volume[i] * 1.8
            ):
                if not (df['tag'].iloc[i - 3:i] == '💥').any():
                    df.at[i, 'tag'] = '💥'

            elif (
                i >= 10 and
                row['low'] < min(df['low'].iloc[i - 10:i]) and
                row['volume'] > avg_volume[i] * 1.8
            ):
                if not (df['tag'].iloc[i - 3:i] == '💣').any():
                    df.at[i, 'tag'] = '💣'

            elif (
                row['close'] > row['open'] and
                body > (row['high'] - row['low']) * 0.7 and
                row['volume'] > avg_volume[i] * 2
            ):
                df.at[i, 'tag'] = '🐂'

            elif (
                row['open'] > row['close'] and
                body > (row['high'] - row['low']) * 0.7 and
                row['volume'] > avg_volume[i] * 2
            ):
                df.at[i, 'tag'] = '🐻'

            elif (
                df['point_change'].iloc[i] > 0 and
                row['close'] > row['open'] and
                body < 0.3 * prev_body and
                row['volume'] < avg_volume[i] * 1.1
            ):
                df.at[i, 'tag'] = '📉'

            elif (
                df['point_change'].iloc[i] < 0 and
                row['open'] > row['close'] and
                body < 0.3 * prev_body and
                row['volume'] < avg_volume[i] * 1.1
            ):
                df.at[i, 'tag'] = '📈'

            elif (
                row['open'] > row['close'] and
                body >= 0.3 * prev_body and
                row['volume'] < avg_volume[i] * 1.1 and
                prev['close'] > prev['open'] and
                '⚠️ D' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '⚠️ D'

            elif (
                row['close'] > row['open'] and
                body >= 0.3 * prev_body and
                row['volume'] < avg_volume[i] * 1.1 and
                prev['open'] > prev['close'] and
                '⚠️ R' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '⚠️ R'

        # --- Visualization ---
        st.subheader(f"{company_symbol} - Smart Money Line Chart")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'],
            mode='lines', name='Close Price',
            line=dict(color='lightblue', width=2),
            hovertext=df['close'],
            hoverinfo="x+y+text"
        ))

        tag_labels = {
            '🟢': '🟢 Aggressive Buyers',
            '🔴': '🔴 Aggressive Sellers',
            '⛔': '⛔ Buyer Absorption',
            '🚀': '🚀 Seller Absorption',
            '💥': '💥 Bullish POR',
            '💣': '💣 Bearish POR',
            '🐂': '🐂 Bullish POI',
            '🐻': '🐻 Bearish POI',
            '📉': '📉 Bullish Weak Legs',
            '📈': '📈 Bearish Weak Legs',
            '⚠️ D': '⚠️ Fake Drop',
            '⚠️ R': '⚠️ Fake Rise'
        }

        signals = df[df['tag'] != '']
        for tag in signals['tag'].unique():
            subset = signals[signals['tag'] == tag]
            fig.add_trace(go.Scatter(
                x=subset['date'], y=subset['close'],
                mode='markers+text',
                name=tag_labels.get(tag, tag),
                text=[tag] * len(subset),
                textposition='top center',
                textfont=dict(size=20),
                marker=dict(size=14, symbol="circle", color='white'),
                customdata=subset[['open', 'high', 'low', 'close', 'point_change']].values,
                hovertemplate=(
                    "📅 Date: %{x|%Y-%m-%d}<br>" +
                    "🟢 Open: %{customdata[0]:.2f}<br>" +
                    "📈 High: %{customdata[1]:.2f}<br>" +
                    "📉 Low: %{customdata[2]:.2f}<br>" +
                    "🔚 Close: %{customdata[3]:.2f}<br>" +
                    "📊 Point Change: %{customdata[4]:.2f}<br>" +
                    f"{tag_labels.get(tag, tag)}<extra></extra>"
                )
            ))

        fig.update_layout(
            height=800,
            plot_bgcolor="black",
            paper_bgcolor="black",
            font_color="white",
            legend=dict(font=dict(size=14)),
            title="Smart Money Signals Chart",
            xaxis=dict(title="Date", tickangle=-45, showgrid=False),
            yaxis=dict(title="Price", showgrid=True, gridcolor="gray", zeroline=True, zerolinecolor="gray"),
            margin=dict(l=50, r=50, b=150, t=50)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Recent 1 Month Signal Observed")
        last_date = df['date'].max()
        one_month_ago = last_date - timedelta(days=30)
        recent_df = df[(df['date'] >= one_month_ago) & (df['tag'] != '')]

        st.dataframe(recent_df[['date', 'open', 'high', 'low', 'close', 'point_change', 'volume', 'tag']].sort_values('date', ascending=False))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            recent_df[['date', 'open', 'high', 'low', 'close', 'point_change', 'volume', 'tag']].to_excel(writer, index=False, sheet_name='Signals')
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Download 1 Month Signals as Excel",
            data=processed_data,
            file_name='recent_1_month_signals.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")
else:
    st.info("ℹ️ Enter a company symbol to begin analysis")
