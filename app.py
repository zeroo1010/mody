import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go

# 1. إعدادات الصفحة (الستايل اللي حبيته)
st.set_page_config(page_title="Gold & Forex Radar", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 2. إعادة الذهب والعملات للقائمة الجانبية
asset_groups = {
    "المعادن والطاقة": {
        "الذهب (Gold)": "GC=F",
        "الفضة (Silver)": "SI=F",
        "النفط (Oil)": "CL=F"
    },
    "العملات الرقمية": {
        "Bitcoin (BTC/USD)": "BTC-USD",
        "Ethereum (ETH/USD)": "ETH-USD"
    },
    "سوق العملات (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X"
    }
}

st.sidebar.title("🔍 رادار الأسواق")
group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "1h", "4h", "1d"], index=0)

# 3. جلب البيانات مع الفلاتر الذكية (في الخلفية)
@st.cache_data(ttl=60)
def fetch_pro_data(symbol, tf):
    p_map = {"5m": "5d", "15m": "7d", "1h": "30d", "4h": "max", "1d": "max"}
    df = yf.download(symbol, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    
    # حساب المؤشرات
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['VOL_SMA'] = ta.sma(df['volume'], length=20)
    return df

try:
    df = fetch_pro_data(symbol, timeframe)
    curr = df.iloc[-1]
    
    # 4. عرض المقاييس العلوية (نفس الستايل القديم)
    st.title(f"📊 تحليل {asset_name}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("السعر الحالي", f"{curr['close']:,.2f}")
    m2.metric("RSI", f"{curr['RSI']:.1f}")
    
    # فلتر السيولة
    vol_status = "عالية 🔥" if curr['volume'] > curr['VOL_SMA'] else "ضعيفة ❄️"
    m3.metric("السيولة", vol_status)
    
    trend = "صاعد 🟢" if curr['close'] > curr['EMA200'] else "هابط 🔴"
    m4.metric("الاتجاه (EMA200)", trend)

    # 5. توزيع الشاشة (الرسم يسار، الإشارة يمين)
    col_chart, col_signal = st.columns([3, 1])

    with col_chart:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='#ff4b4b', width=2), name="Trend Line"))
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_signal:
        st.subheader("📋 حالة الإشارة")
        
        # منطق الإشارة المطور (بيجمع بين الاتجاه والزخم والسيولة)
        if curr['close'] > curr['EMA200'] and curr['RSI'] > 50:
            st.success("🚀 إشارة شراء")
            if curr['volume'] > curr['VOL_SMA']: st.info("📢 سيولة تدعم الصعود")
            tp = curr['close'] + (curr['ATR'] * 2)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        elif curr['close'] < curr['EMA200'] and curr['RSI'] < 50:
            st.error("📉 إشارة بيع")
            if curr['volume'] > curr['VOL_SMA']: st.info("📢 سيولة تدعم الهبوط")
            tp = curr['close'] - (curr['ATR'] * 2)
            sl = curr['close'] + (curr['ATR'] * 1.5)
        else:
            st.warning("⌛ حالة انتظار")
            tp, sl = 0, 0

        if tp != 0:
            st.markdown("---")
            st.write(f"🎯 **الهدف (TP):** {tp:,.2f}")
            st.write(f"🛑 **الوقف (SL):** {sl:,.2f}")

except Exception as e:
    st.info("يرجى اختيار أداة مالية لبدء التحليل...")
