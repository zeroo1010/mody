import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import requests

st.set_page_config(page_title="Gold & Forex Sniper Elite v2.4", layout="wide")

# ==================== Session State ====================
if 'last_alert_key' not in st.session_state:
    st.session_state.last_alert_key = None

# ==================== Telegram ====================
def send_telegram_alert(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
        return True
    except:
        return False

# ==================== Style ====================
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
    .stSuccess { background-color: #1a3c2e; }
    .stError { background-color: #3c1f1f; }
    </style>
    """, unsafe_allow_html=True)

# ==================== Sidebar ====================
st.sidebar.header("🕹️ لوحة التحكم Elite")

with st.sidebar.expander("🤖 إعدادات التليجرام"):
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")
    auto_send = st.checkbox("إرسال التنبيهات تلقائياً", value=False)

asset_groups = {
    "⭐ المعادن الثمينة": {"الذهب (Gold)": "GC=F", "الفضة (Silver)": "SI=F"},
    "💵 سوق الفوركس": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X",
        "EUR/JPY": "EURJPY=X", "GBP/JPY": "GBPJPY=X"
    },
    "₿ العملات الرقمية": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
}

group = st.sidebar.selectbox("اختر الفئة", list(asset_groups.keys()))
asset_key = st.sidebar.selectbox("اختر الأداة", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_key]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h", "1d"], index=2)

# ==================== Data Fetch ====================
@st.cache_data(ttl=40)
def get_data(sym, tf):
    p_map = {"5m": "7d", "15m": "10d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    
    if df.empty or len(df) < 100:
        return None
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [str(col).lower() for col in df.columns]
    return df

df = get_data(symbol, timeframe)

if df is None:
    st.error("❌ فشل في جلب البيانات. حاول مرة أخرى.")
    st.stop()

# ==================== Indicators ====================
df['EMA200'] = ta.ema(df['close'], length=200)
df['EMA50']  = ta.ema(df['close'], length=50)
df['RSI']    = ta.rsi(df['close'], length=14)
df['ATR']    = ta.atr(df['high'], df['low'], df['close'], length=14)
df['ADX']    = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']

macd_data = ta.macd(df['close'])
df['MACD'] = macd_data['MACD_12_26_9']
df['MACD_signal'] = macd_data['MACDs_12_26_9']

curr = df.iloc[-1]

# Higher Timeframe
htf_tf = "4h" if timeframe in ["5m","15m","30m","1h"] else "1d"
df_htf = get_data(symbol, htf_tf)
htf_ema200 = ta.ema(df_htf['close'], 200) if df_htf is not None else pd.Series()
htf_trend = "صاعد" if (df_htf is not None and len(htf_ema200) > 0 and 
                       df_htf['close'].iloc[-1] > htf_ema200.iloc[-1]) else "هابط"

# ==================== Signal Logic ====================
def get_advanced_signal():
    price = curr['close']
    score = 0
    reasons = []

    if price > curr['EMA200']:
        score += 30
        reasons.append("✅ فوق EMA200")
    else:
        score -= 30
        reasons.append("❌ تحت EMA200")

    # HTF Confluence
    if ((price > curr['EMA200'] and htf_trend == "صاعد") or 
        (price < curr['EMA200'] and htf_trend == "هابط")):
        score += 25
        reasons.append(f"✅ توافق مع الـ {htf_tf}")

    # RSI
    if curr['RSI'] > 60:
        score += 15; reasons.append("✅ زخم شرائي قوي (RSI)")
    elif curr['RSI'] < 40:
        score -= 15; reasons.append("✅ زخم بيعي قوي (RSI)")

    # ADX + MACD
    if curr['ADX'] > 25:
        score += 12; reasons.append("✅ ترند قوي (ADX > 25)")
    if curr['MACD'] > curr['MACD_signal']:
        score += 8

    if score >= 65:
        return "شراء قوي 🚀", score, reasons
    elif score <= -65:
        return "بيع قوي 📉", score, reasons
    return "انتظار ⚖️", score, reasons

signal, confidence, reasons = get_advanced_signal()

# ==================== Main UI ====================
st.title(f"🔍 رادار القناص Elite v2.4 - {asset_key}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("السعر الحالي", f"{curr['close']:,.4f}")
m2.metric("RSI", f"{curr['RSI']:.1f}")
m3.metric("ADX", f"{curr['ADX']:.1f}")
m4.metric("الاتجاه العالي", htf_trend)

col_left, col_right = st.columns([3.2, 1])

with col_left:
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                        low=df['low'], close=df['close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2.5), name="EMA 200"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], line=dict(color='orange', width=1.5, dash='dot'), name="EMA 50"))
    
    fig.update_layout(height=620, template="plotly_dark", 
                      xaxis_rangeslider_visible=False,
                      title=f"{asset_key} - {timeframe}")
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("💡 التوصية النهائية")
    
    if "شراء" in signal:
        st.success(signal)
        st.progress(confidence / 100)
        st.caption(f"**ثقة الإشارة: {confidence}%**")
        tp = curr['close'] + (curr['ATR'] * 2.8)
        sl = curr['close'] - (curr['ATR'] * 1.4)
        
    elif "بيع" in signal:
        st.error(signal)
        st.progress(abs(confidence) / 100)
        st.caption(f"**ثقة الإشارة: {abs(confidence)}%**")
        tp = curr['close'] - (curr['ATR'] * 2.8)
        sl = curr['close'] + (curr['ATR'] * 1.4)
        
    else:
        st.warning(signal)
        tp = sl = None

    if tp:
        st.write(f"**🎯 TP:** {tp:,.4f}")
        st.write(f"**🛑 SL:** {sl:,.4f}")
        st.write(f"**نسبة RR:** 1 : 2")

        # Telegram Alert
        alert_key = f"{symbol}_{signal}_{df.index[-1].strftime('%Y%m%d%H%M')}"
        if auto_send and bot_token and chat_id and st.session_state.last_alert_key != alert_key:
            msg = f"""🚨 *إشارة قناص جديدة*
• الأصل: {asset_key}
• الإشارة: {signal}
• السعر: {curr['close']:,.4f}
• TP: {tp:,.4f}
• SL: {sl:,.4f}
• الفريم: {timeframe}
• الوقت: {datetime.now().strftime('%H:%M')}"""
            
            if send_telegram_alert(bot_token, chat_id, msg):
                st.session_state.last_alert_key = alert_key
                st.toast("✅ تم إرسال الإشارة إلى تليجرام", icon="🚀")

    st.markdown("---")
    st.write("**أسباب الإشارة:**")
    for r in reasons:
        st.write(r)

st.caption(f"● آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
