import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Gold & Oil Elite Sniper v5.5", layout="wide", page_icon="🛢️")

# --- دالة جلب البيانات مع ضبط المدة للسلع ---
@st.cache_data(ttl=30)
def get_commodity_data(sym, tf):
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max"}
    try:
        df = yf.download(sym, period=p_map.get(tf, "30d"), interval=tf, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except: return None

# --- الجانب الأيسر (الإعدادات) ---
st.sidebar.title("🚀 Commodity Radar")
asset_choice = st.sidebar.selectbox("اختر السلعة", ["الذهب (Gold)", "النفط (Crude Oil)"])
symbols = {"الذهب (Gold)": "GC=F", "النفط (Crude Oil)": "CL=F"}
symbol = symbols[asset_choice]

timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h"], index=1)

df = get_commodity_data(symbol, timeframe)

if df is not None:
    # 1. حساب مؤشر SuperTrend (قوي جداً للذهب والنفط)
    # ملاحظة: يستخدم 10 كفترة و 3 كمعامل ضرب
    st_data = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    df['st_direction'] = st_data['SUPERTd_10_3.0'] # 1 للاتجاه الصاعد، -1 للهابط
    
    # 2. المتوسطات والمؤشرات المساعدة
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # --- منطق الإشارة المخصص للسلع ---
    def get_commodity_signal():
        score = 0
        reasons = []
        
        # شرط 1: اتجاه السوبر تريند (وزن عالي 40)
        if curr['st_direction'] == 1:
            score += 40; reasons.append("✅ SuperTrend: صاعد")
        else:
            score -= 40; reasons.append("❌ SuperTrend: هابط")

        # شرط 2: الموقع من المتوسط 200
        if curr['close'] > curr['EMA200']:
            score += 20; reasons.append("✅ فوق EMA200 (تريند عام صاعد)")
        else:
            score -= 20; reasons.append("❌ تحت EMA200 (تريند عام هابط)")

        # شرط 3: الزخم RSI
        if curr['RSI'] > 55: score += 15
        elif curr['RSI'] < 45: score -= 15

        # تحديد النتيجة (عتبة 60 للذهب والنفط لضمان الجودة)
        if score >= 60: return "شراء قوي 🚀", score, reasons
        if score <= -60: return "بيع قوي 📉", abs(score), reasons
        return "انتظار ⚖️", score, reasons

    signal, conf, reasons = get_commodity_signal()

    # --- العرض المرئي ---
    st.title(f"📊 تحليل {asset_choice} المباشر")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("السعر الحالي", f"${curr['close']:,.2f}")
    m2.metric("حالة RSI", f"{curr['RSI']:.1f}")
    m3.metric("تذبذب ATR", f"{curr['ATR']:.2f}")

    col_chart, col_sig = st.columns([3, 1])

    with col_chart:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='red', width=1.5), name="EMA 200"))
        # إضافة مستويات الدعم والمقاومة السريعة
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_sig:
        st.subheader("💡 التوصية")
        if "شراء" in signal:
            st.success(signal)
            # أهداف الذهب والنفط تكون أكبر (2.5 للهدف و 1.5 للوقف)
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
            st.info(f"🎯 الهدف: {tp:,.2f}\n\n🛑 الوقف: {sl:,.2f}")
            st.write(f"**نسبة الثقة:** {abs(conf)}%")
        
        st.markdown("---")
        st.write("**لماذا هذه الإشارة؟**")
        for r in reasons: st.write(r)

else:
    st.error("فشل تحميل بيانات السلع. تأكد أن الرمز صحيح والسوق مفتوح.")

st.caption(f"تحديث تلقائي: {datetime.now().strftime('%H:%M:%S')}")
