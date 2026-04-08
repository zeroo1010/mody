import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# إعدادات واجهة المستخدم الاحترافية
st.set_page_config(page_title="Gold & Oil Elite v5.7", layout="wide", page_icon="💹")

# --- محرك جلب البيانات الذكي ---
@st.cache_data(ttl=30)
def get_safe_data(sym, tf):
    # موازنة الفترات الزمنية لضمان عدم رفض الطلب من ياهو فاينانس
    p_map = {"5m": "5d", "15m": "7d", "30m": "30d", "1h": "60d", "4h": "max"}
    try:
        df = yf.download(sym, period=p_map.get(tf, "30d"), interval=tf, progress=False, auto_adjust=True)
        if df.empty or len(df) < 100: return None
        # تنظيف الأعمدة
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(col).lower() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"حدث خطأ في الاتصال: {e}")
        return None

# --- القائمة الجانبية ---
st.sidebar.title("💹 المساعد الذكي المعتمد")
asset_choice = st.sidebar.selectbox("اختر السلعة", ["الذهب (Gold)", "النفط (Crude Oil)"])
symbols = {"الذهب (Gold)": "GC=F", "النفط (Crude Oil)": "CL=F"}
symbol = symbols[asset_choice]
timeframe = st.sidebar.selectbox("الفريم الزمني", ["5m", "15m", "30m", "1h", "4h"], index=1)

# شروط إدارة رأس المال
with st.sidebar.expander("💰 إدارة المخاطر"):
    balance = st.number_input("رأس المال ($)", value=1000.0)
    risk_pct = st.slider("نسبة المخاطرة لكل صفقة (%)", 0.5, 5.0, 1.0)

df = get_safe_data(symbol, timeframe)

if df is not None:
    # 1. حساب SuperTrend بطريقة "آمنة" (تجنب KeyError)
    st_data = ta.supertrend(df['high'], df['low'], df['close'], length=10, multiplier=3)
    # نستخدم iloc لضمان جلب عمود الاتجاه بغض النظر عن اسمه
    df['st_direction'] = st_data.iloc[:, 1] 
    
    # 2. مؤشرات التأكيد الفنية
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    # حساب الدعم والمقاومة اللحظية (أعلى/أقل سعر في 20 شمعة)
    df['recent_high'] = df['high'].rolling(window=20).max()
    df['recent_low'] = df['low'].rolling(window=20).min()

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # --- منطق الإدارة المعتمد (Decision Engine) ---
    def get_final_signal():
        score = 0
        reasons = []
        
        # قوة الاتجاه (SuperTrend)
        if curr['st_direction'] > 0:
            score += 50; reasons.append("🟢 اتجاه السوبر تريند: صاعد")
        else:
            score -= 50; reasons.append("🔴 اتجاه السوبر تريند: هابط")

        # التوافق مع المتوسط الكبير (EMA 200)
        if curr['close'] > curr['EMA200']:
            score += 20; reasons.append("🟢 السعر فوق المتوسط 200 (إيجابي)")
        else:
            score -= 20; reasons.append("🔴 السعر تحت المتوسط 200 (سلبي)")

        # الزخم (RSI)
        if 50 < curr['RSI'] < 70: score += 10
        elif 30 < curr['RSI'] < 50: score -= 10

        # نتيجة القرار
        if score >= 65: return "شراء قوي 🏹", score, reasons
        if score <= -65: return "بيع قوي 📉", abs(score), reasons
        return "انتظار (تذبذب) ⚖️", abs(score), reasons

    signal, confidence, reasons = get_final_signal()

    # --- واجهة العرض الاحترافية ---
    st.title(f"📊 تحليل {asset_choice} | {timeframe}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("السعر الحالي", f"${curr['close']:,.2f}")
    col2.metric("حالة RSI", f"{curr['RSI']:.1f}")
    col3.metric("ATR (السيولة)", f"{curr['ATR']:.2f}")
    col4.metric("الثقة", f"{confidence}%")

    chart_col, info_col = st.columns([3, 1])

    with chart_col:
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='orange', width=1.5), name="EMA 200"))
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with info_col:
        st.subheader("💡 التوصية النهائية")
        if "شراء" in signal:
            st.success(signal)
            tp = curr['close'] + (curr['ATR'] * 3) # أهداف السلع أكبر
            sl = curr['close'] - (curr['ATR'] * 1.5)
            lot = (balance * (risk_pct/100)) / ((curr['close'] - sl) * 100) if asset_choice == "الذهب (Gold)" else (balance * (risk_pct/100)) / ((curr['close'] - sl) * 1000)
            st.info(f"🎯 الهدف (TP): {tp:,.2f}\n\n🛑 الوقف (SL): {sl:,.2f}")
            st.metric("حجم اللوت المقترح", f"{abs(lot):.2f}")
        elif "بيع" in signal:
            st.error(signal)
            tp = curr['close'] - (curr['ATR'] * 3)
            sl = curr['close'] + (curr['ATR'] * 1.5)
            lot = (balance * (risk_pct/100)) / ((sl - curr['close']) * 100) if asset_choice == "الذهب (Gold)" else (balance * (risk_pct/100)) / ((sl - curr['close']) * 1000)
            st.info(f"🎯 الهدف (TP): {tp:,.2f}\n\n🛑 الوقف (SL): {sl:,.2f}")
            st.metric("حجم اللوت المقترح", f"{abs(lot):.2f}")
        else:
            st.warning(signal)
            st.write("نصيحة: السوق في حالة تذبذب حالياً، انتظر وضوح الاتجاه.")

        st.write("---")
        st.write("**تحليل الأسباب:**")
        for r in reasons: st.write(r)

else:
    st.error("فشل تحميل البيانات. يرجى الضغط على زر التحديث أو تغيير الفريم.")

st.sidebar.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
