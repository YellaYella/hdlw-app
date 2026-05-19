import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="HDLW3 免開戶智能面板", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .reportview-container .main .block-container { max-width: 100%; padding-top: 1rem; padding-bottom: 1rem; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-size: 16px; font-weight: bold; }
    .card { padding: 15px; border-radius: 10px; margin-bottom: 15px; color: white; }
    .low-risk { background-color: #1e4620; border-left: 5px solid #4caf50; }
    .med-risk { background-color: #5c4300; border-left: 5px solid #ffeb3b; }
    .high-risk { background-color: #4a1212; border-left: 5px solid #f44336; }
    </style>
""", unsafe_allow_html=True)

st.title("📲 HDLW3 美股無限制面板")
st.caption("🟢 免開戶免密碼版 · 雅虎財經即時驅動")

@st.cache_data(ttl=5)
def fetch_yahoo_data(symbol, time_frame):
    tf_map = {
        "1分": ("1m", "1d"), "5分": ("5m", "5d"), "15分": ("15m", "5d"),
        "30分": ("30m", "5d"), "1小時": ("60m", "7d"), "日線": ("1d", "3mo"), "週線": ("1wk", "1y")
    }
    interval, period = tf_map[time_frame]
    
    # 【最新優化點】：移除舊版 requests 衝突，改由 yf 官方機制自動處理連線
    ticker = yf.Ticker(symbol.upper())
    data = ticker.history(period=period, interval=interval)
    
    if data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    df = data.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={df.columns[0]: 'time'})
    return df

def calculate_hdlw3(df):
    if df.empty or len(df) < 34: return df
    df['typ'] = (df['low'] + df['open'] + df['close'] + df['high']) / 4
    df['var1'] = df['typ'].shift(1)
    df['abs_diff'] = (df['low'] - df['var1']).abs()
    df['max_diff'] = (df['low'] - df['var1']).apply(lambda x: max(x, 0))
    df['sma_abs'] = df['abs_diff'].ewm(alpha=1/13, adjust=False).mean()
    df['sma_max'] = df['max_diff'].ewm(alpha=1/10, adjust=False).mean()
    df['var2'] = df['sma_abs'] / df['sma_max']
    df['var3'] = df['var2'].ewm(span=10, adjust=False).mean()
    df['var4'] = df['low'].rolling(window=33).min()
    df['cond_var3'] = np.where(df['low'] <= df['var4'], df['var3'], 0)
    df['var5'] = df['cond_var3'].ewm(span=3, adjust=False).mean()
    df['var5_ref'] = df['var5'].shift(1)
    df['主力金'] = np.where(df['var5'] > df['var5_ref'], df['var5'].clip(upper=150), 0)
    df['洗盤'] = np.where(df['var5'] < df['var5_ref'], df['var5'].clip(upper=150), 0)
    df['llv_27'] = df['low'].rolling(window=27).min()
    df['hhv_27'] = df['high'].rolling(window=27).max()
    df['rsv'] = ((df['close'] - df['llv_27']) / (df['hhv_27'] - df['llv_27'])) * 100
    df['sma_rsv_5'] = df['rsv'].ewm(alpha=1/5, adjust=False).mean()
    df['sma_rsv_3'] = df['sma_rsv_5'].ewm(alpha=1/3, adjust=False).mean()
    df['趨勢'] = 3 * df['sma_rsv_5'] - 2 * df['sma_rsv_3']
    return df

symbol = st.text_input("🔍 請輸入美股代號：", value="SOXL").strip()
time_frame = st.radio("⏱️ 選擇分析時框：", ["1分", "5分", "15分", "30分", "1小時", "日線", "週線"], index=1, horizontal=True)

if symbol:
    with st.spinner('雅虎財經連線計算中...'):
        raw_data = fetch_yahoo_data(symbol, time_frame)
        if raw_data.empty:
            st.error(f"❌ 無法取得 {symbol} 數據。請確認美股代號正確。")
        else:
            df = calculate_hdlw3(raw_data)
            curr = df.iloc[-1]
            price = curr['close']
            var4_support = curr['var4'] if not pd.isna(curr['var4']) else price * 0.95
            trend = curr['趨勢']
            main_gold = curr['主力金']
            wash_plate = curr['洗盤']
            
            reason = "📈 趨勢偏弱，目前處於盤整尋底階段。"
            if main_gold > 0: reason = f"🔥 偵測到【主力金爆發 (值:{main_gold:.1f})】，主力資金吸籌中！"
            elif wash_plate > 0: reason = f"🟢 偵測到【主力洗盤完畢 (值:{wash_plate:.1f})】，築底完成。"
            elif trend <= 10: reason = "🟡 進入【準備買】極度超跌區，隨時迎來強烈反彈！"
            
            st.subheader(f"📊 {symbol.upper()} [{time_frame}] 決策报告")
            st.metric("當前最新股價", f"${price:.3f}")
            st.write(f"**💡 進場原因核心判定：** {reason}")
            st.write("---")
            
            stop_loss = var4_support * 0.97
            
            st.markdown(f'<div class="card low-risk"><h3>🟢 低風險策略 (保守抄底)</h3><p><b>👉 建議入場價：</b> ${var4_support:.3f}</p><p><b>🎯 建議停利價：</b> ${price * 1.05:.3f}</p><p><b>🛑 鋼鐵停損價：</b> ${stop_loss:.3f}</p></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card med-risk"><h3>🟡 中風險策略 (穩健市價)</h3><p><b>👉 建議入場價：</b> ${price:.3f}</p><p><b>🎯 建議停利價：</b> ${price * 1.10:.3f}</p><p><b>🛑 鋼鐵停損價：</b> ${stop_loss:.3f}</p></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card high-risk"><h3>🔴 高風險策略 (當沖追擊)</h3><p><b>👉 建議入場價：</b> ${price * 1.01:.3f}</p><p><b>🎯 建議停利價：</b> ${price * 1.15:.3f}</p><p><b>🛑 鋼鐵停損價：</b> ${stop_loss:.3f}</p></div>', unsafe_allow_html=True)