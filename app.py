import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="專業級股票分析系統", layout="wide")

st.sidebar.header("搜尋條件")
input_id = st.sidebar.text_input("請輸入股票代號", value="8358")
period_option = st.sidebar.selectbox("顯示範圍", ["6mo", "1y", "2y"], index=1)

# --- 2. 資料獲取函數 ---
@st.cache_data(ttl=3600)
def get_stock_data(symbol_num):
    for suffix in [".TW", ".TWO"]:
        target = f"{symbol_num}{suffix}"
        df = yf.download(target, period="5y", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            return df, target
    return pd.DataFrame(), None

# --- 3. 核心邏輯執行 ---
df, final_id = get_stock_data(input_id)

if not df.empty:
    # A. 計算價格均線 (MA)
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    df['MA120'] = df['Close'].rolling(120).mean()
    df['MA240'] = df['Close'].rolling(240).mean()
    
    # B. 計算成交量顏色與均線
    df['Vol_Color'] = np.where(df['Close'] >= df['Close'].shift(1), 
                               'rgba(255, 0, 0, 0.4)', 'rgba(0, 255, 0, 0.4)')
    df['Vol_MA5'] = df['Volume'].rolling(5).mean()

    # C. 裁切顯示範圍
    if period_option == "6mo":
        plot_df = df.tail(125)
    elif period_option == "1y":
        plot_df = df.tail(250)
    else:
        plot_df = df.tail(500)

    # D. 動態 Y 軸刻度邏輯
    latest_price = float(plot_df['Close'].iloc[-1])
    if latest_price < 100:
        g_dtick, t_dtick = 0.1, 1.0
    elif 100 <= latest_price < 500:
        g_dtick, t_dtick = 1.0, 5.0
    elif 500 <= latest_price < 1000:
        g_dtick, t_dtick = 1.0, 10.0
    else:
        g_dtick, t_dtick = 5.0, 25.0

    # --- 4. 繪圖設定 ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.05, row_heights=[0.75, 0.25])

    # [價格區] - 收盤價
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df['Close'], 
        mode='lines+markers', name='收盤價',
        line=dict(color='#1f77b4', width=1.5), 
        marker=dict(size=4),
        hoverlabel=dict(namelength=-1)
    ), row=1, col=1)

    # [價格區] - 均線
    ma_settings = [
        ('MA5', 'rgba(255, 165, 0, 0.5)'),
        ('MA10', 'rgba(255, 0, 255, 0.5)'),
        ('MA60', 'rgba(0, 128, 0, 0.4)'),
        ('MA120', 'rgba(255, 0, 0, 0.4)'),
        ('MA240', 'rgba(128, 0, 128, 0.4)')
    ]
    for ma_name, color in ma_settings:
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[ma_name], 
            mode='lines', name=ma_name,
            line=dict(width=0.8, color=color),
            hoverinfo='skip'
        ), row=1, col=1)

    # [成交量區]
    vol_colors = df.loc[plot_df.index, 'Vol_Color']
    fig.add_trace(go.Bar(
        x=plot_df.index, y=plot_df['Volume'], 
        name='成交量', 
        marker_color=vol_colors,
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df['Vol_MA5'], 
        mode='lines', name='5日均量',
        line=dict(color='rgba(255, 165, 0, 0.7)', width=1),
        hoverinfo='skip'
    ), row=2, col=1)

    # --- 5. 視覺與互動優化設定 (專業十字準星 + 即時數值) ---
    fig.update_layout(
        height=800,
        template="plotly_white",
        hovermode='x', # 💡 使用 'x' 模式讓數據標籤靠近手指
        dragmode='pan', 
        hoverdistance=100,
        spikedistance=1000,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            itemclick=False
        ),
        
        yaxis1=dict(
            title="價格",
            fixedrange=False,
            tickmode='linear',
            dtick=t_dtick,
            minor=dict(dtick=g_dtick, showgrid=True, gridcolor='rgba(235, 235, 235, 0.5)'),
            gridcolor='rgba(220, 220, 220, 0.8)',
            # 💡 水平導引線
            showspikes=True,
            spikemode='across',
            spikethickness=1,
            spikecolor='rgba(150, 150, 150, 0.5)',
            spikedash='dash'
        ),
        xaxis1=dict(
            showgrid=True, 
            fixedrange=False,
            gridcolor='rgba(235, 235, 235, 0.5)',
            # 💡 垂直導引線
            showspikes=True,
            spikemode='across+marker',
            spikesnap='cursor',
            spikethickness=1,
            spikecolor='rgba(150, 150, 150, 0.5)',
            spikedash='dash'
        ),
        yaxis2=dict(title="成交量", fixedrange=False)
    )

    # --- 6. 顯示圖表 (手機觸控優化) ---
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={
            'displayModeBar': False,  
            'scrollZoom': True,       # 💡 開啟捏合縮放感應
            'responsive': True,
            'doubleClick': 'reset',   
            'displaylogo': False
        }
    )

else:
    st.error(f"❌ 找不到股票代號 {input_id}")
