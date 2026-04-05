import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import requests

st.set_page_config(page_title="Gold & Forex Sniper Pro v2.2", layout="wide")

# ==================== ذاكرة الجلسة (لمنع تكرار التنبيهات) ====================
if 'last_signal_time' not in st.session_state:
    st.session_state.last_signal_time = None
if 'last_signal_type' not in st.session_state:
    st.session_state.last_signal_type = None

# ==================== Telegram Function ====================
def send_telegram_alert(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        st.error(f"فشل الاتصال بتليجرام: {e}")
        return False

# ==================== CSS Style ====================
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== Sidebar ====================
st.sidebar.header("🕹️ لوحة التحكم Pro")

with st.sidebar.expander("🤖 إعدادات التليجرام"):
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")
    auto_send = st.checkbox("إرسال الإشارات تلقائياً", value=False)

# قائمة الأصول الشاملة
asset_groups = {
    "⭐ المعادن": {"الذهب (Gold)": "GC=F", "الفضة (Silver)": "SI=F"},
    "💵 الفوركس": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X"
    },
    "₿ الكريبتو": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
}

group = st.sidebar.selectbox("اختر الفئة", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("اختر الأداة", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم", ["5m", "15m", "30m", "1h", "4h", "1d"], index=2)

# ==================== Data Fetching ====================
@st.cache_data(ttl=45)
def get_data(sym, tf):
    period_map = {"5m": "7d", "15m": "10d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=period_map[tf], interval=tf, progress=False, auto_adjust=True)
    if df.empty or len(df) < 100: return None
    df.columns = [col.lower() for col in df.columns]
    return df

df = get_data(symbol, timeframe)
if df is None:
    st.warning("جاري جلب البيانات أو البيانات غير متوفرة لهذا الفريم...")
    st.stop()

# ==================== Indicators ====================
df['EMA200'] = ta.ema(df['close'], length=200)
df['EMA50'] = ta.ema(df['close'], length=50)
df['RSI'] = ta.rsi(df['close'], length=14)
df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
df['ADX'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
macd = ta.macd(df['close'])
df['MACD'] = macd['MACD_12_26_9']
df['MACD_s'] = macd['MACDs_12_26_9']

curr = df.iloc[-1]

# تحليلات الفريم الأكبر
htf_tf = "4h" if timeframe in ["5m","15m","30m","1h"] else "1d"
df_htf = get_data(symbol, htf_tf)
htf_trend = "صاعد" if (df_htf is not None and df_htf['close'].iloc[-1] > ta.ema(df_htf['close'], 200).iloc[-1]) else "هابط"

# ==================== Signal Logic ====================
def get_signal():
    price = curr['close']
    score = 0
    reasons = []

    if price > curr['EMA200']: score += 30; reasons.append("✅ فوق EMA200")
    else: score -= 30; reasons.append("❌ تحت EMA200")

    if (price > curr['EMA200'] and htf_trend == "صاعد") or (price < curr['EMA200'] and htf_trend == "هابط"):
        score += 25; reasons.append(f"✅ توافق مع {htf_tf}")

    if curr['RSI'] > 58: score += 15; reasons.append("✅ زخم شرائي (RSI)")
    elif curr['RSI'] < 42: score -= 15; reasons.append("✅ زخم بيعي (RSI)")

    if curr['ADX'] > 23: score += 10; reasons.append("✅ اتجاه قوي")
    if curr['MACD'] > curr['MACD_s']: score += 10

    if score >= 65: return "شراء قوي 🚀", score, reasons
    elif score <= -65: return "بيع قوي 📉", score, reasons
    return "انتظار ⚖️", score, reasons

signal, confidence, reasons = get_signal()

# ==================== UI Construction ====================
st.title(f"🔍 رادار القناص Elite - {asset_name}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("السعر الحالي", f"{curr['close']:,.4f}")
c2.metric("RSI", f"{curr['RSI']:.1f}")
c3.metric("ADX", f"{curr['ADX']:.1f}")
c4.metric("اتجاه الفريم الكبير", htf_trend)

col_chart, col_info = st.columns([3, 1])

with col_chart:
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="EMA 200"))
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col_info:
    st.subheader("💡 التوصية الفنية")
    if "شراء" in signal:
        st.success(signal)
        tp, sl = curr['close'] + (curr['ATR'] * 2.8), curr['close'] - (curr['ATR'] * 1.4)
    elif "بيع" in signal:
        st.error(signal)
        tp, sl = curr['close'] - (curr['ATR'] * 2.8), curr['close'] + (curr['ATR'] * 1.4)
    else:
        st.warning(signal)
        tp = sl = None

    if tp:
        st.write(f"**🎯 الهدف (TP):** {tp:,.4f}")
        st.write(f"**🛑 الوقف (SL):** {sl:,.4f}")
        
        # إرسال التنبيه الذكي (مرة واحدة فقط لكل إشارة)
        current_time_str = df.index[-1].strftime('%Y-%m-%d %H:%M')
        if auto_send and bot_token and chat_id:
            if st.session_state.last_signal_time != current_time_str or st.session_state.last_signal_type != signal:
                msg = f"🚨 *إشارة قناص جديدة*\n• الأصل: {asset_name}\n• النوع: {signal}\n• السعر: {curr['close']:,.4f}\n• الهدف: {tp:,.4f}\n• الوقف: {sl:,.4f}\n• الوقت: {current_time_str}"
                if send_telegram_alert(bot_token, chat_id, msg):
                    st.session_state.last_signal_time = current_time_str
                    st.session_state.last_signal_type = signal
                    st.toast("تم إرسال التنبيه لتليجرام!")

    st.markdown("---")
    st.write("**الأسباب:**")
    for r in reasons: st.write(f"• {r}")

st.caption(f"تحديث تلقائي كل 45 ثانية | الوقت الآن: {datetime.now().strftime('%H:%M:%S')}")
