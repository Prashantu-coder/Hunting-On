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
col1, col2, col3, col4 =st.columns([0.5,0.5,0.5,0.5])

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
        label_visibility= "collapsed",
        key="company"
    )
# ---Manual Input---
with col3:
    user_input = st.text_input(
        "🔍 Enter Company Symbol",
        "",
        label_visibility= "collapsed",
        placeholder= "🔍 Enter Symbol"
    )
with col4:
    search_clicked = st.button("Search")
    label_visibility= "collapsed"
company_symbol = ""
if search_clicked:
    company_symbol = (user_input or selected_dropdown).strip().upper()
    if not company_symbol:
        st.warning("⚠️ Please enter or select a company.")
    
# ────────────────────────────────── Data Helpers ──────────────────────────────────────

def get_sheet_gid(sheet_name: str) -> int:
    return {"Daily Price": 0}.get(sheet_name, 0)

@st.cache_data(ttl=3600)
def get_sheet_data(symbol: str, sheet_name: str = "Daily Price") -> pd.DataFrame:
    url = f"https://docs.google.com/spreadsheets/d/1Q_En7VGGfifDmn5xuiF-t_02doPpwl4PLzxb4TBCW0Q/export?format=csv&gid={get_sheet_gid(sheet_name)}"
    df = pd.read_csv(url).iloc[:, :7]
    df.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
    return df[df['symbol'].str.strip().str.upper() == symbol]

# ───────────────────────────────── Weak‑Leg Logic ────────────────────────────────────

def add_weak_leg(df: pd.DataFrame, rs_thr: float = 0.6, rv_thr: float = 1.25, win: int = 20) -> pd.DataFrame:
    rng = (df['high'] - df['low']).replace(0, pd.NA)
    df['RS'] = (df['close'] - df['open']) / rng
    df['RV'] = df['volume'] / df['volume'].rolling(win).mean()
    bull = (df['RS'] >  rs_thr) & (df['RV'] >= rv_thr)
    bear = (df['RS'] < -rs_thr) & (df['RV'] >= rv_thr)
    df['weak_dir'] = 0
    df.loc[bull, 'weak_dir'] = 1
    df.loc[bear, 'weak_dir'] = -1
    return df

