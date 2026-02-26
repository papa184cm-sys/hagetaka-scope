import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === ⚙️ ページ設定 ===
st.set_page_config(
    page_title="源太AI・ハゲタカscope",
    page_icon="🦅",
    layout="wide"
)

# === 🦅 サイドバー：源太流・相場カレンダー ===
st.sidebar.title("🦅 ハゲタカ戦略室")
st.sidebar.markdown("---")
st.sidebar.subheader("📅 2026年 戦略カレンダー")

current_month = datetime.now().month
strategy_text = {
    1: "⚠️ **1月：資金温存**\n外国人買いが入りますが、3月の暴落に備えて現金比率を高めましょう。",
    2: "⚠️ **2月：様子見**\n無理に動く時期ではありません。監視銘柄の選定に集中。",
    3: "📉 **3月：換金売り警戒＆仕込み**\n中旬の暴落は「優良株」を拾う最大のチャンス！",
    4: "🔥 **4月：ニューマネー流入**\n新年度予算で中小型株が吹き上がります。3月の仕込みを利益に。",
    5: "🔥 **5月：セルインメイは嘘**\n決算後の「材料出尽くし」急落は、ハゲタカの集め場です。",
    6: "💰 **6月：ボーナス・配当再投資**\n資金潤沢。大型株へシフトする時期。",
    7: "💰 **7月：サマーラリー**\n夏枯れ前の最後のひと稼ぎ。",
    8: "🌊 **8月：夏枯れ・真空地帯**\nハゲタカ不在。AIによるフラッシュクラッシュ（急落）のみ警戒。",
    9: "📉 **9月：彼岸底**\n10月の大底に向けた調整。",
    10: "🔥 **10月：年内最後の大底**\nここから年末ラリーへ。全力買いの急所。",
    11: "🍂 **11月：節税売り（タックスロス）**\n投げ売りされた銘柄を拾う。",
    12: "🎉 **12月：掉尾の一振**\n年末ラリーで全てを利益に変えて逃げ切る。"
}
st.sidebar.info(strategy_text.get(current_month, "戦略待機中"))

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🦅 記号の解説
* **💎 プラチナ (Platinum)**
    * 時価総額 **500億～2000億円**
    * ハゲタカが最も仕掛けやすい黄金サイズ。
* **🦅 ハゲタカ参戦？**
    * 出来高急増＋株価ヨコヨコ
    * 水面下での「仕込み」疑惑あり。
* **回転率**
    * 全株式の何%が売買されたか。
    * **3%以上**で活況、**10%以上**は過熱。
