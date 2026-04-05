import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import requests
import numpy as np

# إعداد الصفحة مع أيقونة تداول
st.set_page_config(page_title="Gold & Forex Sniper Elite v4.6", layout="wide", page_icon="🎯")

# ==================== Session State ====================
if 'last_alert_key' not in st.session_state:
    st.session_state.last_alert_key = None
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"
if 'signals_history' not in st.session_state:
    st.session_state.signals_history = pd.DataFrame(columns=['الوقت', 'الأصل', 'الإشارة', 'السعر', 'TP', 'SL', 'الثقة', 'حجم اللوت'])

# ==================== Functions ====================
def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

def send_telegram(token, chat_id, msg):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=8)
        return True
    except:
        return False

# ==================== Style & UI ====================
st.markdown(f"""
    <style>
    .main {{ background-color: {'#0e1117' if st.session_state.theme == 'dark' else '#f8f9fa'}; }}
    div[data-testid="stMetric"] {{ 
        background-color: {'#161b22' if st.session_state.theme == 'dark' else '#ffffff'}; 
        border: 1px solid {'#30363d' if st.session_state.theme == 'dark' else '#dee2e6'}; 
        border-radius: 12px; padding: 15px; 
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; }}
    .stTabs [data-baseweb="tab"] {{ padding: 10px 20px; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# ==================== Sidebar ====================
st.sidebar.title("🎯 Sniper Elite v4.6")

with st.sidebar.expander("🎨 التخصيص"):
    if st.button("تبديل مظهر (Dark/Light)"):
        toggle_theme()
        st.rerun()

with st.sidebar.expander("⚖️ إدارة المخاطر"):
    capital = st.number_input("رأس مال الحساب ($)", value=1000.0, step=100.0)
    risk_p = st.slider("مخاطرة الصفقة (%)", 0.1, 5.0, 1.0)
    
with st.sidebar.expander("🤖 التنبيهات"):
    bot_token = st.text_input("Bot Token", type="password")
    chat_id = st.text_input("Chat ID")
    auto_send = st.checkbox("إرسال لتليجرام", value=False)

# قائمة الأصول المحدثة
asset_groups = {
    "⭐ المعادن": {"الذهب": "GC=F", "الفضة": "SI=F"},
    "💵 الفوركس": {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "JPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X"
    },
    "₿ الكريبتو": {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
}

group = st.sidebar.selectbox("الفئة", list(asset_groups.keys()))
asset_name = st.sidebar.selectbox("الأصل", list(asset_groups[group].keys()))
symbol = asset_groups[group][asset_name]
timeframe = st.sidebar.selectbox("الفريم", ["5m", "15m", "30m", "1h", "4h", "1d"], index=3)

# ==================== Data Processing ====================
@st.cache_data(ttl=30)
def load_data(sym, tf):
    p_map = {"5m": "7d", "15m": "10d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    df = yf.download(sym, period=p_map[tf], interval=tf, progress=False)
    if df.empty or len(df) < 150: return None
    
    # حل مشكلة الـ Multi-Index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [str(c).lower() for c in df.columns]
    return df

df = load_data(symbol, timeframe)

if df is not None:
    # المؤشرات الفنية
    df['EMA200'] = ta.ema(df['close'], 200)
    df['EMA50'] = ta.ema(df['close'], 50)
    df['RSI'] = ta.rsi(df['close'], 14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], 14)
    df['ADX'] = ta.adx(df['high'], df['low'], df['close'], 14)['ADX_14']
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # منطق الشموع اليابانية
    body = abs(curr['close'] - curr['open'])
    lower_wick = min(curr['open'], curr['close']) - curr['low']
    is_pinbar = lower_wick > (body * 2) and curr['close'] > curr['open']
    
    # الفريم الأكبر للفلترة
    htf = "4h" if timeframe in ["5m", "15m", "30m", "1h"] else "1d"
    df_htf = load_data(symbol, htf)
    htf_trend = "UP" if (df_htf is not None and df_htf['close'].iloc[-1] > ta.ema(df_htf['close'], 200).iloc[-1]) else "DOWN"

    # حساب الإشارة
    def calculate_signal():
        score = 0
        reasons = []
        
        # الاتجاه
        if curr['close'] > curr['EMA200']: score += 35; reasons.append("Above EMA200")
        else: score -= 35; reasons.append("Below EMA200")
        
        # التوافق مع الفريم الكبير
        if (curr['close'] > curr['EMA200'] and htf_trend == "UP") or (curr['close'] < curr['EMA200'] and htf_trend == "DOWN"):
            score += 25; reasons.append("HTF Alignment")
            
        # الزخم
        if curr['RSI'] > 55: score += 15
        elif curr['RSI'] < 45: score -= 15
        
        # البرايس أكشن
        if is_pinbar: score += 10; reasons.append("Bullish Pinbar")
        
        if score >= 70: return "Strong Buy 🚀", score, reasons
        if score <= -70: return "Strong Sell 📉", abs(score), reasons
        return "Neutral ⚖️", abs(score), reasons

    signal_text, conf, sig_reasons = calculate_signal()

    # ==================== UI Tabs ====================
    tab_main, tab_history = st.tabs(["📊 التحليل المباشر", "📜 السجل"])

    with tab_main:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("السعر الحالي", f"{curr['close']:,.4f}")
        c2.metric("RSI", f"{curr['RSI']:.1f}")
        c3.metric("ATR (Volatility)", f"{curr['ATR']:.4f}")
        c4.metric("اتجاه HTF", htf_trend)

        col_left, col_right = st.columns([3, 1])
        
        with col_left:
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=2), name="EMA 200"))
            fig.update_layout(height=600, template="plotly_dark" if st.session_state.theme == "dark" else "plotly_white", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("💡 الإشارة")
            if "Buy" in signal_text:
                st.success(signal_text)
                tp = curr['close'] + (curr['ATR'] * 2.5)
                sl = curr['close'] - (curr['ATR'] * 1.5)
            elif "Sell" in signal_text:
                st.error(signal_text)
                tp = curr['close'] - (curr['ATR'] * 2.5)
                sl = curr['close'] + (curr['ATR'] * 1.5)
            else:
                st.warning(signal_text)
                tp = sl = None

            if tp:
                # حساب حجم اللوت (مبسط)
                risk_cash = capital * (risk_p / 100)
                dist = abs(curr['close'] - sl)
                # حساب تقريبي: النقطة في الفوركس تختلف عن الذهب
                is_gold = "GC=F" in symbol
                lot = round(risk_cash / (dist * (100 if is_gold else 10000)), 2)
                
                st.info(f"🎯 الهدف: {tp:,.4f}\n\n🛑 الوقف: {sl:,.4f}")
                st.metric("حجم اللوت المقترح", f"{max(lot, 0.01)}")
                st.caption(f"مخاطرة الصفقة: ${risk_cash:.2f}")

                # إرسال التنبيه
                alert_id = f"{symbol}_{df.index[-1]}"
                if auto_send and bot_token and chat_id and st.session_state.last_alert_key != alert_id:
                    msg = f"🎯 Sniper Elite Signal\n\nAsset: {asset_name}\nAction: {signal_text}\nPrice: {curr['close']:,.4f}\nTP: {tp:,.4f}\nSL: {sl:,.4f}"
                    if send_telegram(bot_token, chat_id, msg):
                        st.session_state.last_alert_key = alert_id
                        st.toast("تم إرسال التنبيه!")

    with tab_history:
        st.dataframe(st.session_state.signals_history, use_container_width=True)
else:
    st.error("خطأ في جلب البيانات. يرجى التأكد من الرمز (Symbol) أو الفريم الزمني.")

st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')} | Version 4.6")
