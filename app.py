import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import plotly.graph_objects as go

# إعداد الصفحة
st.set_page_config(page_title="Smart Trader Pro", layout="wide")

# --- دالة جلب البيانات مع الفلاتر الجديدة ---
@st.cache_data(ttl=60)
def get_advanced_data(symbol, tf):
    p_map = {"5m": "5d", "15m": "7d", "1h": "30d", "4h": "max"}
    df = yf.download(symbol, period=p_map[tf], interval=tf, progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.columns = [col.lower() for col in df.columns]
    
    # إضافة المؤشرات الأساسية
    df['EMA200'] = ta.ema(df['close'], length=200)
    df['RSI'] = ta.rsi(df['close'], length=14)
    df['VOL_AVG'] = ta.sma(df['volume'], length=20) # متوسط السيولة
    
    # تعريف شمعة الابتلاع (Engulfing)
    df['is_bullish'] = df['close'] > df['open']
    df['is_engulfing_bull'] = (df['is_bullish']) & (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))
    df['is_engulfing_bear'] = (~df['is_bullish']) & (df['close'] < df['open'].shift(1)) & (df['open'] > df['close'].shift(1))
    
    return df

# --- واجهة المستخدم ---
st.sidebar.title("🛠️ إعدادات الرادار")
symbol_input = st.sidebar.selectbox("اختر الأصل", ["BTC-USD", "ETH-USD", "GC=F", "EURUSD=X", "GBPUSD=X"])
tf_input = st.sidebar.selectbox("فريم التحليل", ["5m", "15m", "1h", "4h"], index=1)

try:
    df = get_advanced_data(symbol_input, tf_input)
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    # --- منطق الإشارة الاحترافي ---
    score = 0  # نظام نقاط لقوة الإشارة
    
    # 1. فلتر الاتجاه
    trend = "صاعد" if curr['close'] > curr['EMA200'] else "هابط"
    if trend == "صاعد": score += 1
    else: score -= 1
    
    # 2. فلتر الزخم (RSI)
    if 40 < curr['RSI'] < 60: momentum = "متذبذب"
    elif curr['RSI'] >= 60: 
        momentum = "قوي شرائي"
        score += 1
    else: 
        momentum = "قوي بيعي"
        score -= 1

    # 3. فلتر السيولة
    high_vol = curr['volume'] > curr['VOL_AVG']
    if high_vol: score *= 1.5 # مضاعفة أهمية الإشارة لو السيولة عالية

    # --- اتخاذ القرار النهائي ---
    st.title(f"🚀 تحليل ذكي: {symbol_input}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("السعر الحالي", f"{curr['close']:,.2f}")
    col2.metric("حالة السيولة", "عالية 🔥" if high_vol else "ضعيفة ❄️")
    col3.metric("قوة الإشارة", f"{abs(score):.1f}")

    if score >= 1.5:
        st.success(f"💎 **إشارة شراء قوية**: الاتجاه {trend} مع سيولة تدعم الصعود.")
    elif score <= -1.5:
        st.error(f"📉 **إشارة بيع قوية**: الاتجاه {trend} مع ضغط بيعي واضح.")
    else:
        st.warning("⚠️ **منطقة حيادية**: لا توجد سيولة كافية أو تضارب في المؤشرات.")

    # الرسم البياني
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="الشموع")])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], line=dict(color='yellow', width=1.5), name="EMA 200"))
    
    # إضافة علامات الابتلاع على الرسم (لو حابب)
    bull_signals = df[df['is_engulfing_bull']]
    fig.add_trace(go.Scatter(x=bull_signals.index, y=bull_signals['low']*0.999, mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'), name="ابتلاع شرائي"))

    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"حدث خطأ في جلب البيانات: {e}")
