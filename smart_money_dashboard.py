import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
import gspread
import urllib.parse
import io
from datetime import timedelta
import os

# Check if the file exists
json_keyfile = '/path/to/your/service_account_file.json'  # Update this with the correct path

if os.path.exists(json_keyfile):
    print("JSON key file found.")
else:
    print(f"JSON key file not found at {json_keyfile}")

# 🔧 Google Sheet setup
SHEET_ID = "1_pmG2oMSEk8VciNm2uqcshyvPPZBbjf-oKV59chgT1w"  # Replace with your Google Sheet ID
json_keyfile = 'C:\Users\Dell\Downloads\quantexo-458612-3f15459a6740.json'  # Replace with the path to your downloaded JSON key file

# 📋 UI
st.set_page_config(page_title="Quantexo", layout="wide")
st.title("📊 Smart Money Stock Dashboard")

company = st.text_input("Search Company", placeholder="e.g., UpperTamakoshi")

# Authenticate and access Google Sheets
def authenticate_google_sheets(json_keyfile):
    credentials = Credentials.from_service_account_file(
        json_keyfile,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(credentials)
    return gc

# 📥 Load and display data from Google Sheets
def load_sheet_data(company):
    gc = authenticate_google_sheets(json_keyfile)
    
    # Open the sheet by ID
    try:
        worksheet = gc.open_by_key(SHEET_ID).sheet1
        data = worksheet.get_all_records()

        # Convert data to DataFrame
        df = pd.DataFrame(data)

        # Search for company in Column B and filter rows where the company name matches
        company_data = df[df['Company'] == company]  # Assuming column B has 'Company'

        # If the company is found, extract the relevant columns and return the data
        if not company_data.empty:
            company_data = company_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            company_data['Date'] = pd.to_datetime(company_data['Date'])
            company_data = company_data.sort_values('Date')
            company_data['Volume'] = pd.to_numeric(company_data['Volume'], errors='coerce')
            return company_data
        else:
            st.error(f"Company '{company}' not found in the Google Sheet.")
            return None

    except Exception as e:
        st.error(f"Failed to load data from Google Sheets. Error: {e}")
        return None

# --- Signal Detection Logic ---
def detect_signals(df):
    df['point_change'] = df['Close'].diff().fillna(0)

    # Signal tagging logic
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

        # 📉 Bullish Weak Legs
        elif (
            df['point_change'].iloc[i] > 0
            and row['Close'] > row['Open']
            and body < 0.3 * prev_body
            and row['Volume'] < avg_volume[i] * 1.1
        ):
            df.at[i, 'tag'] = '📉'

        # 📈 Bearish Weak Legs
        elif (
            df['point_change'].iloc[i] < 0
            and row['Open'] > row['Close']
            and body < 0.3 * prev_body
            and row['Volume'] < avg_volume[i] * 1.1
        ):
            df.at[i, 'tag'] = '📈'

    return df

# If company is provided, fetch data and visualize
if company:
    df = load_sheet_data(company)

    if df is not None:
        # Detect signals
        df = detect_signals(df)

        # 📈 Plot closing price with signal tags
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines', name='Close Price'))
        
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
            'Buyer Absorption':'Buyer Absorption',
            'Seller Absorption' : 'Seller Absorption'
        }

        # Plot signal markers
        for tag in df['tag'].unique():
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
            xaxis=dict(title="Date", tickangle=-45, showgrid=False),
            yaxis=dict(title="Price", showgrid=True, gridcolor="gray", zeroline=True),
            margin=dict(l=50, r=50, b=150, t=50),
        )

        st.plotly_chart(fig, use_container_width=True)

        # 📋 Display data for recent month
        st.subheader("📋 Recent 1 Month Data")
        last_date = df['Date'].max()
        one_month_ago = last_date - pd.Timedelta(days=30)
        recent_df = df[df['Date'] >= one_month_ago]

        st.dataframe(recent_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].sort_values('Date', ascending=False))

        # --- Download Excel File ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            recent_df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_excel(writer, index=False, sheet_name='Recent Data')
        processed_data = output.getvalue()

        st.download_button(
            label="📥 Download 1 Month Data as Excel",
            data=processed_data,
            file_name=f'{company}_recent_1_month_data.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