if company_symbol:
    df =get_sheet_data(company_symbol)
    if df.empty:
        st.warning(f"No data found for {company_symbol}")
        st.stop()
    
    #Validation
    df.columns=[c.lower() for c in df.columns]
    df['date']=pd.to_datetime(df['date'],errors='coerce')
    df.dropna(subset=['date'],inplace=True)
    for c in ['open','high','low','close','volume']:
        df[c]=pd.to_numeric(df[c],errors='coerce')
    df.dropna(inplace=True)
    df.sort_values('date',inplace=True)
    df.reset_index(drop=True,inplace=True)

    df['point_change'] = df['close'].diff().fillna(0)

    df=add_weak_leg(df)

    min_window = min(20, max(5, len(df)//2))
    avg_volume = df['volume'].rolling(min_window).mean().fillna(method='bfill').fillna(df['volume'].mean())

    df['tag'] = ''

    if len(df) < 4:          # need at least 4 rows for the logic
        st.warning("Not enough price history to compute signals (need ≥ 4 rows).")
    st.plotly_chart(go.Figure(), use_container_width=False)
    st.stop()

    for i in range(min(3, len(df)-1), len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        body = abs(row['close'] - row['open'])
        prev_body = abs(prev['close'] - prev['open'])
        rng = row['high']-row['low']
        recent = df['tag'].iloc[max(0, i - 4):i]
        next_candles = df.iloc[i + 1:min(i + 6, len(df))]

        # ⏳ Weak-Leg
        if row['weak_dir']!=0:
            df.at[i,'tag']='⏳'
            continue

        # 🟢 Aggressive Buyers
        if (row['close']>row['open'] and row['close']>=row['high']-0.1*rng and row['volume']>avg_volume[i]*1.5 and body>prev_body and '🟢' not in recent.values):
            df.at[i,'tag']='🟢'
            continue

        # 🔴 Aggressive Sellers
        if (row['open']>row['close'] and row['close']<=row['low']+0.1*rng and row['volume']>avg_volume[i]*1.5 and body>prev_body and '🔴' not in recent.values):
            df.at[i,'tag']='🔴'
            continue

        # 💥 Bullish POR
        if (i>=10 and row['high']>max(df['high'].iloc[i-10:i]) and row['volume']>avg_volume[i]*1.8 and not (df['tag'].iloc[i-8:i]=='💥').any()):
            df.at[i,'tag']='💥'
            continue

        # 💣 Bearish POR
        if (i>=10 and row['low']<min(df['low'].iloc[i-10:i]) and row['volume']>avg_volume[i]*1.8 and not (df['tag'].iloc[i-8:i]=='💣').any()):
            df.at[i,'tag']='💣'
            continue

        # 🐂 Bullish POI
        if (row['close']>row['open'] and body>0.7*rng and row['volume']>avg_volume[i]*2):
            df.at[i,'tag']='🐂'
            continue

        # 🐻 Bearish POI
        if (row['open']>row['close'] and body>0.7*rng and row['volume']>avg_volume[i]*2):
            df.at[i,'tag']='🐻'
            continue    

        # 🐂 Bullish POI
        if (row['close']>row['open'] and body>0.7*rng and row['volume']>avg_volume[i]*2):
            df.at[i,'tag']='🐂'
            continue

        # 🐻 Bearish POI
        if (row['open']>row['close'] and body>0.7*rng and row['volume']>avg_volume[i]*2):
            df.at[i,'tag']='🐻'
            continue

        # ⛔ Buyer Absorption
        if (row['close']>row['open'] and row['volume']>avg_volume[i]*1.2):
            for j,c in next_candles.iterrows():
                if c['close']<row['open']:
                    df.at[j,'tag']='⛔'; break

        # 🚀 Seller Absorption
        if (row['open']>row['close'] and row['volume']>avg_volume[i]*1.2):
            for j,c in next_candles.iterrows():
                if c['close']>row['open']:
                    df.at[j,'tag']='🚀'; break

     # ─────────────────────────────── Plotting ───────────────────────────────
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
            '⏳':'⏳ Weak‑Leg'
        }
        signals = df[df['tag'] != '']
        for tag in signals['tag'].unique():
            subset = signals[signals['tag'] == tag]
            hover_extra = subset.apply(lambda r: ('Bullish Weak‑Leg' if r['weak_dir'] > 0 else 'Bearish Weak‑Leg') if tag == '⏳' else tag_labels[tag], axis=1)
            fig.add_trace(go.Scatter(
                x=subset['date'], y=subset['close'],
                mode='markers+text',
                name=tag_labels.get(tag, tag),
                text=[tag] * len(subset),
                textposition='top center',
                textfont=dict(size=20),
                marker=dict(size=14, symbol="circle", color='white'),
                customdata=pd.concat([subset[['open', 'high', 'low', 'close', 'point_change']].reset_index(drop=True), hover_extra.reset_index(drop=True)], axis=1).values,
                hovertemplate=(
                    "📅 Date: %{x|%Y-%m-%d}<br>" +
                    "🟢 Open: %{customdata[0]:.2f}<br>" +
                    "📈 High: %{customdata[1]:.2f}<br>" +
                    "📉 Low: %{customdata[2]:.2f}<br>" +
                    "🔚 Close: %{customdata[3]:.2f}<br>" +
                    "📊 Point Change: %{customdata[4]:.2f}<br>" +
                    "%{customdata[5]}<extra></extra>"
                )
            ))

            # Calculate 15 days ahead of the last date
        last_date = df['date'].max()
        extended_date = last_date + timedelta(days=15)
        fig.update_layout(
            height=800,
            width=1800,
            plot_bgcolor="darkslategray",
            paper_bgcolor="darkslategray",
            font_color="white",
            xaxis=dict(title="Date", tickangle=-45, showgrid=False, range=[df['date'].min(),extended_date]), #extend x-axis to show space after latest date
            yaxis=dict(title="Price", showgrid=False),
            margin=dict(l=50, r=50, b=130, t=50),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5, font=dict(size=14), bgcolor="rgba(0,0,0,0)" ),
            dragmode="zoom", 
            annotations=[
                dict(text=f"{company_symbol} <br> Quantexo", xref="paper", yref="paper", x=0.5, y=0.5,  xanchor="center", yanchor="middle", font=dict(size=25, color="rgba(59, 59, 59)"), showarrow=False
                )
            ]
        )
    st.plotly_chart(fig, use_container_width=False)
else:
    st.info("ℹ👆🏻 Enter a company symbol to get analysed chart 👆🏻")