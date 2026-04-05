import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==================== إعدادات الصفحة ====================
st.set_page_config(page_title="Sniper Elite v4.9 - Fast & Stable", layout="wide", page_icon="🎯")

if 'last_alert_key' not in st.session_state:
    st.session_state.last_alert_key = None

# ==================== الدالات الأساسية ====================
def send_telegram(token, chat_id, msg):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        return True
    except: return False

@st.cache_data(ttl=60)
def get_data(sym, tf):
    # موازنة المدة الزمنية لمنع فشل التحميل (مهم جداً للـ 15m و 5m)
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    try:
        df = yf.download(sym, period=p_map.get(tf, "30d"), interval=tf, progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except: return None

# ==================== القائمة الجانبية (كل العملات) ====================
st.sidebar.title("🎯 Sniper Elite v4.9")

with st.sidebar.expander("⚖️ إدارة المخاطر"):
    capital = st.number_input("رأس المال ($)", value=1000.0)
    risk_p = st.slider("المخاطرة (%)", 0.5, 5.0, 1.0)

with st.sidebar.expander("🤖 التليجرام"):
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")
    auto_send = st.checkbox("إرسال تلقائي", value=False)

asset_groups = {
    "⭐ المعادن": {"الذهب": "GC=F", "الفضة": "SI=F"},
    "💵 الفوركس": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "USD/CHF": "USDCHF=X"
    },
    "₿ الكريبتو": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
}

group = st.sidebar.selectbox("الفئة", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("الأداة", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم", ["5m", "15m", "30m", "1h", "4h", "1d"], index=1)

if st.sidebar.button("🔄 تحديث البيانات إجبارياً"):
    st.cache_data.clear()
    st.rerun()

# ==================== معالجة البيانات والإشارات ====================
df = get_data(symbol, timeframe)

if df is not None:
    # حساب المؤشرات (النسخة السريعة)
    df['EMA200'] = ta.ema(df['close'], length=200) if len(df) > 200 else ta.ema(df['close'], length=50)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]
    
    # منطق الإشارة السريع (عتبة 55 لإشارات أكثر)
    def get_signal():
        score = 0
        reasons = []
        # الاتجاه
        if curr['close'] > curr['EMA200']: score += 30; reasons.append("Above EMA200")
        else: score -= 30; reasons.append("Below EMA200")
        # الزخم
        if curr['RSI'] > 52: score += 25
        elif curr['RSI'] < 48: score -= 25
        
        if score >= 55: return "شراء 🚀", score, reasons
        if score <= -55: return "بيع 📉", abs(score), reasons
        return "انتظار ⚖️", score, reasons

    signal, confidence, reasons = get_signal()

    # ==================== العرض المرئي ====================
    st.title(f"🔍 {asset_name} - فريم {timeframe}")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("السعر الحالي", f"{curr['close']:,.4f}")
    col_m2.metric("RSI", f"{curr['RSI']:.1f}")
    col_m3.metric("ATR", f"{curr['ATR']:.4f}")

    c_left, c_right = st.columns([3, 1])

    with c_left:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="EMA"))
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("💡 التوصية")
        if "شراء" in signal:
            st.success(signal)
            tp = curr['close'] + (curr['ATR'] * 2.5)
            sl = curr['close'] - (curr['ATR'] * 1.5)
        elif "بيع" in signal:
            st.error(signal)
            tp = curr['close'] - (curr['ATR'] * 2.5)
            sl = curr['close'] + (curr['ATR'] * 1.5)
        else:
            st.warning(signal)
            tp = sl = None

        if tp:
            # حساب اللوت
            risk_cash = capital * (risk_p / 100)
            dist = abs(curr['close'] - sl)
            is_gold = "GC=F" in symbol
            lot = round(risk_cash / (dist * (100 if is_gold else 10000)), 2)
            
            st.info(f"🎯 TP: {tp:,.4f}\n\n🛑 SL: {sl:,.4f}")
            st.write(f"**حجم اللوت:** {max(lot, 0.01)}")
            
            # إرسال تليجرام
            if auto_send and bot_token and chat_id:
                alert_id = f"{symbol}_{df.index[-1]}"
                if st.session_state.last_alert_key != alert_id:
                    msg = f"🎯 إشارة Sniper\n• {asset_name}\n• {signal}\n• السعر: {curr['close']:,.4f}\n• TP: {tp:,.4f}\n• SL: {sl:,.4f}"
                    if send_telegram(bot_token, chat_id, msg):
                        st.session_state.last_alert_key = alert_id
                        st.toast("تم إرسال التنبيه!")

        st.markdown("---")
        st.write("**الأسباب:**")
        for r in reasons: st.write(f"• {r}")

else:
    st.error("❌ فشل في تحميل البيانات. يرجى محاولة:")
    st.write("1. الضغط على زر 'تحديث البيانات إجبارياً' في اليسار.")
    st.write("2. تغيير الفريم الزمني (مثلاً من 15m إلى 1h) ثم العودة مرة أخرى.")
    st.write("3. التأكد أن السوق مفتوح (اليوم ليس سبت أو أحد للعملات والمعادن).")

st.caption(f"تحديث: {datetime.now().strftime('%H:%M:%S')}")
