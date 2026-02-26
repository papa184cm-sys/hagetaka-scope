import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# === ⚙️ ページ設定 ===
st.set_page_config(
    page_title="源太AI・ハゲタカSCOPE",
    page_icon="🦅",
    layout="wide"
)

# === 🦅 サイドバー：源太流・相場カレンダー ===
st.sidebar.title("🦅 ハゲタカ戦略室")
st.sidebar.markdown("---")
st.sidebar.subheader("📅 2026年 戦略カレンダー")

# 現在月を取得して戦略を表示
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

@st.cache_data(ttl=3600) # 1時間キャッシュ
def get_jpx_tickers():
    # 本番用：1300〜9999のコードを生成（簡易版）
    # 実際はJPXリストを使うのがベストですが、エラー回避のため範囲生成
    # デモ動作を軽くするため、主要な銘柄コードリストを手動定義推奨
    # 今回はデモとして「動きのある有名銘柄 + ランダム」で構成
    # ※本番運用では全銘柄リストに差し替えます
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

def analyze_stock(ticker):
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
        
        if market_cap == 0: 
            market_cap = current_price * shares # 補正
        market_cap_oku = market_cap / 100000000

        # --- 🛡️ 足切りフィルター ---
        if current_price <= 300: return None
        if market_cap_oku < 100 or market_cap_oku > 5000: return None

        # --- 🛡️ 安全装置（2週間・20%ルール） ---
        recent_14_low = hist['Low'][-14:].min()
        deviation = (current_price - recent_14_low) / recent_14_low * 100
        if deviation > 20.0: return None # 高値掴み防止

        # --- 🔥 ハゲタカ検知 ---
        avg_vol_100 = hist['Volume'][-100:].mean()
        is_magma = current_vol > (avg_vol_100 * 1.5)
        
        turnover = 0
        if shares > 0:
            turnover = (current_vol / shares) * 100

        # --- 💎 プラチナ判定 ---
        is_platinum = 500 <= market_cap_oku <= 2000

        # --- 🚨 アラート（ニュース） ---
        alert_msg = ""
        # ニュース取得はAPI制限があるため、デモでは回転率で擬似判定
        if turnover > 5.0: alert_msg = "🟡活況(好材料?)"
        if deviation > 15.0: alert_msg = "🔴過熱警戒"

        # --- 👑 ランク付け ---
        rank = "D" # 通常
        rank_score = 0
        
        if is_platinum: rank_score += 3
        if is_magma: rank_score += 4
        if 1.0 <= turnover <= 5.0: rank_score += 2 # 程よい活況
        
        # 煮詰まり判定（ボリンジャーバンド幅が狭い）
        bb_std = hist['Close'][-20:].std()
        bb_mean = hist['Close'][-20:].mean()
        if bb_mean > 0 and (bb_std / bb_mean) < 0.05: # 変動率5%未満
             rank_score += 2 # 煮詰まりボーナス

        # 総合判定
        if rank_score >= 7 and is_platinum: rank = "S"
        elif rank_score >= 5: rank = "A"
        elif is_platinum: rank = "B"
        elif turnover >= 3.0: rank = "C"

        return {
            "コード": ticker.replace(".T", ""),
            "銘柄名": info.get('longName', ticker),
            "現在値": int(current_price),
            "時価総額": f"{int(market_cap_oku)}億",
            "ランク": rank,
            "プラチナ": is_platinum,
            "ハゲタカ": is_magma,
            "回転率": turnover,
            "乖離率": deviation,
            "アラート": alert_msg,
            "ヒストリ": hist # チャート用
        }
    except:
        return None

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")
st.caption("Pro Version: 2026.02 | Target: VIP Members")

# ボタンでスキャン開始
if st.button("🔍 市場スキャン開始（ハゲタカ検知）"):
    with st.spinner('🦅 ハゲタカAIが全市場をパトロール中...'):
        tickers = get_jpx_tickers()
        results = []
        progress_bar = st.progress(0)
        
        for i, t in enumerate(tickers):
            data = analyze_stock(t)
            if data:
                results.append(data)
            progress_bar.progress((i + 1) / len(tickers))
        
        st.success(f"スキャン完了！ {len(results)} 銘柄を抽出しました。")

        # データフレーム化
        if results:
            df = pd.DataFrame(results)
            
            # Sランクなどの並び替え
            rank_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
            df['score'] = df['ランク'].map(rank_map)
            df = df.sort_values(by=['score', '回転率'], ascending=[False, False])

            # --- 結果表示 ---
            for index, row in df.iterrows():
                # デザイン整形
                rank_color = "red" if row['ランク'] == "S" else "orange" if row['ランク'] == "A" else "blue"
                
                # アイコン
                icons = ""
                if row['プラチナ']: icons += "💎 "
                if row['ハゲタカ']: icons += "🦅 "
                
                with st.expander(f"【{row['ランク']}】 {icons} {row['コード']} {row['銘柄名']} | {row['現在値']}円"):
                    
                    # 3カラムレイアウト
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("時価総額", row['時価総額'])
                        st.metric("回転率", f"{row['回転率']:.2f}%")
                    
                    with col2:
                        st.metric("底値乖離率", f"+{row['乖離率']:.1f}%")
                        if row['アラート']:
                            st.warning(row['アラート'])
                        else:
                            st.success("✅ 安全圏内")
                            
                    with col3:
                        # AIコメント生成
                        comment = ""
                        if row['ランク'] == "S":
                            comment = "🔥 **【激アツ】** プラチナ銘柄に「ハゲタカ参戦？」の痕跡あり！底値圏で煮詰まっており、初動の可能性大。"
                        elif row['ランク'] == "A":
                            comment = "📈 **【有望】** 出来高急増（ハゲタカ参戦？）を検知。資金流入が確認できます。"
                        elif row['ランク'] == "B":
                            comment = "👀 **【監視】** プラチナ級のサイズ感。まだ動きは静かですが、仕込み時を探るフェーズ。"
                        else:
                            comment = "市場の動きに合わせて監視継続。"
                        st.markdown(comment)

                    # --- チャート表示（Plotly） ---
                    hist_data = row['ヒストリ']
                    
                    # 需給の壁（価格帯別出来高）計算
                    price_bins = pd.cut(hist_data['Close'], bins=10)
                    vol_profile = hist_data.groupby(price_bins)['Volume'].sum()
                    max_vol_price = vol_profile.idxmax().mid # 最も出来高が多い価格帯
                    
                    # チャート描画
                    fig = go.Figure()
                    
                    # ローソク足
                    fig.add_trace(go.Candlestick(
                        x=hist_data.index,
                        open=hist_data['Open'], high=hist_data['High'],
                        low=hist_data['Low'], close=hist_data['Close'],
                        name="株価"
                    ))
                    
                    # 需給の壁ライン
                    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", annotation_text="🚧 需給の壁（抵抗線）")
                    
                    fig.update_layout(
                        title=f"{row['銘柄名']} 日足チャート (需給の壁チェック)",
                        xaxis_rangeslider_visible=False,
                        height=300,
                        margin=dict(l=0, r=0, t=30, b=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("該当銘柄なし。条件を緩めて再スキャンしてください。")
