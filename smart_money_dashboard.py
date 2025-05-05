import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import io
from datetime import datetime, timedelta
import pytz
import kaleido

# --- Page Setup ---
st.set_page_config(page_title="Quantexo", layout="wide")

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stApp {
        background-color: darkslategray;
    }
    </style>
    <div class='header-container'>
        <div class='header-title'>Quantexo🕵️</div>
        <div class='header-subtitle'>💰 Advanced Insights for Bold Trades</div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Company Search ---
col1, col2 = st.columns([3,1])
with col1:
    user_input = st.text_input("🔍 Search Company Symbol","", label_visibility="collapsed")
with col2: search_clicked = st.button("Search")

company_symbol = user_input.strip().upper() if search_clicked else""

if company_symbol:
    @st.cache_data(ttl=3600)
    def get_sheet_data(symbol, sheet_name="Daily Price"):
        try:
            # Google Sheets URL with the specific sheet's gid
            sheet_url = f"https://docs.google.com/spreadsheets/d/1xNH6LHi4JYLTXr2D8Ds9q74Z2ujocmkXJFx5qlJJUac/export?format=csv&gid={get_sheet_gid(sheet_name)}"
            
            # Read data as CSV directly (no auth needed if public)
            df = pd.read_csv(sheet_url)

            # Ensure only the first 7 columns are used (ignoring any additional columns)
            df = df.iloc[:, :7]  # Select only the first 7 columns

            # Define the columns based on the new column mappings
            df.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']

            # Filter data based on company symbol
            df['symbol'] = df['symbol'].astype(str).str.strip().str.upper()
            return df[df['symbol'].str.upper() == symbol.upper()]
        except Exception as e:
            st.error(f"🔴 Error fetching data: {str(e)}")
            return pd.DataFrame()

    def get_sheet_gid(sheet_name):
        # You need to know the gid value of the sheet, or you can find it in the sheet's URL when editing the sheet
        sheet_gids = {
            "Daily Price": 0,  # Default sheet (GID of Sheet1)
            # Add more sheets here with their respective GIDs
        }
        return sheet_gids.get(sheet_name, 0)  # Default to GID 0 if sheet_name not found

    sheet_name = "Daily Price"
    df = get_sheet_data(company_symbol, sheet_name)

    if df.empty:
        st.warning(f"No data found for {company_symbol}")
        st.stop()

    try:
        # Convert column names to lowercase
        df.columns = [col.lower() for col in df.columns]

        # Check required columns
        required_cols = {'date', 'open', 'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(set(df.columns)):
            st.error("❌ Missing required columns: date, open, high, low, close, volume")
            st.stop()

        # Convert and validate dates
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].isnull().any():
            st.error("❌ Invalid date format in some rows")
            st.stop()

        # Validate numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('[^\d.]', '', regex=True),  # Remove non-numeric chars
                errors='coerce'
            )
            if df[col].isnull().any():
                bad_rows = df[df[col].isnull()][['date', col]].head()
                st.error(f"❌ Found {df[col].isnull().sum()} invalid values in {col} column. Examples:")
                st.dataframe(bad_rows)
                st.stop()

        # Remove any rows with NA values
        df = df.dropna()
        if len(df) == 0:
            st.error("❌ No valid data after cleaning")
            st.stop()

        # Sort and reset index
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        # ===== END OF ADDED VALIDATION =====

        df['point_change'] = df['close'].diff().fillna(0)
        df['tag'] = ''
        avg_volume = df['volume'].rolling(window=20).mean()

        for i in range(3, len(df) - 6):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            next_candles = df.iloc[i + 1:i + 6]
            body = abs(row['close'] - row['open'])
            prev_body = abs(prev['close'] - prev['open'])
            recent_tags = df['tag'].iloc[max(0, i - 4):i]

            if (
                row['close'] > row['open'] and
                row['close'] >= row['high'] - (row['high'] - row['low']) * 0.2 and
                row['volume'] > avg_volume[i] and
                body > prev_body and
                '🟢' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '🟢'

            elif (
                row['open'] > row['close'] and
                row['close'] <= row['low'] + (row['high'] - row['low']) * 0.2 and
                row['volume'] > avg_volume[i] and
                body > prev_body and
                '🔴' not in recent_tags.values
            ):
                df.at[i, 'tag'] = '🔴'
            elif (
                row['close'] > row['open'] and
                row['volume'] > avg_volume[i] * 1.2
            ):
                 # Remove only existing ⛔ tags
                df.loc[df['tag'] == '⛔', 'tag'] = ''

                for j, candle in next_candles.iterrows():
                    if candle['close'] < row['open']:  # Bearish confirmation
                        df.at[j, 'tag'] = '⛔'  # Tag FIRST bearish candle closing below
                        break  # Stop after first occurrence
            elif (
                row['open'] > row['close'] and
                row['volume'] > avg_volume[i] * 1.2 
            ):
                 # Remove only existing 🚀 tags
                df.loc[df['tag'] == '🚀', 'tag'] = ''

                for j, candle in next_candles.iterrows():  # Check next 5 candles
                    if candle['close'] > row['open']:  # Price recovers above bearish candle's open
                        df.at[j, 'tag'] = '🚀'  # Tag the rejection candle
                        break  # Stop at first confirmation
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

        # --- Visualization ---
        # st.subheader(f"{company_symbol} - Smart Money Line Chart")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'],
            mode='lines', name='Close Price',
            line=dict(color='lightblue', width=2),
            customdata=df[['date', 'close', 'point_change']],
            hovertemplate=(
                "📅 Date: %{customdata[0]|%Y-%m-%d}<br>" +
                "💰 LTP: %{customdata[1]:.2f}<br>" +
                "📊 Point Change: %{customdata[2]:.2f}<extra></extra>"
            )
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
            '📈': '📈 Bearish Weak Legs'
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
        # Calculate one month ahead of the last date
        last_date = df['date'].max()
        extended_date = last_date + timedelta(days=30)
        fig.update_layout(
            height=800,
            width=1800,
            plot_bgcolor="darkslategray",
            paper_bgcolor="darkslategray",
            font_color="white",
            title="Smart Money Signals Chart",
            xaxis=dict(title="Date", tickangle=-45, showgrid=False, range=[df['date'].min(),extended_date]), #extend x-axis to show space after latest date
            yaxis=dict(title="Price", showgrid=False, zeroline=True, zerolinecolor="gray"),
            margin=dict(l=50, r=50, b=150, t=50),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.3,  # Adjust this value to move further down if needed
                xanchor="center",
                x=0.5,
                font=dict(size=14),
                bgcolor="rgba(0,0,0,0)"  # Optional: keeps legend background transparent),
            )
        )
        st.plotly_chart(fig, use_container_width=False)
        
        nepali_tz = pytz.timezone('Asia/Kathmandu')
        now = datetime.now(nepali_tz)
        timestamp_str = now.strftime("%Y-%B-%d_%I-%M%p")
        img_name = f"{company_symbol}_{timestamp_str}_Quantexo🕵️_NEPSE"
        img_bytes = fig.to_image(format="png")
        st.download_button(
            label="📥 Download Chart as PNG",
            data=img_bytes,
            file_name=img_name,
            mime="image/png"
        )

        st.subheader(" 🔍📅 Recent 1 Month Signal Observed")
        last_date = df['date'].max()
        one_month_ago = last_date - timedelta(days=30)
        recent_df = df[(df['date'] >= one_month_ago) & (df['tag'] != '')]
        recent_df['tag_description'] = recent_df['tag'].map(tag_labels)

        st.dataframe(recent_df[['date', 'open', 'high', 'low', 'close', 'point_change', 'volume', 'tag_description']].sort_values('date', ascending=False))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            recent_df[['date', 'open', 'high', 'low', 'close', 'point_change', 'volume', 'tag_description']].rename(columns={'tag_description':'Signa Description'}).to_excel(writer, index=False, sheet_name=f'Signals Detected for - {company_symbol}')
        processed_data = output.getvalue()

        nepali_tz = pytz.timezone('Asia/Kathmandu')
        now = datetime.now(nepali_tz)
        timestamp_str = now.strftime("%Y-%B-%d_%I-%M%p")
        file_name = f"1_Months_Signal_{company_symbol}_{timestamp_str}_Quantexo🕵️_NEPSE"

        st.download_button(
            label="📥 Download 1 Month Signals as Excel",
            data=processed_data,
            file_name=file_name,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")

else:
    st.info("ℹ️ Enter a company symbol to begin analysis")