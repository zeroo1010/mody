import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go

# 1. إعدادات الصفحة
st.set_page_config(page_title="Global Forex & Crypto Radar", layout="wide")

# 2. قائمة شاملة لعملات الفوركس والمعادن
asset_groups = {
    "سوق العملات (Forex)": {
        "EUR/USD (اليورو/دولار)": "EURUSD=X",
        "GBP/USD (الباوند/دولار)": "GBPUSD=X",
        "USD/JPY (الدولار/ين)": "JPY=X",
        "AUD/USD (الأسترالي/دولار)": "AUDUSD=X",
        "USD/CAD (الدولار/كندي)": "USDCAD=X",
        "USD/CHF (الدولار/فرنك)": "USDCHF=X",
        "NZD/USD (النيوزلندي/دولار)": "NZDUSD=X",
        "EUR/GBP (اليورو/باوند)": "EURGBP=X",
        "EUR/JPY (اليورو/ين)": "EURJPY=X",
        "GBP/JPY (الباوند/ين)": "GBPJPY=X",
        "GOLD/USD (الذهب)": "GC=F",
        "SILVER/USD (الفضة)": "SI=F"
    },
    "العملات الرقمية": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "Solana (SOL)": "SOL-USD",
        "Ripple (XRP)": "XRP-USD"
    }
}

st.sidebar.header("🔍 رادار الأسواق العالمي")
group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=2)

# 3. جلب البيانات
@st.cache_data(ttl=30)
def get_comprehensive_data(sym, tf):
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    df = get_comprehensive_data(symbol, timeframe)
    
    # حساب المؤشرات (الاستراتيجية الواقعية)
    df['EMA50'] = ta.ema(df['close'], length=50)
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    
    # 4. واجهة العرض
    st.title(f"📊 رادار التحليل: {asset_name}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("السعر الحالي", f"{curr['close']:,.4f}")
    c2.metric("RSI (الزخم)", f"{curr['RSI']:.1f}")
    c3.metric("متوسط 50", f"{curr['EMA50']:,.4f}")
    c4.metric("متوسط 200", f"{curr['EMA200']:,.4f}")

    col_l, col_r = st.columns([3, 1])

    with col_l:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price")])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="الاتجاه العام"))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='orange', width=1), name="المتوسط السريع"))
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("💡 التوصية")
        
        # المنطق الواقعي
        price, ema200, rsi = curr['close'], curr['EMA200'], curr['RSI']
        
        if price > ema200 and rsi > 55:
            st.success("🚀 إشارة شراء")
            st.write("✅ الاتجاه صاعد والزخم قوي.")
            tp = price + (curr['ATR'] * 2)
            sl = price - (curr['ATR'] * 1.5)
        elif price < ema200 and rsi < 45:
            st.error("📉 إشارة بيع")
            st.write("🔻 الاتجاه هابط والضغط البيعي عالٍ.")
            tp = price - (curr['ATR'] * 2)
            sl = price + (curr['ATR'] * 1.5)
        else:
            st.warning("⚖️ منطقة انتظار")
            st.write("تجنب الدخول، السوق غير واضح الاتجاه حالياً.")
            tp, sl = 0, 0

        if tp != 0:
            st.markdown("---")
            st.info(f"🎯 الهدف: {tp:,.4f}\n\n🛑 الوقف: {sl:,.4f}")

except Exception as e:
    st.error("حدث خطأ في البيانات، يرجى تحديث الصفحة.")
