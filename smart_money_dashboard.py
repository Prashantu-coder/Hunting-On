# -*- coding: utf-8 -*-

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import io
from datetime import datetime, timedelta
import pytz
import kaleido
import plotly.io as pio

# --- Page Setup ---

st.set_page_config(page_title="Quantexo", layout="wide")

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """ <style>
    .stApp {
    background-color: darkslategray;
    } </style> <div class='header-container'> <div class='header-title'>Quantexo🕵️</div> <div class='header-subtitle'>💰 Advanced Insights for Bold Trades</div> </div>
    """,
    unsafe_allow_html=True
)
# --- SECTOR TO COMPANY MAPPING ---
sector_to_companies ={
    "Commercial Banks": {"ADBL","CZBIL","EBL","GBIME","HBL","KBL","LSL","MBL","NABIL","NBL","NICA","NIMB","NMB","PCBL","PRVU","SANIMA","SBI","SBL","SCB"},
    "Development Banks": {"CORBL","EDBL","GBBL","GRDBL","JBBL","KSBBL","LBBL","MDB","MLBL","MNBBL","NABBC","SADBL","SAPDBL","SHINE","SINDU"},
    "Finance": {"BFC","CFCL","GFCL","GMFIL","GUFL","ICFC","JFL","MFIL","MPFL","NFS","PFL","PROFL","RLFL","SFCL","SIFC"},
    "Hotels": {"CGH","CITY","KDL","OHL","SHL","TRH"},
    "Hydro Power": {"AHPC", "AHL", "AKJCL", "AKPL", "API", "BARUN", "BEDC", "BHDC", "BHPL", "BGWT", "BHL", "BNHC", "BPCL", "CHCL", "CHL", "CKHL", "DHPL", "DOLTI", "DORDI", "EHPL", "GHL", "GLH", "GVL", "HDHPC", "HHL", "HPPL", "HURJA", "IHL", "JOSHI", "KKHC", "KPCL", "KBSH", "LEC", "MAKAR", "MANDU", "MBJC", "MEHL", "MEL", "MEN", "MHCL", "MHNL", "MKHC", "MKHL", "MKJC", "MMKJL", "MHL", "MCHL", "MSHL", "NGPL", "NHDL", "NHPC", "NYADI", "PPL", "PHCL", "PMHPL", "PPCL", "RADHI", "RAWA", "RHGCL", "RFPL", "RIDI", "RHPL", "RURU", "SAHAS", "SHEL", "SGHC", "SHPC", "SIKLES", "SJCL", "SMH", "SMHL", "SMJC", "SPC", "SPDL", "SPHL", "SPL", "SSHL", "TAMOR", "TPC", "TSHL", "TVCL", "UHEWA", "ULHC", "UMHL", "UMRH", "UNHPL", "UPCL", "UPPER", "USHL", "USHEC", "VLUCL"},
    "Investment": {"CHDC","CIT","ENL","HATHY","HIDCL","NIFRA","NRN"},
    "Life Insurance":{"ALICL","CLI","CREST","GMLI","HLI","ILI","LICN","NLIC","NLICL","PMLI","RNLI","SJLIC","SNLI","SRLI"},
    "Manufacturing and Processing": {"BNL","BNT","GCIL","HDL","NLO","OMPL","SARBTM","SHIVM","SONA","UNL"},
    "Microfinance": {"ACLBSL","ALBSL","ANLB","AVYAN","CBBL","CYCL","DDBL","DLBS","FMDBL","FOWAD","GBLBS","GILB","GLBSL","GMFBS","HLBSL","ILBS","JBLB","JSLBB","KMCDB","LLBS","MATRI","MERO","MLBBL","MLBS","MLBSL","MSLB","NADEP","NESDO","NICLBSL","NMBMF","NMFBS","NMLBBL","NUBL","RSDC","SAMAJ","SHLB","SKBBL","SLBBL","SLBSL","SMATA","SMB","SMFBS","SMPDA","SWBBL","SWMF","ULBSL","UNLB","USLB","VLBS","WNLB"},
    "Non Life Insurance": {"HEI","IGI","NICL","NIL","NLG","NMIC","PRIN","RBCL","SALICO","SGIC"},
    "Others": {"HRL","MKCL","NRIC","NRM","NTC","NWCL"},
    "Trading": {"BBC","STC"}
}
#---UI LAYOUT---
col1, col2, col3, col4 =st.columns([0.8,0.8,0.8,0.8])

