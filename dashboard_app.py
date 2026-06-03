import streamlit as st
import pandas as pd
import sqlite3
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# ==========================================
# PAGE CONFIG 
# ==========================================
st.set_page_config(
    page_title="KIS Quant Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark theme aesthetics
st.markdown("""
<style>
    .reportview-container .main .block-container{
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
        border-left: 5px solid #00FF00;
    }
    .metric-card.loss {
        border-left: 5px solid #FF0000;
    }
    .metric-title {
        color: #A0A0A0;
        font-size: 1rem;
        margin-bottom: 5px;
    }
    .metric-value {
        color: white;
        font-size: 2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# DATA FETCHING
# ==========================================
@st.cache_data(ttl=2)
def load_live_state():
    try:
        with open("health_state.json", "r") as f:
            return json.load(f)
    except Exception:
        return None

@st.cache_data(ttl=10)
def load_trade_history():
    try:
        conn = sqlite3.connect("trades.db")
        query = "SELECT * FROM trades ORDER BY entry_time DESC LIMIT 100"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def load_daily_pnl():
    try:
        conn = sqlite3.connect("trades.db")
        query = "SELECT * FROM daily_stats ORDER BY date ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ==========================================
# HEADER & SIDEBAR
# ==========================================
st.sidebar.title("🤖 Master Controls")
st.sidebar.markdown("---")
state = load_live_state()

if state:
    api_color = "🟢 OK" if state.get("api_status") == "OK" else "🔴 ERR"
    st.sidebar.metric("KIS API Status", api_color)
    st.sidebar.metric("CPU Usage", f"{state.get('cpu_percent', 0)}%")
    st.sidebar.metric("RAM Usage", f"{state.get('memory_percent', 0)}%")
    regime = state.get('current_regime', 'UNKNOWN')
    reg_color = "🟢" if "BULL" in regime else "🔴" if "BEAR" in regime else "🟡"
    st.sidebar.markdown(f"**Market Regime:** {reg_color} {regime}")
else:
    st.sidebar.warning("Bot is currently offline.")

# 🔑 API Key Master Settings
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 API Settings")

import os
from dotenv import load_dotenv, set_key
load_dotenv()

fh_key = os.getenv("FINNHUB_API_KEY", "")
new_key = st.sidebar.text_input("Finnhub API Key", value=fh_key, type="password")

if new_key != fh_key:
    try:
        set_key(".env", "FINNHUB_API_KEY", new_key)
        st.sidebar.success("✅ Finnhub Key updated!")
        os.environ["FINNHUB_API_KEY"] = new_key
    except Exception as e:
        st.sidebar.error(f"Failed to save key: {e}")

st.title("📈 KIS Auto-Trading Quant Hub")
st.markdown("Real-time telemetry and algorithmic performance metrics.")
st.markdown("---")

# ==========================================
# LIVE METRICS (TOP ROW)
# ==========================================
if state:
    col1, col2, col3, col4 = st.columns(4)
    net_pnl = state.get('net_pnl', 0)
    pnl_pct = state.get('pnl_pct', 0) * 100
    win_rate = state.get('win_rate', 0) * 100
    trades = state.get('trades_count', 0)
    
    col1.metric("Daily Net P&L", f"${net_pnl:,.2f}", f"{pnl_pct:+.2f}%")
    col2.metric("Win Rate", f"{win_rate:.1f}%", f"{state.get('wins',0)}W / {state.get('losses',0)}L")
    col3.metric("Total Trades Today", f"{trades}")
    col4.metric("Active Positions", f"{len(state.get('positions', []))}")


# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["🚀 Live Positions", "📊 Historical Analytics", "📒 Trade Journal"])

# --- TAB 1: LIVE POSITIONS ---
with tab1:
    st.subheader("Currently Open Positions")
    if state and state.get('positions'):
        pos_df = pd.DataFrame(state['positions'])
        # Reformat columns for UI
        pos_df['unrealized_pnl'] = (pos_df['current_price'] - pos_df['entry_price']) * pos_df['quantity']
        
        # Color coding PnL
        def color_pnl(val):
            color = '#00FF00' if val > 0 else '#FF0000'
            return f'color: {color}'
            
        st.dataframe(
            pos_df[['symbol', 'quantity', 'entry_price', 'current_price', 'pnl_pct', 'unrealized_pnl']].style.map(color_pnl, subset=['pnl_pct', 'unrealized_pnl']).format({
                "entry_price": "${:.2f}",
                "current_price": "${:.2f}",
                "pnl_pct": "{:+.2f}%",
                "unrealized_pnl": "${:+.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No active positions currently held.")

# --- TAB 2: HISTORICAL ANALYTICS ---
with tab2:
    st.subheader("Performance Curve (Equity)")
    df_daily = load_daily_pnl()
    if not df_daily.empty:
        # Convert cumulative PnL to Equity Curve
        df_daily['Cum_PnL'] = df_daily['net_pnl'].cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_daily['date'], y=df_daily['Cum_PnL'], mode='lines', fill='tozeroy', name='Cumulative P&L', line=dict(color='#00FFAA', width=3)))
        fig.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Daily P&L Bar Chart")
        fig2 = px.bar(df_daily, x='date', y='net_pnl', text_auto='.2s', color='net_pnl', color_continuous_scale=["red", "green"])
        fig2.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Waiting for historical database to populate...")

# --- TAB 3: TRADE JOURNAL ---
with tab3:
    st.subheader("Recent Execution Log")
    df_trades = load_trade_history()
    if not df_trades.empty:
        df_trades['pnl_pct'] = df_trades['pnl_pct'] * 100
        # Reorder and format display
        display_df = df_trades[['entry_time', 'symbol', 'side', 'price', 'pnl', 'pnl_pct', 'reason']]
        
        def highlight_row(row):
            if row['side'] == 'BUY': return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
            elif row.get('pnl', 0) > 0: return ['background-color: rgba(0, 150, 255, 0.2)'] * len(row)
            else: return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
            
        st.dataframe(
            display_df.style.apply(highlight_row, axis=1).format({
                "price": "${:.2f}",
                "pnl": "${:.2f}",
                "pnl_pct": "{:+.2f}%"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No trades executed yet.")

# Auto-refresh mechanism (if desired, currently users just click refresh, or Streamlit reruns on state touch)
time.sleep(0.5)
