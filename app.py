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
    
    # 【最保守買入價】
    df['conservative_buy'] = np.minimum(df['low'].rolling(window=10).min(), df['var4'] * 0.99)
    
    # 【最激進賣出價】
    df['aggressive_sell'] = np.maximum(df['high'].rolling(window=10).max(), df['close'].rolling(window=10).mean() * 1.05)
    
    # ------------------ 【HDLW3 三層全戰況定義】 ------------------
    # 基礎安全邊際與距離計算
    df['safety_margin'] = ((df['close'] - df['var4']) / df['var4']) * 100
    
    # 【第一層動態趨勢值 1-100 計算】
    low_10 = df['close'].rolling(window=10).min()
    high_10 = df['close'].rolling(window=10).max()
    range_10 = np.where(high_10 == low_10, 1e-5, high_10 - low_10)
    df['trend_score'] = ((df['close'] - low_10) / range_10) * 100
    df['trend_score'] = np.clip(df['trend_score'], 1, 100)
    
    # 第一層：通道波段趨勢
    trend_desc = np.where(df['close'] > df['var4'], "🔴 多頭波段", "🟢 空頭防守")
    df['layer_trend'] = [
        f"{desc} ({score:.0f}) [支撐: ${v4:.2f} / 乖離: {sm:+.2f}%]" 
        for desc, score, v4, sm in zip(trend_desc, df['trend_score'], df['var4'], df['safety_margin'])
    ]
    
    # 第二層：主力大單流向（精確切分三階段）
    df['vol_ma'] = df['volume'].rolling(window=10).mean()
    df['vol_ratio'] = df['volume'] / (df['vol_ma'] + 1e-9)
    
    def get_vol_status(ratio):
        if ratio >= 2.0:
            return "⚡ 主力極致爆量（強烈火拼中）"
        elif ratio >= 1.0:
            return "🟢 資金健康流入（大戶悄悄進場）"
        else:
            return "💤 籌碼縮量沉悶（純散戶震盪市）"
            
    df['layer_flow'] = df['vol_ratio'].apply(get_vol_status)
    
    # 第三層：安全空間邊際（全面升級精確切分三階段）
    cond_safety = [
        df['safety_margin'] <= 1.5,
        (df['safety_margin'] > 1.5) & (df['safety_margin'] <= 4.0),
        df['safety_margin'] > 4.0
    ]
    choice_safety = [
        "✅ 黃金支撐區（安全邊際高）",
        "🟡 穩健觀望區（適度控倉期）",
        "⚠️ 遠離支撐線（嚴防追高滑點）"
    ]
    df['layer_safety'] = np.select(cond_safety, choice_safety, default="⚠️ 遠離支撐線（嚴防追高滑點）")
    
    return df

# --- 介面第一區：隨時換股輸入框 ---
symbol = st.text_input("🔍 請輸入操作美股代號（支援隨時自由換股）：", value="PLTR").strip().upper()
time_frame = st.radio("⏱️ 選擇即時時框：", ["5分", "15分", "30分", "1小時", "日線"], index=4, horizontal=True)