""")

# === 🛠️ 関数定義 ===

@st.cache_data(ttl=3600)
def get_jpx_tickers():
    # デモ用リスト（本番時は全銘柄リストを使用）
    demo_tickers = [
        "7203.T", "9984.T", "215A.T", "5032.T", "1514.T", "1605.T", 
        "8306.T", "6758.T", "7011.T", "9101.T", "6098.T", "4385.T",
        "1357.T", "1570.T", "9501.T", "7201.T", "8035.T", "6857.T",
        "4502.T", "4568.T", "2914.T", "3382.T", "4063.T", "6367.T",
        "6501.T", "6701.T", "6702.T", "6723.T", "6752.T", "6762.T",
        "6861.T", "6902.T", "6954.T", "6971.T", "6981.T", "7267.T",
        "7741.T", "7974.T", "8001.T", "8002.T", "8031.T", "8053.T",
        "8058.T", "8316.T", "8411.T", "8766.T", "8801.T", "8802.T",
        "9020.T", "9021.T", "9022.T", "9202.T", "9432.T", "9433.T",
        "9434.T", "9983.T"
    ]
    return demo_tickers

def analyze_stock(ticker, mode="scan"):
    """
    mode="scan": 条件不一致ならNoneを返す（リスト用）
    mode="search": 条件不一致でも詳細データを返す（個別診断用）
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        if len(hist) < 30: return None

        # データ取得
        current_price = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        info = stock.info
        market_cap = info.get('marketCap', 0)
        shares = info.get('sharesOutstanding', 0)
        long_name = info.get('longName', ticker)
        
        if market_cap == 0: 
            market_cap = current_price * shares 
        market_cap_oku = market_cap / 100000000

        # --- 判定ロジック ---
        
        # 1. 価格フィルター
        is_price_ok = current_price > 300
        
        # 2. 時価総額フィルター（プラチナ or ターゲット圏内）
        is_platinum = 500 <= market_cap_oku <= 2000
        is_cap_ok = 100 <= market_cap_oku <= 5000
        
        # 3. 安全装置（乖離率）
        recent_14_low = hist['Low'][-14:].min()
        deviation = (current_price - recent_14_low) / recent_14_low * 100
        is_safe = deviation <= 20.0
        
        # 4. ハゲタカ検知（マグマ）
        avg_vol_100 = hist['Volume'][-100:].mean()
        is_magma = current_vol > (avg_vol_100 * 1.5)
        
        # 5. 回転率
        turnover = 0
        if shares > 0:
            turnover = (current_vol / shares) * 100
        
        # ランク付け
        rank = "E" # 対象外
        rank_score = 0
        
        if is_cap_ok and is_price_ok and is_safe:
            rank = "D" # 候補
            if is_platinum: rank_score += 3
            if is_magma: rank_score += 4
            if 1.0 <= turnover <= 5.0: rank_score += 2
            
            # 煮詰まりボーナス
            bb_std = hist['Close'][-20:].std()
            bb_mean = hist['Close'][-20:].mean()
            if bb_mean > 0 and (bb_std / bb_mean) < 0.05:
                 rank_score += 2

            if rank_score >= 7 and is_platinum: rank = "S"
            elif rank_score >= 5: rank = "A"
            elif is_platinum: rank = "B"
            elif turnover >= 3.0: rank = "C"
        
        # スキャンモードなら、ランク外は弾く
        if mode == "scan" and rank == "E":
            return None

        # データ返却
        return {
            "コード": ticker.replace(".T", ""),
            "銘柄名": long_name,
            "現在値": int(current_price),
            "時価総額": market_cap_oku,
            "ランク": rank,
            "プラチナ": is_platinum,
            "ハゲタカ": is_magma,
            "回転率": turnover,
            "乖離率": deviation,
            "ヒストリ": hist,
            # 詳細診断用フラグ
            "check_price": is_price_ok,
            "check_cap": is_cap_ok,
            "check_safe": is_safe,
            "check_magma": is_magma
        }
    except:
        return None

