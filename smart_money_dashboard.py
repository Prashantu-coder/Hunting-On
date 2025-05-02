import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import timedelta
import os

# --- Google Sheets authentication ---
def authenticate_google_sheets():
    # Define the scope and path to your credentials file
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Authenticate using the credentials file
    creds = ServiceAccountCredentials.from_json_keyfile_name(r'C:\Users\Dell\Downloads\quantexo-458612-3f15459a6740.json', scope)  # Replace 'credentials.json' with your credentials file path
    client = gspread.authorize(creds)
    return client

# --- Extract data from Google Sheets ---
def get_data_from_sheet(client, sheet_id, sheet_name, symbol):
    # Open the Google Sheet and extract the data
    sheet = client.open_by_key(sheet_id).worksheet(sheet_name)
    data = sheet.get_all_records()

    # Convert data into a DataFrame
    df = pd.DataFrame(data)

    # Convert all relevant columns to numeric, coerce errors to NaN
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    # Filter by company symbol
    df = df[df['company_symbol'].str.contains(symbol, case=False, na=False)]
    
    return df

# --- Page setup ---
st.set_page_config(page_title="Quantexo", layout="wide")
st.title("Advanced Insights for Bold Trades")

# --- Google Sheets Input ---
sheet_id = "1_pmG2oMSEk8VciNm2uqcshyvPPZBbjf-oKV59chgT1w"  # Replace with your actual sheet ID
sheet_name = "Daily Price"  # Replace with your actual sheet name

# Authenticate with Google Sheets
client = authenticate_google_sheets()

# --- Search for company symbol ---
company_symbol = st.text_input("Enter Company Symbol", "")

if company_symbol:
    # Extract data for the given company symbol
    try:
        df = get_data_from_sheet(client, sheet_id, sheet_name, company_symbol)

        # Check if data exists
        if not df.empty:
            df.sort_values('date', inplace=True)
            df.reset_index(drop=True, inplace=True)

            # ➕ Calculate point change
            df['point_change'] = df['close'].diff().fillna(0)

            # --- Signal Tagging ---
            df['tag'] = ''
            avg_volume = df['volume'].rolling(window=10).mean()

            for i in range(3, len(df) - 6):  # ensure room for lookahead
                row = df.iloc[i]
                prev = df.iloc[i - 1]
                next_candles = df.iloc[i + 1:i + 6]  # next 5 candles
                body = abs(row['close'] - row['open'])
                prev_body = abs(prev['close'] - prev['open'])
                recent_tags = df['tag'].iloc[max(0, i-4):i]

                # 🟢 Aggressive Buyers
                if (
                    row['close'] > row['open']
                    and row['close'] >= row['high'] - (row['high'] - row['low']) * 0.1
                    and row['volume'] > avg_volume[i]
                    and body > prev_body
                    and '🟢' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🟢'

                # 🔴 Aggressive Sellers
                elif (
                    row['open'] > row['close']
                    and row['close'] <= row['low'] + (row['high'] - row['low']) * 0.1
                    and row['volume'] > avg_volume[i] 
                    and body > prev_body
                    and '🔴' not in recent_tags.values
                ):
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

            # --- Filter tags ---   
            tags_available = [tag for tag in df['tag'].unique() if tag]
            selected_tags = st.multiselect("Select Signal(s) to View", options=tags_available, default=tags_available)

            # --- Plotting Chart ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['close'],
                mode='lines
