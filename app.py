import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import unicodedata

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

@st.cache_data(ttl=86400) # 1日キャッシュ
def get_jpx_data():
    """JPXから銘柄リストを取得し、コードと日本語名の辞書を作る"""
    try:
        url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
        df = pd.read_excel(url)
        # 形式に合わせて整形（コード、銘柄名、市場区分などを抽出）
        # データ構造が変わる可能性があるため、カラム名ではなく位置で取得などを検討
        # 通常：コード(column 1), 銘柄名(column 2)
        df_tickers = df[df.iloc[:, 3].isin(['プライム', 'スタンダード', 'グロース'])]
        name_map = dict(zip(df_tickers.iloc[:, 1].astype(str), df_tickers.iloc[:, 2]))
        return name_map, list(name_map.keys())
    except:
        return {}, []

# JPXデータ読み込み（初回のみ実行）
jpx_names, jpx_codes = get_jpx_data()

def normalize_input(input_text):
    """入力された文字列（全角、カンマ区切りなど）をリスト化する"""
    if not input_text: return []
    # 全角を半角に
    text = unicodedata.normalize('NFKC', input_text)
    # 区切り文字を統一
    text = text.replace(',', ' ').replace('、', ' ').replace('\n', ' ')
    # 分割して空白削除
    codes = [c.strip() for c in text.split(' ') if c.strip()]
    # 重複削除
    return list(set(codes))

