import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة لتكون عريضة وبنفس الستايل
st.set_page_config(page_title="Pro Market Scanner", layout="wide", page_icon="📈")

# تحسين المظهر باستخدام CSS ليطابق الصورة
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
    }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =========================
# قائمة الأصول المحدثة (فوركس + عملات رقمية + معادن)
# =========================
asset_groups = {
    "العملات الرقمية": {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD",
        "Solana (SOL/USD)": "SOL-USD",
        "Ripple (XRP/USD)": "XRP-USD"
    },
    "سوق العملات (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "USDCAD=X"
    },
    "المعادن والطاقة": {
        "الذهب (Gold)": "GC=F",
        "الفضة (Silver)": "SI=F",
        "النفط (Oil)": "CL=F"
    }
}

# =========================
# القائمة الجانبية (Sidebar)
# =========================
st.sidebar.header("🔍 رادار الأسواق")
group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]

# إضافة فريم الـ 5 دقائق مع إصلاح المشكلة
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=0)

# =========================
# جلب ومعالجة البيانات
# =========================
@st.cache_data(ttl=60)
def fetch_data(symbol, tf):
    # إصلاح: فريم الـ 5 دقائق يتطلب فترة لا تزيد عن 60 يوم في yfinance
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "2mo", "4h": "max", "1d": "max"}
    df = yf.download(symbol, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    df = fetch_data(symbol, timeframe)
    
    if df.empty or len(df) < 20:
        st.error("بيانات غير كافية لهذا الفريم حالياً.")
        st.stop()

    # حساب المؤشرات الفنية (نفس الموجودة في الصورة)
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ADX'] = ta.adx(df['high'], df['low'], df['close'])['ADX_14']
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # حساب Pivot (للأهداف)
    last_h, last_l, last_c = df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]
    pivot = (last_h + last_l + last_c) / 3

    # =========================
    # عرض البيانات (نفس ستايل الصورة)
    # =========================
    st.title(f"📊 تحليل {asset_name}")
    
    # سطر المقاييس (Metrics)
    curr = df.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("السعر الحالي", f"{curr['close']:,.2f}")
    m2.metric("RSI", f"{curr['RSI']:.1f}")
    m3.metric("ADX قوة الاتجاه", f"{curr['ADX']:.1f}")
    m4.metric("ATR التذبذب", f"{curr['ATR']:.2f}")

    # توزيع الشاشة: الرسم البياني على اليسار ولوحة الإشارة على اليمين
    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        fig = go.Figure()
        # الشموع اليابانية
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name="Price"))
        # خط الاتجاه (EMA 200) باللون الأحمر كما في الصورة
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='#ff4b4b', width=2), name="Trend Line"))
        
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False,
                          margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("🔄 تحديث البيانات"):
            st.rerun()

    with col_signal:
        st.subheader("📋 حالة الإشارة")
        
        # منطق الإشارة
        if curr['close'] > curr['EMA200'] and curr['RSI'] > 50:
            st.success("🚀 إشارة شراء")
            tp = curr['close'] + (curr['ATR'] * 2)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        elif curr['close'] < curr['EMA200'] and curr['RSI'] < 50:
            st.error("📉 إشارة بيع")
            tp = curr['close'] - (curr['ATR'] * 2)
            sl = curr['close'] + (curr['ATR'] * 1.5)
        else:
            st.info("⌛ حالة انتظار")
            tp, sl = 0, 0

        st.markdown("---")
        if tp != 0:
            st.write(f"🎯 **الهدف (TP):** {tp:,.2f}")
            st.write(f"🛑 **الوقف (SL):** {sl:,.2f}")
        st.write(f"📍 **نقطة Pivot:** {pivot:,.2f}")

except Exception as e:
    st.info("جاري تحميل البيانات... يرجى الانتظار")
