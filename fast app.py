import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات الصفحة
st.set_page_config(page_title="Sniper Elite v4.7 - Test Mode", layout="wide")

# دالة جلب البيانات مع معالجة الأخطاء المشهورة
def get_data(sym, tf):
    p_map = {"5m": "7d", "15m": "10d", "30m": "30d", "1h": "60d", "4h": "max", "1d": "max"}
    try:
        df = yf.download(sym, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except:
        return None

# القائمة الجانبية للتجربة
st.sidebar.header("🎯 إعدادات الاختبار")
symbol = st.sidebar.text_input("رمز العملة (Yahoo Finance)", value="GC=F")
timeframe = st.sidebar.selectbox("الفريم", ["5m", "15m", "30m", "1h", "4h", "1d"], index=1)

df = get_data(symbol, timeframe)

if df is not None:
    # حساب المؤشرات
    df['EMA200'] = ta.ema(df['close'], 200)
    df['RSI'] = ta.rsi(df['close'], 14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], 14)
    
    curr = df.iloc[-1]
    
    # --- منطق الإشارة السريع (المعدل) ---
    def check_signal():
        score = 0
        reasons = []
        
        # شرط الاتجاه (وزن أخف)
        if curr['close'] > curr['EMA200']: score += 30; reasons.append("Above EMA200")
        else: score -= 30; reasons.append("Below EMA200")
        
        # شرط RSI (نطاق أوسع)
        if curr['RSI'] > 52: score += 25
        elif curr['RSI'] < 48: score -= 25
        
        # النتيجة النهائية (قللنا العتبة لـ 55 لزيادة الإشارات)
        if score >= 55: return "شراء 🚀", score, reasons
        if score <= -55: return "بيع 📉", abs(score), reasons
        return "انتظار ⚖️", score, reasons

    signal, confidence, reasons = check_signal()

    # العرض
    st.title(f"🔍 تجربة الإشارات: {symbol}")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red'), name="EMA 200"))
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("النتيجة الحالية")
        if "شراء" in signal: st.success(signal)
        elif "بيع" in signal: st.error(signal)
        else: st.warning(signal)
        
        st.write(f"**مستوى الثقة:** {abs(confidence)}%")
        st.write("**الأسباب:**")
        for r in reasons: st.write(f"- {r}")

else:
    st.error("فشل في تحميل البيانات. جرب رمز آخر.")