def draw_chart(row):
    hist_data = row['ヒストリ']
    price_bins = pd.cut(hist_data['Close'], bins=10)
    vol_profile = hist_data.groupby(price_bins)['Volume'].sum()
    max_vol_price = vol_profile.idxmax().mid
    
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'], high=hist_data['High'],
        low=hist_data['Low'], close=hist_data['Close'],
        name="株価"
    ))
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", annotation_text="🚧 需給の壁")
    fig.update_layout(title=f"{row['銘柄名']} 日足", xaxis_rangeslider_visible=False, height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")
st.caption("Pro Version: 2026.02 | Target: VIP Members")

# タブの作成
tab1, tab2 = st.tabs(["🔍 個別銘柄診断", "🦅 全市場スキャン"])

# --- タブ1: 個別診断 ---
with tab1:
    st.markdown("##### 気になる銘柄を精密検査します")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        input_code = st.text_input("銘柄コードを入力 (例: 7203, 9984)", max_chars=4)
    with col_btn:
        st.write("") # スペース調整
        st.write("") 
        search_btn = st.button("診断する", type="primary")

    if search_btn and input_code:
        with st.spinner('🦅 ハゲタカAIが診断中...'):
            ticker_code = f"{input_code}.T"
            data = analyze_stock(ticker_code, mode="search")
            
            if data:
                # 結果表示
                st.markdown("---")
                # ヘッダー
                rank_color = "red" if data['ランク'] == "S" else "orange" if data['ランク'] == "A" else "blue"
                if data['ランク'] == "E": rank_color = "gray"
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("判定ランク", f"ランク {data['ランク']}")
                    if data['プラチナ']: st.success("💎 プラチナ・チケット認定")
                    if data['ハゲタカ']: st.error("🦅 ハゲタカ参戦？ (仕込み疑惑)")
                
                with c2:
                    st.subheader(f"{data['コード']} {data['銘柄名']}")
                    st.markdown(f"**現在値:** {data['現在値']}円 | **時価総額:** {int(data['時価総額'])}億円")

                # 診断カルテ（チェックリスト）
                st.markdown("##### 📋 AI診断カルテ")
                
                # 1. ボロ株チェック
                if data['check_price']: st.success("✅ **株価水準:** 合格 (300円以上)")
                else: st.error("❌ **株価水準:** 不合格 (300円以下のボロ株は対象外)")
                
                # 2. 時価総額チェック
                if data['プラチナ']: st.success(f"✅ **サイズ感:** 💎 完璧 (プラチナレンジ {int(data['時価総額'])}億)")
                elif data['check_cap']: st.info(f"✅ **サイズ感:** 合格 (ターゲット圏内 {int(data['時価総額'])}億)")
                else: st.error(f"❌ **サイズ感:** 不合格 (重すぎるか軽すぎる {int(data['時価総額'])}億)")
                
                # 3. 安全性チェック
                if data['check_safe']: st.success(f"✅ **安全性:** 合格 (底値乖離 {data['乖離率']:.1f}%)")
                else: st.error(f"❌ **安全性:** 危険 (高値圏 {data['乖離率']:.1f}% - 飛びつき注意)")
                
                # 4. マグマチェック
                if data['ハゲタカ']: st.success("✅ **資金流入:** 🔥 マグマ発生中 (出来高急増)")
                else: st.info("ℹ️ **資金流入:** 静観 (目立った動きなし)")

                # チャート
                draw_chart(data)
                
            else:
                st.error("銘柄が見つかりません。コードを確認してください。")

# --- タブ2: 全市場スキャン ---
with tab2:
    st.markdown("##### ハゲタカが潜む銘柄を自動抽出します")
    if st.button("🚀 スキャン開始", key="scan_btn"):
        with st.spinner('🦅 全市場をパトロール中...'):
            tickers = get_jpx_tickers()
            results = []
            progress_bar = st.progress(0)
            
            for i, t in enumerate(tickers):
                data = analyze_stock(t, mode="scan")
                if data:
                    results.append(data)
                progress_bar.progress((i + 1) / len(tickers))
            
            st.success(f"スキャン完了！ {len(results)} 銘柄を抽出しました。")

            if results:
                df = pd.DataFrame(results)
                rank_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
                df['score'] = df['ランク'].map(rank_map)
                df = df.sort_values(by=['score', '回転率'], ascending=[False, False])

                for index, row in df.iterrows():
                    icons = ""
                    if row['プラチナ']: icons += "💎 "
                    if row['ハゲタカ']: icons += "🦅 "
                    
                    with st.expander(f"【{row['ランク']}】 {icons} {row['コード']} {row['銘柄名']} | {row['現在値']}円"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("時価総額", f"{int(row['時価総額'])}億")
                            st.metric("回転率", f"{row['回転率']:.2f}%")
                        with col2:
                            st.metric("底値乖離率", f"+{row['乖離率']:.1f}%")
                        with col3:
                            comment = ""
                            if row['ランク'] == "S": comment = "🔥 **【激アツ】** プラチナ×ハゲタカ参戦！"
                            elif row['ランク'] == "A": comment = "📈 **【有望】** 資金流入を検知。"
                            elif row['ランク'] == "B": comment = "👀 **【監視】** 仕込み時を探るフェーズ。"
                            st.markdown(comment)
                        
                        draw_chart(row)
            else:
                st.warning("該当なし。")
