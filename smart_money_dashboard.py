import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import urllib.parse
import io
from datetime import timedelta

# --- Page setup ---
st.set_page_config(page_title="Quantexo", layout="wide")
st.title("📊 Smart Money Stock Dashboard")

# 🔧 Your shared Google Sheet ID
SHEET_ID = "1_pmG2oMSEk8VciNm2uqcshyvPPZBbjf-oKV59chgT1w"  # Replace with your actual Google Sheet ID

# 📋 Search for company input
company = st.text_input("Daily Price", placeholder="e.g., UpperTamakoshi")

if company:
    # 📋 Sanitize the company name to match the sheet name
    sheet_name = company.strip().replace(" ", "")
    
    # 📥 Build GSheet CSV URL for specific sheet/tab
    gsheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"

    try:
        # 📥 Load the data from Google Sheets
        df = pd.read_csv(gsheet_url)
        
        # Make sure 'Date', 'Close', and 'Volume' columns exist
        if not all(col in df.columns for col in ['Date', 'Close', 'Volume']):
            st.error(f"Missing required columns in '{company}' sheet. Ensure 'Date', 'Close', and 'Volume' columns are present.")
        else:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values('Date')

            # Clean volume column and handle non-numeric values gracefully
            df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')

            # ➕ Calculate point change
            df['point_change'] = df['Close'].diff().fillna(0)

            # --- Signal Tagging ---
            df['tag'] = ''
            avg_volume = df['Volume'].rolling(window=10).mean()

            for i in range(3, len(df) - 6):  # ensure room for lookahead
                row = df.iloc[i]
                prev = df.iloc[i - 1]
                next_candles = df.iloc[i + 1:i + 6]  # next 5 candles
                body = abs(row['Close'] - row['Open'])
                prev_body = abs(prev['Close'] - prev['Open'])
                recent_tags = df['tag'].iloc[max(0, i-4):i]

                # 🟢 Aggressive Buyers
                if (
                    row['Close'] > row['Open']
                    and row['Close'] >= row['High'] - (row['High'] - row['Low']) * 0.1
                    and row['Volume'] > avg_volume[i]
                    and body > prev_body
                    and '🟢' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🟢'

                # 🔴 Aggressive Sellers
                elif (
                    row['Open'] > row['Close']
                    and row['Close'] <= row['Low'] + (row['High'] - row['Low']) * 0.1
                    and row['Volume'] > avg_volume[i] 
                    and body > prev_body
                    and '🔴' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🔴'

                # ⛔ Buyer Absorption
                elif (
                    row['Close'] > row['Open']
                    and body > (row['High'] - row['Low']) * 0.6
                    and row['Volume'] > avg_volume[i] * 1.2
                ):
                    if all(candle['Close'] < row['Open'] for _, candle in next_candles.iterrows()):
                        df.at[i, 'tag'] = '⛔'

                # 🚀 Seller Absorption
                elif (
                    row['Open'] > row['Close']
                    and body > (row['High'] - row['Low']) * 0.6
                    and row['Volume'] > avg_volume[i] * 1.2
                    and all(candle['Close'] > row['Open'] for _, candle in next_candles.iterrows())
                ):
                        df.at[i, 'tag'] = '🚀'


                # 💥 Bullish POR
                elif (
                    i >= 10 and
                    row['High'] > max(df['High'].iloc[i - 10:i])
                    and row['Volume'] > avg_volume[i] * 1.8
                ):
                    if not (df['tag'].iloc[i - 3:i] == '💥').any():
                        df.at[i, 'tag'] = '💥'

                # 💣 Bearish POR
                elif (
                    i >= 10 and
                    row['Low'] < min(df['Low'].iloc[i - 10:i])
                    and row['Volume'] > avg_volume[i] * 1.8
                ):
                    if not (df['tag'].iloc[i - 3:i] == '💣').any():
                        df.at[i, 'tag'] = '💣'

                # 🐂 Bullish POI
                elif (
                    row['Close'] > row['Open']
                    and body > (row['High'] - row['Low']) * 0.7
                    and row['Volume'] > avg_volume[i] * 2
                ):
                    df.at[i, 'tag'] = '🐂'

                # 🐻 Bearish POI
                elif (
                    row['Open'] > row['Close']
                    and body > (row['High'] - row['Low']) * 0.7
                    and row['Volume'] > avg_volume[i] * 2
                ):
                    df.at[i, 'tag'] = '🐻'

                # 📉 Bullish Weak Legs (updated)
                elif (
                    df['point_change'].iloc[i] > 0
                    and row['Close'] > row['Open']
                    and body < 0.3 * prev_body
                    and row['Volume'] < avg_volume[i] * 1.1
                ):
                    df.at[i, 'tag'] = '📉'

                # 📈 Bearish Weak Legs (updated)
                elif (
                    df['point_change'].iloc[i] < 0
                    and row['Open'] > row['Close']
                    and body < 0.3 * prev_body
                    and row['Volume'] < avg_volume[i] * 1.1
                ):
                    df.at[i, 'tag'] = '📈'
                
                # ⚠️ Fake Drop - Large bearish candle but weak volume
                elif ( 
                    row['Open'] > row['Close']
                    and body >= 0.3 * prev_body
                    and row['Volume'] < avg_volume[i] * 1.1
                    and prev['Close'] > prev['Open']
                    and '⚠️ D' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '⚠️ D'

                # ⚠️ Fake Rise - Large bullish candle but weak volume
                elif (
                    row['Close'] > row['Open']
                    and body >= 0.3 * prev_body
                    and row['Volume'] < avg_volume[i] *1.1
                    and prev['Open'] > prev['Close']
                    and '⚠️ R' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '⚠️ R'


            # --- Filter tags ---
            tags_available = [tag for tag in df['tag'].unique() if tag]
            selected_tags = st.multiselect("Select Signal(s) to View", options=tags_available, default=tags_available)

            # --- Plotting Chart ---
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Close'],
                mode='lines', name='Close Price',
                line=dict(color='lightblue', width=2),
                hovertext=df['Close'],
                hoverinfo="x+y+text"
            ))

            # Tag descriptions
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
                '⚠️ R': '⚠️ Fake Rise',
                'Buyer Absorption':'Buyer Absorption',
                'Seller Absorption' : 'Seller Absorption'
            }

            for tag in selected_tags:
                subset = df[df['tag'] == tag]
                fig.add_trace(go.Scatter(
                    x=subset['Date'], y=subset['Close'],
                    mode='markers+text',
                    name=tag_labels.get(tag, tag),
                    text=[tag] * len(subset),
                    textposition='top center',
                    textfont=dict(size=20),
                    marker=dict(size=14, symbol="circle", color='white'),
                    customdata=subset[['Open', 'High', 'Low', 'Close', 'point_change']].values,
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
                xaxis=dict(
                    title="Date",
                    tickangle=-45,
                    showgrid=False
                ),
                yaxis=dict(
                    title="Price",
                    showgrid=True,
                    gridcolor="gray",
                    zeroline=True,
                    zerolinecolor="gray",
                ),
                margin=dict(l=50, r=50, b=150, t=50),
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- Table for last 1 month signals ---
            st.subheader("📋 Recent 1 Month Signal Observed")
            last_date = df['Date'].max()
            one_month_ago = last_date - timedelta(days=60)
            recent_df = df[(df['Date'] >= one_month_ago) & (df['tag'] != '')]

            st.dataframe(recent_df[['Date', 'Open', 'High', 'Low', 'Close', 'point_change', 'tag']])

    except Exception as e:
        st.error(f"Failed to load data for '{company}'. Error: {e}")
