import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 手機響應式頁面配置
st.set_page_config(page_title="📲 HDLW3 全戰況決策面板", layout="centered")
st.title("📲 HDLW3 美股無限制決策面板")

# 核心數據獲取函數
def fetch_yahoo_data(symbol, time_frame):
    mapping = {"1分": "1m", "5分": "5m", "15分": "15m", "30分": "30m", "1小時": "1h", "日線": "1d", "週線": "1wk"}
    period_map = {"1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d", "1h": "730d", "1d": "max", "1wk": "max"}
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=mapping[time_frame], period=period_map[mapping[time_frame]])
        return df
    except Exception as e:
        return pd.DataFrame()

# HDLW3 三層戰況演算法計算邏輯
def calculate_hdlw3_complete(df):
    df['close'] = df['Close']
    df['high'] = df['High']
    df['low'] = df['Low']
    df['volume'] = df['Volume']
    
    # ------------------ 【HDLW3 價格區間精確計算】 ------------------
    # 基礎動態支撐 (Var4)
    df['var4'] = df['close'].rolling(window=10).mean() * 0.98
    
    # 【最保守買入價】：過去10期最低價的最低防守位，或是 Var4 的 99%（取其低者，確保最安全）
    df['conservative_buy'] = np.minimum(df['low'].rolling(window=10).min(), df['var4'] * 0.99)
    
    # 【最激進賣出價】：動態通道的極速擴張軌（MA+標準差），或是過去10期最高價的 1.03 倍
    df['aggressive_sell'] = np.maximum(df['high'].rolling(window=10).max(), df['close'].rolling(window=10).mean() * 1.05)
    
    # ------------------ 【HDLW3 三層全戰況定義】 ------------------
    # 第一層：通道波段趨勢 (Trend Layer)
    df['layer_trend'] = np.where(df['close'] > df['var4'], "🔴 多頭波段（動能續強）", "🟢 空頭防守（靜待打底）")
    
    # 第二層：主力大單流向 (Money Flow Layer)
    df['vol_ma'] = df['volume'].rolling(window=10).mean()
    df['layer_flow'] = np.where(df['volume'] > df['vol_ma'] * 1.5, "🔥 主力金湧入（大單進場）", "💤 散戶縮量（籌碼冷清）")
    df['is_volume_spike'] = df['volume'] > df['vol_ma'] * 1.5
    
    # 第三層：安全空間空間 (Safety Space Layer)
    df['safety_margin'] = ((df['close'] - df['var4']) / df['var4']) * 100
    df['layer_safety'] = np.where(df['safety_margin'] <= 1.5, "✅ 黃金支撐區（安全邊際高）", "⚠️ 遠離支撐線（嚴防追高滑點）")
    
    return df

# --- 介面第一區：隨時換股輸入框 ---
symbol = st.text_input("🔍 請輸入操作美股代號（支援隨時自由換股）：", value="PLTR").strip().upper()
time_frame = st.radio("⏱️ 選擇即時時框：", ["5分", "15分", "30分", "1小時", "日線"], index=4, horizontal=True)

if symbol:
    with st.spinner('HDLW3 雲端高速對接計算中...'):
        raw_data = fetch_yahoo_data(symbol, time_frame)
        if raw_data.empty:
            st.error(f"❌ 無法取得 {symbol} 實時數據，請檢查美股代號。")
        else:
            df = calculate_hdlw3_complete(raw_data)
            curr = df.iloc[-1]
            
            # --- 介面第二區：精準買賣點位看板 (左右並列，手機單手秒看) ---
            st.markdown(f"### 🎯 {symbol} 即時雙向防守點位")
            
            # 主報價卡片
            st.metric(label="當前市價", value=f"${curr['close']:.2f}")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.info(f"🛡️ 【最保守買入價】\n\n**${curr['conservative_buy']:.2f}**\n\n*(非此價不輕易出手)*")
            with col_p2:
                st.warning(f"🚀 【最激進賣出價】\n\n**${curr['aggressive_sell']:.2f}**\n\n*(多頭極致停利點)*")
            
            st.markdown("---")
            
            # --- 介面第三區：HDLW3 三層全戰況動態審查 ---
            st.markdown("### 📊 HDLW3 三層戰況系統評估")
            
            # 第一層：趨勢
            if "🔴" in curr['layer_trend']:
                st.success(f"**【第一層：波段趨勢】** {curr['layer_trend']}")
            else:
                st.error(f"**【第一層：波段趨勢】** {curr['layer_trend']}")
                
            # 第二層：資金
            if "🔥" in curr['layer_flow']:
                st.error(f"**【第二層：大單流向】** {curr['layer_flow']}")
            else:
                st.write(f"**【第二層：大單流向】** {curr['layer_flow']}")
                
            # 第三層：安全邊際
            if "✅" in curr['layer_safety']:
                st.success(f"**【第三層：空間邊際】** {curr['layer_safety']}")
            else:
                st.warning(f"**【第三層：空間邊際】** {curr['layer_safety']}")
                
            st.markdown("---")
            
            # --- 介面第四區：智慧自動買入觸發提醒 ---
            st.subheader("📋 鸚鵡操盤決策提醒")
            
            # 觸發核心買入密語邏輯：
            # 條件：多頭波段內 + 屬於黃金支撐區(或跌破保守買入) + 主力放量進場
            if "多頭" in curr['layer_trend'] and (curr['close'] <= curr['var4'] * 1.015 or curr['close'] <= curr['conservative_buy']):
                if curr['is_volume_spike']:
                    st.error(f"🚨 🔴 核心提示：【主力資金大單湧入 {symbol} 保守買入區】！完美符合三層黃金共振，請執行買入命令！")
                else:
                    st.success("💡 提示：價格已落入最保守買入區附近，但主力大單尚未明顯拉抬，請搬好小板凳，盯緊成交量爆發。")
            elif "空頭" in curr['layer_trend']:
                if curr['is_volume_spike']:
                    st.error("⚠️ 警告：空頭通道出現爆量洗盤或砸盤！大單方向不明，當沖狀態下嚴格禁止盲目接刀。")
                else:
                    st.warning("⚠️ 警告：趨勢偏弱，且無主力資金承接。請分批回收現金，多看少動。")
            else:
                if curr['close'] >= curr['aggressive_sell'] * 0.98:
                    st.error(f"🔥 提示：價格已極度逼近【最激進賣出價 (${curr['aggressive_sell']:.2f})】！多頭動能處於短線極速超買頂點，切勿追高，有持倉者建議分批落袋為安。")
                else:
                    st.write("📊 提示：股價在通道中間健康震盪。未觸及最保守買入價，亦未到激進賣出價，手癢想沖請輕倉。")

            # 底部署名
            st.caption(f"ℹ️ HDLW3 動態 Var4 支撐位為: ${curr['var4']:.2f} | 當前距離安全邊際: {curr['safety_margin']:.2f}%")
