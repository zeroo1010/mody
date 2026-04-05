import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Ultra Market Scanner", layout="wide", page_icon="💰")

# =========================
# قائمة عملات الفوركس وبقية الأصول
# =========================
asset_groups = {
    "سوق العملات (Forex)": {
        "EUR/USD": "EURUSD=X",
        "GBP/USD": "GBPUSD=X",
        "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X",
        "USD/CAD": "USDCAD=X",
        "USD/CHF": "USDCHF=X",
        "NZD/USD": "NZDUSD=X",
        "EUR/GBP": "EURGBP=X",
        "EUR/JPY": "EURJPY=X",
        "GBP/JPY": "GBPJPY=X"
    },
    "العملات الرقمية": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "Solana (SOL)": "SOL-USD",
        "Binance Coin (BNB)": "BNB-USD",
        "Ripple (XRP)": "XRP-USD"
    },
    "المعادن والطاقة": {
        "الذهب (Gold)": "GC=F",
        "الفضة (Silver)": "SI=F",
        "النفط (Oil WTI)": "CL=F",
        "الغاز الطبيعي (Gas)": "NG=F"
    }
}

# =========================
# الإعدادات الجانبية
# =========================
st.sidebar.header("🕹️ لوحة التحكم")
group = st.sidebar.selectbox("اختر الفئة", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الزوج", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]

# تعديل الفريمات وإصلاح مشكلة الـ 5 دقائق
timeframe = st.sidebar.selectbox("الفريم الزمني", ["1m", "5m", "15m", "1h", "4h", "1d"], index=1)

# =========================
# جلب البيانات مع إصلاح الفريمات الصغيرة
# =========================
@st.cache_data(ttl=30)
def fetch_data(symbol, tf):
    # تحديد المدة المسموح بها لكل فريم (yfinance strict rules)
    period_map = {
        "1m": "1d",     # الدقيقة تحتاج يوم واحد فقط
        "5m": "5d",     # 5 دقائق تحتاج بحد أقصى 5-7 أيام
        "15m": "5d",
        "1h": "1mo",
        "4h": "3mo",
        "1d": "max"
    }
    
    df = yf.download(symbol, period=period_map[tf], interval=tf, progress=False, auto_adjust=True)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    return df

try:
    with st.spinner('جاري جلب بيانات السوق...'):
        df = fetch_data(symbol, timeframe)
    
    if df.empty or len(df) < 200:
        st.warning(f"البيانات المتاحة لفريم {timeframe} قليلة جداً حالياً، جرب فريم أكبر أو انتظر افتتاح السوق.")
        st.stop()

    # حساب المؤشرات (EMA 200, RSI, MACD)
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['Signal'] = macd['MACDs_12_26_9']

    # =========================
    # عرض البيانات
    # =========================
    st.title(f"📈 رادار: {asset_name} ({timeframe})")
    
    last_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    diff = last_price - prev_price
    
    c1, c2, c3 = st.columns(3)
    c1.metric("السعر الحالي", f"{last_price:,.4f}", f"{diff:,.4f}")
    c2.metric("مؤشر RSI", f"{df['RSI'].iloc[-1]:.1f}")
    
    # تحديد قوة الاتجاه
    trend = "صاعد 🟢" if last_price > df['EMA200'].iloc[-1] else "هابط 🔴"
    c3.metric("الاتجاه العام (EMA200)", trend)

    # الرسم البياني
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="الشموع"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='yellow', width=1.5), name="EMA 200"))
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # نظام الإشارات المطور
    st.subheader("💡 التوصية اللحظية")
    rsi_val = df['RSI'].iloc[-1]
    
    if last_price > df['EMA200'].iloc[-1] and rsi_val < 40:
        st.success("🔥 فرصة شراء قوية (ارتداد من تشبع بيعي في اتجاه صاعد)")
    elif last_price < df['EMA200'].iloc[-1] and rsi_val > 60:
        st.error("📉 فرصة بيع قوية (ارتداد من تشبع شرائي في اتجاه هابط)")
    else:
        st.info("⚖️ السوق في حالة تذبذب - انتظر إشارة أوضح")

except Exception as e:
    st.error(f"حدث خطأ: {e}")