# --- Sector Selection ---
with col1:
    selected_sector = st.selectbox("Select Sector",placeholder="Select Sector",options=[""]+ list(sector_to_companies.keys()),label_visibility= "collapsed")
# ---Filter Companies based on Sector ---
with col2:
    if selected_sector:
        filered_companies = sorted(sector_to_companies[selected_sector])
    else:
        filered_companies =[]
    
    selected_dropdown = st.selectbox(
        "Select Company",
        options=[""]+ filered_companies,
        index=0,
        label_visibility= "collapsed",
        key="company"
    )
# ---Manual Input---
with col3:
    user_input = st.text_input(
        "🔍 Enter Company Symbol",
        "",
        label_visibility= "collapsed",
        placeholder= "🔍 Enter Company Symbol"
    )
with col4:
    st.write("")
    search_clicked = st.button("Search")
    label_visibility= "collapsed"
# --- Priority: Manual Entry Overries Dropdown ---
if search_clicked:
    if user_input.strip():
        company_symbol = user_input.strip().upper()
    elif selected_dropdown:
        company_symbol = selected_dropdown
    else:
        st.warning("⚠️ Please enter or select a company.")
        company_symbol = ""
else:
    company_symbol = ""
    
if company_symbol:
    @st.cache_data(ttl=3600)
    def get_sheet_data(symbol, sheet_name="Daily Price"):
        try:
            # Google Sheets URL with the specific sheet's gid
            sheet_url = f"https://docs.google.com/spreadsheets/d/1Q_En7VGGfifDmn5xuiF-t_02doPpwl4PLzxb4TBCW0Q/export?format=csv&gid={get_sheet_gid(sheet_name)}"

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
        
        # Dynamically adjust the rolling window size based on available data
        min_window = min(20, max(5, len(df) // 2))  # Use at least 5 days, at most 20, or half the data
        
        # Calculate rolling average with adjusted window size
        avg_volume = df['volume'].rolling(window=min_window).mean()
        
        # Ensure we have some valid rolling average values before proceeding
        if avg_volume.notna().sum() > 0:
            # Fill NaN values with the first valid value
            avg_volume = avg_volume.fillna(method='bfill').fillna(df['volume'].mean())
            
            # Modified loop to process all available data including the most recent
            # Important: Changed the range to include all data points
            for i in range(min(3, len(df)-1), len(df)):
                row = df.iloc[i]
                prev = df.iloc[i - 1]
                next_candles = df.iloc[i + 1:min(i + 6, len(df))]
                is_last_candle = (i == len(df) - 1)  # Flag for last candle

                body = abs(row['close'] - row['open'])
                prev_body = abs(prev['close'] - prev['open'])
                recent_tags = df['tag'].iloc[max(0, i - 4):i]

                # --- Signals that DON'T require future data (always checked) ---
                if (
                    row['close'] > row['open'] and
                    row['close'] >= row['high'] - (row['high'] - row['low']) * 0.1 and
                    row['volume'] > avg_volume[i] * 1.5 and
                    body > prev_body and
                    '🟢' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🟢'

                elif (
                    row['open'] > row['close'] and
                    row['close'] <= row['low'] + (row['high'] - row['low']) * 0.1 and
                    row['volume'] > avg_volume[i] * 1.5 and
                    body > prev_body and
                    '🔴' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🔴'

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
                    row['volume'] < avg_volume[i] * 0.5
                ):
                    df.at[i, 'tag'] = '📉'

                elif (
                    df['point_change'].iloc[i] < 0 and
                    row['open'] > row['close'] and
                    body < 0.3 * prev_body and
                    row['volume'] < avg_volume[i] * 0.5
                ):
                    df.at[i, 'tag'] = '📈'

                # --- Signals that normally require future data ---
                # Modified to work on last candle with adjusted conditions
                if is_last_candle:
                    # For ⛔ (Buyer Absorption): Check if last candle is bullish with high volume
                    if (
                        row['close'] > row['open'] and
                        row['volume'] > avg_volume[i] * 1.5
                    ):
                        df.at[i, 'tag'] = '⛔ (Potential)'

                    # For 🚀 (Seller Absorption): Check if last candle is bearish with high volume
                    elif (
                        row['open'] > row['close'] and
                        row['volume'] > avg_volume[i] * 1.5
                    ):
                        df.at[i, 'tag'] = '🚀 (Potential)'
                else:
                    # Original future-dependent logic for non-last candles
                    if (
                        row['close'] > row['open'] and
                        row['volume'] > avg_volume[i] * 1.2
                    ):
                        df.loc[df['tag'] == '⛔', 'tag'] = ''
                        for j, candle in next_candles.iterrows():
                            if candle['close'] < row['open']:
                                df.at[j, 'tag'] = '⛔'
                                break

                    elif (
                        row['open'] > row['close'] and
                        row['volume'] > avg_volume[i] * 1.2
                    ):
                        df.loc[df['tag'] == '🚀', 'tag'] = ''
                        for j, candle in next_candles.iterrows():
                            if candle['close'] > row['open']:
                                df.at[j, 'tag'] = '🚀'
                                break
            # --- Visualization ---
            # st.subheader(f"{company_symbol} - Smart Money Line Chart")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['date'], y=df['close'],
                mode='lines', name='Close Price',
                line=dict(color='lightblue', width=2),
                customdata=df[['date', 'open', 'high', 'low', 'close', 'point_change']],
                hovertemplate=(
                    "📅 Date: %{customdata[0]|%Y-%m-%d}<br>" +
                    "🟢 Open: %{customdata[1]:.2f}<br>" +
                    "📈 High: %{customdata[2]:.2f}<br>" +
                    "📉 Low: %{customdata[3]:.2f}<br>" +
                    "💰 LTP: %{customdata[4]:.2f}<br>" +
                    "📊 Point Change: %{customdata[5]:.2f}<extra></extra>"
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
                
            # Calculate 15 days ahead of the last date
            last_date = df['date'].max()
            extended_date = last_date + timedelta(days=15)
            chart_bg = ""
            fig.update_layout(
                height=800,
                width=1800,
                plot_bgcolor="darkslategray",
                paper_bgcolor="darkslategray",
                font_color="white",
                title=chart_bg,
                xaxis=dict(title="Date", tickangle=-45, showgrid=False, range=[df['date'].min(),extended_date]), #extend x-axis to show space after latest date
                yaxis=dict(title="Price", showgrid=False, zeroline=True, zerolinecolor="gray", autorange=True),
                margin=dict(l=50, r=50, b=130, t=50),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.2,  # Adjust this value to move further down if needed
                    xanchor="center",
                    x=0.5,
                    font=dict(size=14),
                    bgcolor="rgba(0,0,0,0)"  # Optional: keeps legend background transparent)
                ),
                # Add zoom and pan capabilities
                dragmode="zoom",  # Enable box zoom
                annotations=[
                    dict(
                        text=f"{company_symbol} <br> Quantexo",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5,
                        xanchor="center", yanchor="middle",
                        font=dict(size=25, color="rgba(59, 59, 59)"),
                        showarrow=False
                    )
                ]
            )
            st.plotly_chart(fig, use_container_width=False)
                

        else:
            st.warning("⚠️ Unable to calculate trading signals due to insufficient data")
            
    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")

else:
    st.info("ℹ👆🏻 Enter a company symbol to get analysed chart 👆🏻")