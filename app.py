import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="Gold & Forex Sniper Elite v2.3", layout="wide")

# منع تكرار الرسائل في التليجرام باستخدام ذاكرة الجلسة
if 'last_alert_key' not in st.session_state:
    st.session_state.last_alert_key = None

# ==================== دالة التليجرام ====================
def send_telegram_alert(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

# ==================== الستايل المرئي ====================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== القائمة الجانبية ====================
st.sidebar.header("🕹️ لوحة التحكم Elite")

with st.sidebar.expander("🤖 إعدادات التليجرام"):
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")
    auto_send = st.checkbox("إرسال التنبيهات تلقائياً", value=False)

asset_groups = {
    "⭐ المعادن الثمينة": {"الذهب (Gold)": "GC=F", "الفضة (Silver)": "SI=F"},
    "💵 سوق الفوركس": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X"
    },
    "₿ العملات الرقمية": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
}

group = st.sidebar.selectbox("اختر الفئة", list(asset_groups.keys()))
asset_key = st.sidebar.selectbox("اختر الأداة", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_key]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=2)

# ==================== جلب البيانات (الحل النهائي للخطأ) ====================
@st.cache_data(ttl=45)
def get_data(sym, tf):
    p_map = {"5m": "7d", "15m": "10d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    
    if df.empty or len(df) < 100:
        return None
    
    # حل مشكلة الـ MultiIndex التي تسببت في الخطأ السابق
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # توحيد أسماء الأعمدة لتجنب AttributeError
    df.columns = [str(col).lower() for col in df.columns]
    return df

df = get_data(symbol, timeframe)

if df is None:
    st.warning("جاري تحميل البيانات... تأكد من استقرار الإنترنت.")
    st.stop()

# ==================== حساب المؤشرات ====================
df['EMA200'] = ta.ema(df['close'], length=200)
df['EMA50'] = ta.ema(df['close'], length=50)
df['RSI'] = ta.rsi(df['close'], length=14)
df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['ADX'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']

macd_data = ta.macd(df['close'])
df['MACD'] = macd_data['MACD_12_26_9']
df['MACD_s'] = macd_data['MACDs_12_26_9']

# تحليل الفريم الأكبر (HTF)
htf_tf = "4h" if timeframe in ["5m","15m","30m","1h"] else "1d"
df_htf = get_data(symbol, htf_tf)
htf_trend = "صاعد" if (df_htf is not None and df_htf['close'].iloc[-1] > ta.ema(df_htf['close'], 200).iloc[-1]) else "هابط"

curr = df.iloc[-1]

# ==================== منطق الإشارة المطور ====================
def get_advanced_signal():
    price = curr['close']
    score = 0
    reasons = []

    # 1. الاتجاه الأساسي (وزن ثقيل)
    if price > curr['EMA200']:
        score += 30; reasons.append("✅ السعر فوق المتوسط 200")
    else:
        score -= 30; reasons.append("❌ السعر تحت المتوسط 200")

    # 2. توافق الفريمات
    if (price > curr['EMA200'] and htf_trend == "صاعد") or (price < curr['EMA200'] and htf_trend == "هابط"):
        score += 25; reasons.append(f"✅ توافق مع اتجاه الـ {htf_tf}")

    # 3. الزخم (تعديل 60/40 للدقة)
    if curr['RSI'] > 60: score += 15; reasons.append("✅ زخم شرائي قوي")
    elif curr['RSI'] < 40: score -= 15; reasons.append("✅ زخم بيعي قوي")

    # 4. قوة الترند والـ MACD
    if curr['ADX'] > 25: score += 10; reasons.append("✅ قوة ترند مثالية")
    if curr['MACD'] > curr['MACD_s']: score += 10

    if score >= 65: return "شراء قوي 🚀", score, reasons
    elif score <= -65: return "بيع قوي 📉", score, reasons
    return "انتظار ⚖️", score, reasons

signal, confidence, reasons = get_advanced_signal()

# ==================== الواجهة الرسومية ====================
st.title(f"🔍 رادار القناص Elite - {asset_key}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("السعر الحالي", f"{curr['close']:,.4f}")
m2.metric("RSI", f"{curr['RSI']:.1f}")
m3.metric("ADX (القوة)", f"{curr['ADX']:.1f}")
m4.metric("اتجاه الفريم الكبير", htf_trend)

col_left, col_right = st.columns([3, 1])

with col_left:
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="الشموع")])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="EMA 200"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='orange', width=1, dash='dot'), name="EMA 50"))
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("💡 التوصية")
    if "شراء" in signal:
        st.success(signal)
        tp = curr['close'] + (curr['ATR'] * 2.8)
        sl = curr['close'] - (curr['ATR'] * 1.4)
    elif "بيع" in signal:
        st.error(signal)
        tp = curr['close'] - (curr['ATR'] * 2.8)
        sl = curr['close'] + (curr['ATR'] * 1.4)
    else:
        st.warning(signal)
        tp = sl = None

    if tp:
        st.write(f"🎯 **TP:** {tp:,.4f}")
        st.write(f"🛑 **SL:** {sl:,.4f}")
        
        # إرسال التليجرام (تجنب التكرار)
        alert_key = f"{asset_key}_{signal}_{df.index[-1].strftime('%H:%M')}"
        if auto_send and bot_token and chat_id:
            if st.session_state.last_alert_key != alert_key:
                msg = f"🚨 *إشارة قناص جديدة*\n\n• الأداة: {asset_key}\n• الإشارة: {signal}\n• السعر: {curr['close']:,.4f}\n• الهدف: {tp:,.4f}\n• الوقف: {sl:,.4f}\n• الفريم: {timeframe}\n• الوقت: {datetime.now().strftime('%H:%M')}"
                if send_telegram_alert(bot_token, chat_id, msg):
                    st.session_state.last_alert_key = alert_key
                    st.toast("تم إرسال التنبيه!")

    st.markdown("---")
    st.write("**لماذا هذه الإشارة؟**")
    for r in reasons: st.write(f"• {r}")

st.caption(f"تحديث تلقائي | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
