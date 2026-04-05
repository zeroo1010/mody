import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go

# 1. إعدادات الصفحة والستايل الأصلي
st.set_page_config(page_title="Professional Trading Radar", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. القائمة الجانبية (الأصول والفريمات)
st.sidebar.header("🔍 رادار الأسواق")
asset_groups = {
    "المعادن والطاقة": {"الذهب (Gold)": "GC=F", "الفضة (Silver)": "SI=F", "النفط (Oil)": "CL=F"},
    "العملات الرقمية": {"Bitcoin (BTC/USD)": "BTC-USD", "Ethereum (ETH/USD)": "ETH-USD"},
    "سوق العملات (Forex)": {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X"}
}

group = st.sidebar.selectbox("اختر فئة الأصول", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة المالية", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=2) # الافتراضي 30د

@st.cache_data(ttl=30)
def get_market_data(sym, tf):
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    df = get_market_data(symbol, timeframe)
    
    # --- المؤشرات الفنية للواقعية ---
    df['EMA_Fast'] = ta.ema(df['close'], length=50)  # لسرعة التفاعل
    df['EMA_Slow'] = ta.ema(df['close'], length=200) # لتحديد الاتجاه العام
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 3. عرض المربعات العلوية
    st.title(f"📈 رادار التحليل: {asset_name}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("السعر الحالي", f"{curr['close']:,.2f}")
    m2.metric("RSI (الزخم)", f"{curr['RSI']:.1f}")
    m3.metric("EMA 50 (سريع)", f"{curr['EMA_Fast']:,.2f}")
    m4.metric("EMA 200 (بطيء)", f"{curr['EMA_Slow']:,.2f}")

    col_left, col_right = st.columns([3, 1])

    with col_left:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price"))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_Slow'], line=dict(color='red', width=2), name="الاتجاه العام"))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_Fast'], line=dict(color='orange', width=1, dash='dot'), name="المتوسط السريع"))
        fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📋 التوصية الواقعية")
        
        # --- منطق الإشارة الواقعي (The Strategy) ---
        # شراء واقعي: السعر فوق الـ 200، والـ RSI ارتد من فوق الـ 50، والسعر فوق المتوسط السريع
        buy_cond = (curr['close'] > curr['EMA_Slow']) and (curr['RSI'] > 55) and (curr['close'] > curr['EMA_Fast'])
        
        # بيع واقعي: السعر تحت الـ 200، والـ RSI تحت الـ 45، والسعر تحت المتوسط السريع
        sell_cond = (curr['close'] < curr['EMA_Slow']) and (curr['RSI'] < 45) and (curr['close'] < curr['EMA_Fast'])
        
        if buy_cond:
            st.success("✅ **إشارة شراء مؤكدة**")
            st.info("الاتجاه صاعد والزخم يدعم الدخول")
            tp = curr['close'] + (curr['ATR'] * 2.5)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        elif sell_cond:
            st.error("📉 **إشارة بيع مؤكدة**")
            st.info("الاتجاه هابط والضغط البيعي قوي")
            tp = curr['close'] - (curr['ATR'] * 2.5)
            sl = curr['close'] + (curr['ATR'] * 1.5)
        else:
            st.warning("⚖️ **منطقة حيادية**")
            st.write("السوق في حالة تذبذب أو تصحيح. لا تنصح بالدخول الآن.")
            tp, sl = 0, 0

        if tp != 0:
            st.markdown("---")
            st.write(f"🎯 **الهدف المقترح:** {tp:,.2f}")
            st.write(f"🛑 **وقف الخسارة:** {sl:,.2f}")

except Exception as e:
    st.error(f"خطأ في البيانات: {e}")