if symbol:
    with st.spinner('HDLW3 雲端高速對接計算中...'):
        raw_data = fetch_yahoo_data(symbol, time_frame)
        if raw_data.empty:
            st.error(f"❌ 無法取得 {symbol} 實時數據，請檢查美股代號是否正確、或該時框目前是否有盤前交易量。")
        else:
            df = calculate_hdlw3_complete(raw_data)
            curr = df.iloc[-1]
            
            # --- 介面第二區：精準買賣點位看板 ---
            st.markdown(f"### 🎯 {symbol} 即時雙向防守點位")
            st.metric(label="當前市價", value=f"${curr['close']:.2f}")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.info(f"🛡️ 【最保守買入價】\n\n**${curr['conservative_buy']:.2f}**\n\n*(非此價不輕易出手)*")
            with col_p2:
                st.warning(f"🚀 【最激進賣出價】\n\n**${curr['aggressive_sell']:.2f}**\n\n*(多頭極致停利點)*")
            
            st.markdown("---")
            
            # --- 介面第三區：HDLW3 三層全戰況動態審查 ---
            st.markdown("### 📊 HDLW3 三層戰況系統評估")
            
            # 第一層
            if "🔴" in curr['layer_trend']:
                st.success(f"**【第一層：波段趨勢】** {curr['layer_trend']}")
            else:
                st.error(f"**【第一層：波段趨勢】** {curr['layer_trend']}")
                
            # 第二層（根據三階段動態給予視覺顏色提示）
            if "⚡" in curr['layer_flow']:
                st.error(f"**【第二層：大單流向】** {curr['layer_flow']} [倍數: {curr['vol_ratio']:.2f}x]")
            elif "🟢" in curr['layer_flow']:
                st.success(f"**【第二層：大單流向】** {curr['layer_flow']} [倍數: {curr['vol_ratio']:.2f}x]")
            else:
                st.write(f"**【第二層：大單流向】** {curr['layer_flow']} [倍數: {curr['vol_ratio']:.2f}x]")
                
            # 第三層（根據最新三階段動態給予完美視覺顏色提示）
            if "✅" in curr['layer_safety']:
                st.success(f"**【第三層：空間邊際】** {curr['layer_safety']}")
            elif "🟡" in curr['layer_safety']:
                st.info(f"**【第三層：空間邊際】** {curr['layer_safety']}")
            else:
                st.warning(f"**【第三層：空間邊際】** {curr['layer_safety']}")
                
            st.markdown("---")
            
            # --- 介面第四區：智慧自動買入觸發提醒 ---
            st.subheader("📋 鸚鵡操盤決策提醒")
            
            # 決策聯動：主力大單達到「溫補量以上」(vol_ratio >= 1.0) 且符合趨勢與支撐即可觸發
            if "🔴" in curr['layer_trend'] and (curr['close'] <= curr['var4'] * 1.015 or curr['close'] <= curr['conservative_buy']):
                if curr['vol_ratio'] >= 1.0:
                    st.error(f"🚨 🔴 核心提示：【主力資金大單湧入 {symbol} 保守買入區】！完美符合三層黃金共振，請執行買入命令！")
                else:
                    st.success("💡 提示：價格已落入最保守買入區附近，但主力大單尚未明顯拉抬，請搬好小板凳，盯緊成交量爆發。")
            elif "🟢" in curr['layer_trend']:
                if curr['vol_ratio'] >= 2.0:
                    st.error("⚠️ 警告：空頭通道出現極致暴量洗盤或砸盤！大單方向不明，當沖狀態下嚴格禁止盲目接刀。")
                elif curr['vol_ratio'] >= 1.0:
                    st.warning("⚠️ 警告：空頭通道雖有大戶資金悄悄進場溫補，但波段結構仍弱，短線切勿盲目重倉。")
                else:
                    st.warning("⚠️ 警告：趨勢偏弱，且無主力資金承接（純散戶冷清）。請分批回收現金，多看少動。")
            else:
                if curr['close'] >= curr['aggressive_sell'] * 0.98:
                    st.error(f"🔥 提示：價格已極度逼近【最激進賣出價 (${curr['aggressive_sell']:.2f})】！短線處於極速超買頂點，切勿追高，有持倉者建議分批落袋為安。")
                else:
                    st.write("📊 提示：股價在通道中間健康震盪。未觸及最保守買入價，亦未到激進賣出價，手癢想沖請輕倉。")

            st.markdown("---")

            # --- 介面第五區：核心指標說明書 ---
            st.markdown("### 📈 HDLW3 核心量化指標說明書")
            st.markdown(f"""
            * **第一層：波段趨勢 `(趨勢值 1-100) [支撐 / 乖離]`**
                * `🔴 多頭波段`：市價站穩動態均線之上，波段動能看漲。
                * `🟢 空頭防守`：市價處於動態均線之下，趨勢偏弱應保守。
                * `[趨勢值含意說明區間]`：
                    * **【85 ~ 100】極致過熱區**：多頭強烈噴發，短線乖離拉高，盲目追高易套牢。
                    * **【50 ~ 84】多頭前進區**：多方掌控路權，回踩支撐不破即為健康的多頭蓄勢。
                    * **【15 ~ 49】空頭震盪區**：市場多空拉鋸，多為反彈或打底階段，結構不穩。
                    * **【1 ~ 14】超跌伏擊區**：空頭砸盤力道接近衰竭，通常配合第三層出現「黃金支撐」。
                * `[支撐價格]`：動態 Var4 黃金均線防禦位，趨勢多空的生命線。
                * `[即時乖離]`：當前價格距離 Var4 的百分比。正值為多頭延伸，負值為超跌打底。
            * **第二層：大單流向 `(當前量 / 10期均量)`**
                * `⚡ 主力極致爆量（強烈火拼中）`：當期量 $\\ge$ 10期均量的 **2.0 倍以上**，主力大單瘋狂火拼，極易噴出日內大行情。
                * `🟢 資金健康流入（大戶悄悄進場）`：當期量介於 **1.0 倍 到 2.0 倍之間**，資金健康溫補，屬於大戶悄悄吃單階段。
                * `💤 籌碼縮量沉悶（純散戶震盪市）`：當期量 **低於 1.0 倍均量**，成交量低迷降溫，無主力參與，多為散戶磨人震盪市。
            * **第三層：空間邊際 `(距離 Var4 %)`**
                * `✅ 黃金支撐區`：股價與 Var4 支撐位距離 $\\le$ 1.5%，屬於安全邊際極高的低風險伏擊區。
                * `🟡 穩健觀望區`：股價與 Var4 支撐位距離介於 1.5% 到 4.0% 之間，屬於健康上漲或合理回撤的緩衝防禦帶，宜適度控倉。
                * `⚠️ 遠離支撐線`：股價已拉離支撐線 > 4.0%，短線極易遭遇高位洗盤或滑點風險，嚴禁盲目當沖追高。
            """)

            # 最底部分頁簽名（更新至三階段完美對齊）
            st.caption(f"ℹ️ HDLW3 動態 Var4 支撐: ${curr['var4']:.2f} | 趨勢強弱值: {curr['trend_score']:.0f}/100 | 量能倍數: {curr['vol_ratio']:.2f}x | 安全邊際距離: {curr['safety_margin']:.2f}%")
