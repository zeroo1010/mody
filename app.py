import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh # استيراد مكتبة التحديث

st.set_page_config(page_title="Gold & Oil Elite v5.8", layout="wide", page_icon="💹")

# --- محرك التحديث التلقائي (30 ثانية) ---
# سيعمل فقط إذا كان المستخدم مفعلاً لخيار التحديث التلقائي
refresh_counter = 0

# --- دالة جلب البيانات ---
@st.cache_data(ttl=20) # تقليل مدة الكاش لـ 20 ثانية فقط
def get_data(sym, tf):
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max"}
    try:
        df = yf.download(sym, period=p_map.get(tf, "30d"), interval=tf, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except: return None

# --- Sidebar ---
st.sidebar.title("💹 المساعد الذكي v5.8")

# أزرار التحديث
with st.sidebar:
    if st.button("🔄 تحديث يدوي الآن", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    auto_ref = st.checkbox("تشغيل التحديث التلقائي (30ث)", value=True)
    if auto_ref:
        st_autorefresh(interval=30000, key="f_refresh")

asset_choice = st.sidebar.selectbox("اختر السلعة", ["الذهب (Gold)", "النفط (Crude Oil)"])
symbols = {"الذهب (Gold)": "GC=F", "النفط (Crude Oil)": "CL=F"}
symbol = symbols[asset_choice]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h"], index=1)

# [بقية الكود الخاص بالحسابات والرسوم البيانية والإشارات كما هو في النسخة السابقة]
df = get_data(symbol, timeframe)
if df is not None:
    st_data = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    df['st_direction'] = st_data.iloc[:, 1] 
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    
    # العرض
    st.title(f"📊 تحليل {asset_choice} المباشر")
    st.info(f"آخر تحديث للبيانات: {datetime.now().strftime('%H:%M:%S')}")
    
    # [بقية كود الرسم والنتائج...]
    st.metric("السعر الحالي", f"${curr['close']:,.2f}")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
