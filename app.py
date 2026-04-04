import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Pro Market Scanner", layout="wide", page_icon="📈")

# تحسين المظهر باستخدام CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 15px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# قائمة الأصول المتاحة
# =========================
asset_groups = {
    "العملات الرقمية": {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD",
        "Solana (SOL/USD)": "SOL-USD"
    },
    "المعادن والطاقة": {
        "الذهب (Gold)": "GC=F",
        "نفط برنت (Brent)": "BZ=F",
        "النفط الخام (WTI)": "CL=F",
        "الفضة (Silver)": "SI=F"
    },
    "سوق العملات (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X"
    }
}

# =========================
# الإعدادات الجانبية
# =========================
st.sidebar.header("🔍 رادار الأسواق")
group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]

timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=3)

# =========================
# جلب ومعالجة البيانات
# =========================
@st.cache_data(ttl=60)
def fetch_data(symbol, tf):
    p_map = {"5m": "1d", "15m": "5d", "30m": "5d", "1h": "1mo", "4h": "3mo", "1d": "1y"}
    df = yf.download(symbol, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    
    # معالجة رأس الجدول لضمان التوافق
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    df = fetch_data(symbol, timeframe)
    
    if df.empty:
        st.error("فشل في جلب البيانات، يرجى المحاولة لاحقاً.")
        st.stop()

    # حساب المؤشرات الفنية
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ADX'] = ta.adx(df['high'], df['low'], df['close'])['ADX_14']
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # حساب نقاط Pivot مبسطة
    last_h, last_l, last_c = df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]
    pivot = (last_h + last_l + last_c) / 3

    # =========================
    # منطق الإشارة
    # =========================
    curr = df.iloc[-1]
    
    # تحديد الإشارة بناءً على EMA200 و RSI
    if curr['close'] > curr['EMA200'] and curr['RSI'] > 50:
        final_sig = "BUY"
    elif curr['close'] < curr['EMA200'] and curr['RSI'] < 50:
        final_sig = "SELL"
    else:
        final_sig = "NEUTRAL"

    # =========================
    # عرض النتائج
    # =========================
    st.title(f"📊 تحليل {asset_name}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("السعر الحالي", f"{curr['close']:,.2f}")
    c2.metric("RSI", f"{curr['RSI']:.1f}")
    c3.metric("قوة الاتجاه ADX", f"{curr['ADX']:.1f}")
    c4.metric("التذبذب ATR", f"{curr['ATR']:.2f}")

    col_chart, col_info = st.columns([3, 1])

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name="Price"))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="Trend Line"))
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.subheader("📋 حالة الإشارة")
        if final_sig == "BUY":
            st.success("🚀 إشارة شراء")
        elif final_sig == "SELL":
            st.error("📉 إشارة بيع")
        else:
            st.info("⌛ انتظار")

        st.markdown("---")
        # حساب الأهداف مبسط
        tp_mult = 2.5 if "BTC" in symbol or "ETH" in symbol else 1.5
        if final_sig == "BUY":
            tp = curr['close'] + (curr['ATR'] * tp_mult)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        else:
            tp = curr['close'] - (curr['ATR'] * tp_mult)
            sl = curr['close'] + (curr['ATR'] * 1.5)
            
        st.write(f"🎯 **الهدف (TP):** {tp:,.2f}")
        st.write(f"🛑 **الوقف (SL):** {sl:,.2f}")
        st.write(f"📍 **نقطة Pivot:** {pivot:,.2f}")

    if st.button("🔄 تحديث البيانات"):
        st.rerun()

except Exception as e:
    st.error(f"حدث خطأ غير متوقع: {e}")