def evaluate_stock(ticker):
    """銘柄の詳細診断を行う"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        if len(hist) < 30: return None

        # データ取得
        current_price = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        avg_vol_100 = hist['Volume'][-100:].mean()
        info = stock.info
        
        market_cap = info.get('marketCap', 0)
        shares = info.get('sharesOutstanding', 0)
        
        if market_cap == 0: market_cap = current_price * shares
        market_cap_oku = market_cap / 100000000

        # 日本語名取得
        code_only = ticker.replace(".T", "")
        jp_name = jpx_names.get(code_only, info.get('longName', ticker))

        # --- 🔍 1. 株価水準 (Value Score) ---
        # 300円以上かどうかのチェックは内部で行うが、表示はランクで。
        # 簡易的な割安度判定 (PBR/PERがあれば使う)
        pbr = info.get('priceToBook', 0)
        per = info.get('trailingPE', 0)
        
        value_rank = "C" # 標準
        value_comment = "適正水準"
        
        if current_price <= 300:
            value_rank = "E"
            value_comment = "ボロ株圏内（対象外）"
        elif pbr > 0 and pbr < 1.0:
            value_rank = "S"
            value_comment = "超割安（お宝水準）"
        elif pbr > 0 and pbr < 1.5:
            value_rank = "A"
            value_comment = "割安圏"
        elif per > 30 or pbr > 5:
            value_rank = "D"
            value_comment = "やや割高感あり"
        else:
            value_rank = "B"
            value_comment = "標準的"

        # --- 🔍 2. サイズ感 (Market Cap) ---
        size_rank = "良好"
        size_comment = "合格"
        is_platinum = False
        
        if market_cap_oku < 50:
            size_rank = "小さすぎる"
            size_comment = "板が薄く危険"
        elif market_cap_oku < 100:
            size_rank = "やや小さい"
            size_comment = "流動性注意"
        elif market_cap_oku <= 500:
            size_rank = "良好"
            size_comment = "合格圏内"
        elif market_cap_oku <= 2000:
            size_rank = "💎 プラチナ"
            size_comment = "ハゲタカの好物"
            is_platinum = True
        elif market_cap_oku <= 5000:
            size_rank = "やや大きい"
            size_comment = "動きが重い可能性"
        elif market_cap_oku <= 10000: # 1兆
            size_rank = "大きい"
            size_comment = "機関投資家の主戦場"
        else:
            size_rank = "特大"
            size_comment = "国策・インデックス級"

        # --- 🔍 3. 安全性 (Deviation) ---
        recent_14_low = hist['Low'][-14:].min()
        deviation = (current_price - recent_14_low) / recent_14_low * 100
        
        safe_rank = "見送り"
        safe_class = "danger" # error color
        
        if deviation <= 5.0:
            safe_rank = "絶好"
            safe_class = "success"
        elif deviation <= 10.0:
            safe_rank = "良好"
            safe_class = "success"
        elif deviation <= 15.0:
            safe_rank = "短期なら"
            safe_class = "warning" # yellow
        elif deviation <= 20.0:
            safe_rank = "及第点"
            safe_class = "warning"
        elif deviation <= 30.0:
            safe_rank = "見送り（上値意識）"
            safe_class = "error"
        else:
            safe_rank = "手出し無用（過熱）"
            safe_class = "error"

        # --- 🔍 4. 資金流入 (Inflow / Magma) ---
        vol_ratio = 0
        if avg_vol_100 > 0:
            vol_ratio = current_vol / avg_vol_100
        
        inflow_rank = "皆無に近い"
        inflow_class = "info" # blue
        is_magma = False
        
        if vol_ratio > 3.0:
            inflow_rank = "🦅 ハゲタカ察知！"
            inflow_class = "success"
            is_magma = True
        elif vol_ratio > 2.0:
            inflow_rank = "ハゲタカ気配あり"
            inflow_class = "success"
            is_magma = True
        elif vol_ratio > 1.5:
            inflow_rank = "流入予兆"
            inflow_class = "warning"
        elif vol_ratio > 1.2:
            inflow_rank = "やや流入観測"
            inflow_class = "info"

        # --- 総合ランク判定 ---
        total_rank = "D"
        # スコアリング
        score = 0
        if is_platinum: score += 3
        if is_magma: score += 3
        if deviation <= 20: score += 2
        if value_rank in ["S", "A", "B"]: score += 1
        
        if score >= 8: total_rank = "S"
        elif score >= 6: total_rank = "A"
        elif score >= 4: total_rank = "B"
        elif deviation > 20: total_rank = "注意"
        else: total_rank = "C"

        if current_price <= 300: total_rank = "E"

        return {
            "コード": code_only,
            "銘柄名": jp_name,
            "現在値": int(current_price),
            "時価総額": market_cap_oku,
            "ランク": total_rank,
            "プラチナ": is_platinum,
            "ハゲタカ": is_magma,
            "乖離率": deviation,
            "ヒストリ": hist,
            # 詳細評価用
            "value_rank": value_rank,
            "value_comment": value_comment,
            "size_rank": size_rank,
            "size_comment": size_comment,
            "safe_rank": safe_rank,
            "safe_class": safe_class,
            "inflow_rank": inflow_rank,
            "inflow_class": inflow_class
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
tab1, tab2 = st.tabs(["🔍 複数銘柄一括診断", "🦅 全市場スキャン"])

# --- タブ1: 個別診断 ---
with tab1:
    st.markdown("##### 気になる銘柄を入力（スペース区切りで複数可）")
    st.markdown("例: `7011 7203` `9984, 8306`")
    
    with st.form(key='search_form'):
        input_code = st.text_area("銘柄コード", height=68)
        search_btn = st.form_submit_button("🦅 ハゲタカAIで診断する")

    if search_btn and input_code:
        codes = normalize_input(input_code)
        
        if not codes:
            st.error("銘柄コードを入力してください")
        else:
            with st.spinner(f'🦅 {len(codes)}銘柄を精密検査中...'):
                for code in codes:
                    # 数値かチェック
                    if not code.isdigit(): continue
                    
                    ticker_code = f"{code}.T"
                    data = evaluate_stock(ticker_code)
                    
                    if data:
                        # === カード表示 ===
                        with st.expander(f"{data['ランク']}ランク | {data['コード']} {data['銘柄名']}", expanded=True):
                            
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                # ランクバッジ表示
                                rank_color = "red" if data['ランク'] == "S" else "orange" if data['ランク'] == "A" else "blue"
                                st.markdown(f"<h2 style='color:{rank_color};'>ランク {data['ランク']}</h2>", unsafe_allow_html=True)
                                st.write(f"現在値: **{data['現在値']}** 円")
                                st.write(f"時価総額: **{int(data['時価総額'])}** 億円")
                                
                            with c2:
                                # === 📋 診断カルテ ===
                                st.markdown("##### 📋 AI診断カルテ")
                                
                                # 1. 株価水準
                                st.info(f"💰 **株価水準:** {data['value_rank']}ランク ({data['value_comment']})")
                                
                                # 2. サイズ感
                                if data['プラチナ']:
                                    st.success(f"📏 **サイズ感:** {data['size_rank']} ({data['size_comment']})")
                                elif "特大" in data['size_rank'] or "小さい" in data['size_rank']:
                                    st.error(f"📏 **サイズ感:** {data['size_rank']} ({data['size_comment']})")
                                else:
                                    st.info(f"📏 **サイズ感:** {data['size_rank']} ({data['size_comment']})")
                                
                                # 3. 安全性
                                msg_safe = f"🛡️ **安全性:** {data['safe_rank']} (底値乖離 {data['乖離率']:.1f}%)"
                                if data['safe_class'] == "success": st.success(msg_safe)
                                elif data['safe_class'] == "warning": st.warning(msg_safe)
                                else: st.error(msg_safe)
                                
                                # 4. 資金流入
                                msg_inflow = f"🔥 **資金流入:** {data['inflow_rank']}"
                                if data['inflow_class'] == "success": st.success(msg_inflow)
                                elif data['inflow_class'] == "warning": st.warning(msg_inflow)
                                else: st.info(msg_inflow)

                            # チャート
                            draw_chart(data)
                    else:
                        st.error(f"❌ {code}: データ取得エラー（上場廃止などの可能性）")

# --- タブ2: 全市場スキャン ---
with tab2:
    st.markdown("##### ハゲタカが潜む銘柄を自動抽出します")
    if st.button("🚀 スキャン開始", key="scan_btn"):
        st.info("※デモ動作中：市場の主要銘柄から抽出します（全銘柄実装はサーバー負荷のため調整中）")
        
        # デモ用リスト（実際はここを全銘柄ループにする）
        demo_codes = ["7203", "9984", "215A", "5032", "1514", "1605", "8306", "7011", "9101", "1787"]
        # + ランダムで少し混ぜるなど
        
        results = []
        progress_bar = st.progress(0)
        
        for i, code in enumerate(demo_codes):
            data = evaluate_stock(f"{code}.T")
            if data and data['ランク'] != "E": # Eランク以外を表示
                results.append(data)
            progress_bar.progress((i + 1) / len(demo_codes))
        
        if results:
            df = pd.DataFrame(results)
            # Sランク優先
            rank_map = {"S": 5, "A": 4, "B": 3, "注意": 2, "C": 1}
            df['score'] = df['ランク'].map(rank_map)
            df = df.sort_values(by=['score'], ascending=False)

            for index, row in df.iterrows():
                with st.expander(f"【{row['ランク']}】 {row['コード']} {row['銘柄名']} | {row['現在値']}円"):
                    st.write(f"時価総額: {int(row['時価総額'])}億")
                    st.write(f"乖離率: {row['乖離率']:.1f}%")
                    comment = "監視継続"
                    if row['ランク']=="S": comment = "🔥 激アツ！プラチナ×マグマ"
                    st.markdown(comment)
                    draw_chart(row)
        else:
            st.warning("該当なし")
