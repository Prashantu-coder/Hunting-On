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
companies = {"ACLBSL", "ADBL", "AHL", "AHPC", "AKJCL", "AKPL", "ALBSL", "ALICL", "ANLB", "API", "AVYAN", "BARUN", "BBC", "BEDC", "BFC", "BGWT", "BHDC", "BHL", "BHPL", "BNHC", "BNL", "BNT", "BPCL", "C30MF", "CBBL", "CCBD88", "CFCL", "CGH", "CHCL", "CHDC", "CHL", "CIT", "CITY", "CIZBD90", "CKHL", "CLI", "CMF2", "CORBL", "CREST", "CYCL", "CZBIL", "DDBL", "DHPL", "DLBS", "DOLTI", "DORDI", "EBL", "EBLD85", "EBLD86", "EDBL", "EHPL", "ENL", "FMDBL", "FOWAD", "GBBD85", "GBBL", "GBILD84/85", "GBILD86/87", "GBIME", "GBLBS", "GCIL", "GFCL", "GHL", "GIBF1", "GILB", "GLBSL", "GLH", "GMFBS", "GMFIL", "GMLI", "GRDBL", "GSY", "GUFL", "GVL", "GWFD83", "H8020", "HATHY", "HBL", "HDHPC", "HDL", "HEI", "HEIP", "HHL", "HIDCL", "HIDCLP", "HLBSL", "HLI", "HPPL", "HRL", "HURJA", "ICFC", "ICFCD83", "ICFCD88", "IGI", "IHL", "ILBS", "ILI", "JBBD87", "JBBL", "JBBLPO", "JBLB", "JFL", "JOSHI", "JSLBB", "KBL", "KBLD86", "KBSH", "KDBY", "KDL", "KEF", "KKHC", "KMCDB", "KPCL", "KSBBL", "KSBBLD87", "KSY", "LBBL", "LEC", "LICN", "LLBS", "LSL", "LUK", "LVF2", "MAKAR", "MANDU", "MATRI", "MBJC", "MBL", "MBLD87", "MCHL", "MDB", "MEHL", "MEL", "MEN", "MERO", "MFIL", "MFLD85", "MHCL", "MHL", "MHNL", "MKCL", "MKHC", "MKHL", "MKJC", "MLBBL", "MLBL", "MLBS", "MLBSL", "MMF1", "MMKJL", "MNBBL", "MNMF1", "MPFL", "MSHL", "MSLB", "NABBC", "NABIL", "NABILD87", "NADEP", "NBBD2085", "NBF2", "NBF3", "NBL", "NBLD85", "NBLD87", "NESDO", "NFS", "NGPL", "NHDL", "NHPC", "NIBD2082", "NIBD84", "NIBLGF", "NIBLSTF", "NIBSF2", "NICA", "NICBF", "NICD88", "NICFC", "NICGF2", "NICL", "NICLBSL", "NICSF", "NIFRA", "NIFRAUR85/86", "NIL", "NIMB", "NIMBPO", "NLG", "NLIC", "NLICL", "NMB", "NMB50", "NMBHF2", "NMBMF", "NMFBS", "NMIC", "NMLBBL", "NRIC", "NRM", "NRN", "NSIF2", "NTC", "NUBL", "NWCL", "NYADI", "OHL", "OMPL", "PBD84", "PBD88", "PCBL", "PFL", "PHCL", "PMHPL", "PMLI", "PPCL", "PPL", "PRIN", "PROFL", "PRSF", "PRVU", "PSF", "RADHI", "RAWA", "RBCL", "RBCLPO", "RFPL", "RHGCL", "RHPL", "RIDI", "RLFL", "RMF1", "RMF2", "RNLI", "RSDC", "RURU", "SADBL", "SAGF", "SAHAS", "SALICO", "SAMAJ", "SAND2085", "SANIMA", "SAPDBL", "SARBTM", "SBCF", "SBD87", "SBI", "SBID83", "SBID89", "SBL", "SCB", "SEF", "SFCL", "SFEF", "SFMF", "SGHC", "SGIC", "SHEL", "SHINE", "SHIVM", "SHL", "SHLB", "SHPC", "SICL", "SIFC", "SIGS3", "SIKLES", "SINDU", "SJCL", "SJLIC", "SKBBL", "SLBBL", "SLBSL", "SLCF", "SMATA", "SMB", "SMFBS", "SMH", "SMHL", "SMJC", "SMPDA", "SNLI", "SONA", "SPC", "SPDL", "SPHL", "SPIL", "SPL", "SRLI", "SSHL", "STC", "SWBBL", "SWMF", "TAMOR", "TPC", "TRH", "TSHL", "TVCL", "UAIL", "UHEWA", "ULBSL", "ULHC", "UMHL", "UMRH", "UNHPL", "UNLB", "UPCL", "UPPER", "USHEC", "USHL", "USLB", "VLBS", "VLUCL", "WNLB"
}
col1, col2, col3 = st.columns([1,1,1.2])
with col1:
    selected_dropdown = st.selectbox("",options=[""] + sorted(list(companies)), index=0, label_visibility="collapsed")
