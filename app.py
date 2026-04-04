import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Pro Market Scanner", layout="wide", page_icon="📊")

# --- تحسين المظهر ---
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
        "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X"
    }
}

# =========================
# الإعدادات الجانبية
# =========================
st.sidebar.header("🔍 اختيار السوق")
group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]

timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=3)

with st.sidebar.expander("⚖️ أوزان الخوارزمية"):
    w_trend = st.slider("الاتجاه (EMA200)", 1, 10, 6)
    w_rsi = st.slider("القوة النسبية (RSI)", 1, 5, 2)
    w_macd = st.slider("الزخم (MACD)", 1, 5, 3)

# =========================
# جلب ومعالجة البيانات
# =========================
@st.cache_data(ttl=60)
def fetch_data(symbol, tf):
    p_map = {"5m": "1d", "15m": "5d", "30m": "5d", "1h": "1mo", "4h": "3mo", "1d": "1y"}
    df = yf.download(symbol, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    df = fetch_data(symbol, timeframe)
    
    # حساب المؤشرات الفنية
    df['EMA9'] = ta.ema(df['close'], length=9)
    df['EMA21'] = ta.ema(df['close'], length=21)
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ADX'] = ta.adx(df['high'], df['low'], df['close'])['ADX_14']
    
    # بولنجر باند
    bb = ta.bbands(df['close'], length=20, std=2)
    df['BBU'] = bb.iloc[:, 2] # Upper Band
    df['BBL'] = bb.iloc[:, 0] # Lower Band
    
    # ATR لإدارة المخاطر
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # حساب نقاط Pivot
    last_h, last_l, last_c = df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]
    pivot = (last_h + last_l + last_c) / 3
    r1 = (2 * pivot) - last_l
    s1 = (2 * pivot) - last_h

    # =========================
    # منطق الإشارة المطور
    # =========================
    curr = df.iloc[-1]
    score = 0
    
    # 1. فلتر الاتجاه العام
    trend_up = curr['close'] > curr['EMA200']
    score += w_trend if trend_up else -w_trend
    
    # 2. RSI فلتر
    if curr['RSI'] < 30: score += w_rsi
    elif curr['RSI'] > 70: score -= w_rsi
    
    # 3. تقاطع EMA
    if curr['EMA9'] > curr['EMA21']: score += 2
    else: score -= 2
    
    # تحديد نوع الإشارة
    if score >= 5: final_sig = "BUY"
    elif score <= -5: final_sig = "SELL"
    else: final_sig = "NEUTRAL"

    # =========================
    # العرض (Dashboard)
    # =========================
    st.title(f"📈 {asset_name} Analysis")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"{curr['close']:,.2f}")
    m2.metric("RSI", f"{curr['RSI']:.1f}")
    m3.metric("Trend Strength (ADX)", f"{curr['ADX']:.1f}")
    m4.metric("Volatility (ATR)", f"{curr['ATR']:.2f}")

    col_chart, col_info = st.columns([3, 1])

    with col_chart:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="Trend (EMA200)"))
        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.subheader("📋 Signal Status")
        if curr['ADX'] < 20:
            st.warning("⚠️ ضعيف (سوق عرضي)")
        
        if final_sig == "BUY":
            st.success("🚀 STRONG BUY")
        elif final_sig == "SELL":
            st.error("📉 STRONG SELL")
        else:
            st.info("⌛ NEUTRAL")

        st.markdown("---")
        # حساب الأهداف (تعديل المعامل حسب نوع الأصل)
        tp_mult = 3.0 if group == "العملات الرقمية" else 1.5
        if final_sig == "BUY":
            tp = curr['close'] + (curr['ATR'] * tp_mult)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        else:
            tp = curr['close'] - (curr['ATR'] * tp_mult)
            sl = curr['close'] + (curr['ATR'] * 1.5)
            
        st.write(f"🎯 **Target (TP):** {tp:,.2f}")
        st.write(f"🛑 **Stop Loss:** {sl:,.2f}")
        st.write(f"📍 **Pivot:** {pivot:,.2f}")

    if st.button("🔄 تحديث الآن"):
        st.rerun()

except Exception as e:
    st.error(f"خطأ في جلب البيانات: {e}")
    st.info("تأكد من اتصال الإنترنت أو صحة الرمز.")