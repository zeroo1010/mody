import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Gold & Oil Professional", layout="wide", page_icon="💹")

# دالة جلب البيانات (مؤمنة ضد أخطاء ياهو)
@st.cache_data(ttl=10) # الكاش 10 ثواني فقط عشان التحديث يكون فعال
def get_data(sym, tf):
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max"}
    try:
        df = yf.download(sym, period=p_map.get(tf, "30d"), interval=tf, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100: return None
        # تنظيف الأعمدة (السطر ده ضروري عشان السكربت ما يوقفش)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except:
        return None

# --- القائمة الجانبية ---
st.sidebar.title("💹 رادار الذهب والنفط")

# زر التحديث (Refresh) - الطريقة الرسمية المضمونة
if st.sidebar.button("🔄 تحديث البيانات الآن", use_container_width=True):
    st.cache_data.clear() # يمسح الذاكرة لجلب سعر جديد
    st.rerun()            # يعيد تشغيل الصفحة

asset_choice = st.sidebar.selectbox("اختر السلعة", ["الذهب (Gold)", "النفط (Crude Oil)"])
symbols = {"الذهب (Gold)": "GC=F", "النفط (Crude Oil)": "CL=F"}
symbol = symbols[asset_choice]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h"], index=1)

df = get_data(symbol, timeframe)

if df is not None:
    # حساب السوبر تريند (بطريقة الـ iloc عشان نتجنب الـ KeyError)
    st_data = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    df['st_direction'] = st_data.iloc[:, 1] 
    
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    curr = df.iloc[-1]

    # منطق الإشارة
    def get_signal():
        score = 0
        if curr['st_direction'] > 0: score += 50
        else: score -= 50
        if curr['close'] > curr['EMA200']: score += 20
        else: score -= 20
        
        if score >= 60: return "شراء قوي 🚀", score
        if score <= -60: return "بيع قوي 📉", abs(score)
        return "انتظار ⚖️", abs(score)

    signal, conf = get_signal()

    # --- العرض ---
    st.title(f"📊 {asset_choice} | {timeframe}")
    st.caption(f"توقيت البيانات: {datetime.now().strftime('%H:%M:%S')}")

    col1, col2 = st.columns([3, 1])
    
    with col1:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='orange'), name="EMA 200"))
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("💡 التوصية")
        if "شراء" in signal: st.success(signal)
        elif "بيع" in signal: st.error(signal)
        else: st.warning(signal)
        
        st.metric("السعر الحالي", f"${curr['close']:,.2f}")
        st.write(f"نسبة الثقة: {conf}%")
        
        if signal != "انتظار ⚖️":
            tp = curr['close'] + (curr['ATR'] * 2.5) if "شراء" in signal else curr['close'] - (curr['ATR'] * 2.5)
            sl = curr['close'] - (curr['ATR'] * 1.5) if "شراء" in signal else curr['close'] + (curr['ATR'] * 1.5)
            st.info(f"🎯 الهدف: {tp:,.2f}\n\n🛑 الوقف: {sl:,.2f}")
else:
    st.error("فشل في تحميل البيانات. يرجى الضغط على زر التحديث.")