with col2: 
    user_input = st.text_input("🔍 Enter Company Symbol","", label_visibility="collapsed",placeholder="🔍 Enter Company Symbol")
with col3: search_clicked = st.button("Search")

# --- Priority: Manual Entry overrides Dropdown ---
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
                # Define next_candles safely to avoid index errors
                next_candles = df.iloc[i + 1:min(i + 6, len(df))]
                body = abs(row['close'] - row['open'])
                prev_body = abs(prev['close'] - prev['open'])
                recent_tags = df['tag'].iloc[max(0, i - 4):i]

                # Check if we have enough lookahead data for certain patterns
                has_lookahead = i < len(df) - 5
                
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
                    row['volume'] > avg_volume[i] *1.5 and
                    body > prev_body and
                    '🔴' not in recent_tags.values
                ):
                    df.at[i, 'tag'] = '🔴'
                    
                # For patterns that require lookahead data, only process if we have enough data
                elif (
                    row['close'] > row['open'] and
                    row['volume'] > avg_volume[i] * 1.2 and
                    has_lookahead  # Only check if we have enough future data
                ):
                    # Remove only existing ⛔ tags
                    df.loc[df['tag'] == '⛔', 'tag'] = ''

                    for j, candle in next_candles.iterrows():
                        if candle['close'] < row['open']:  # Bearish confirmation
                            df.at[j, 'tag'] = '⛔'  # Tag FIRST bearish candle closing below
                            break  # Stop after first occurrence
                            
                elif (
                    row['open'] > row['close'] and
                    row['volume'] > avg_volume[i] * 1.2 and
                    has_lookahead  # Only check if we have enough future data
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
            chart_bg = f""
            fig.update_layout(
                height=800,
                width=1800,
                plot_bgcolor="darkslategray",
                paper_bgcolor="darkslategray",
                font_color="white",
                title=chart_bg,
                xaxis=dict(title="Date", tickangle=-45, showgrid=False, range=[df['date'].min(),extended_date]), #extend x-axis to show space after latest date
                yaxis=dict(title="Price", showgrid=False, zeroline=True, zerolinecolor="gray", autorange=True),
                margin=dict(l=50, r=50, b=150, t=50),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.3,  # Adjust this value to move further down if needed
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
                        font=dict(size=50, color="rgba(105, 113, 101)"),
                        showarrow=False
                    )
                ]
            )
            
            # Add latest date highlight
            latest_data = df.iloc[-1]
            fig.add_trace(go.Scatter(
                x=[latest_data['date']],
                y=[latest_data['close']],
                mode='markers',
                name='Latest Data',
                marker=dict(
                    color='yellow',
                    size=12,
                    line=dict(color='white', width=2),
                    symbol='star'
                ),
            ))
            
            st.plotly_chart(fig, use_container_width=False)

        else:
            st.warning("⚠️ Unable to calculate trading signals due to insufficient data")
            
    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")

else:
    st.info("ℹ👆🏻 Enter a company symbol to get analysed chart 👆🏻")