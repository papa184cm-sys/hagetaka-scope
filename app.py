import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import unicodedata
import requests
import io

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
* **🧬 DNA（習性）**
    * 過去に短期間で急騰した実績あり。
""")

# === 🛠️ 関数定義 ===

@st.cache_data(ttl=86400)
def get_jpx_data():
    try:
        url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        df = pd.read_excel(io.BytesIO(response.content))
        df_tickers = df[df.iloc[:, 3].isin(['プライム', 'スタンダード', 'グロース'])]
        name_map = dict(zip(df_tickers.iloc[:, 1].astype(str), df_tickers.iloc[:, 2]))
        return name_map, list(name_map.keys())
    except Exception:
        return {}, []

jpx_names, jpx_codes = get_jpx_data()

def normalize_input(input_text):
    if not input_text: return []
    text = unicodedata.normalize('NFKC', input_text)
    text = text.replace(',', ' ').replace('、', ' ').replace('\n', ' ')
    codes = [c.strip() for c in text.split(' ') if c.strip()]
    return list(set(codes))

def check_dna(hist):
    try:
        window = 60
        if len(hist) < window: return False
        pct_change = hist['Close'].pct_change(periods=60)
        max_spike = pct_change.max()
        return max_spike >= 0.8
    except:
        return False

def evaluate_stock(ticker, mode="scan"):
    try:
        stock = yf.Ticker(ticker)

        # --- 第一段階: 高速足切り ---
        if mode == "scan":
            try:
                fast = stock.fast_info
                last_price = getattr(fast, 'last_price', None)
                if last_price and last_price <= 300: return None
                mcap = getattr(fast, 'market_cap', None)
                if mcap:
                    mcap_oku = mcap / 100000000
                    if mcap_oku < 50 or mcap_oku > 10000: return None
            except:
                pass

        # --- 第二段階: 精密検査 ---
        hist = stock.history(period="2y")
        if len(hist) < 30: return None

        current_price = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        avg_vol_100 = hist['Volume'][-100:].mean()
        info = stock.info
        
        market_cap = info.get('marketCap', 0)
        shares = info.get('sharesOutstanding', 0)
        if market_cap == 0: market_cap = current_price * shares
        market_cap_oku = market_cap / 100000000

        code_only = ticker.replace(".T", "")
        jp_name = jpx_names.get(code_only, info.get('longName', ticker))

        if current_price <= 300 and mode == "scan": return None

        # --- 時価総額によるカテゴリ分け（AI解説出し分け用） ---
        if market_cap_oku >= 5000:
            cap_category = "large"
            intervention_name = "🏢 機関投資家・大口流入度"
        elif market_cap_oku >= 50:
            cap_category = "target"
            intervention_name = "🦅 ハゲタカ介入度"
        else:
            cap_category = "small"
            intervention_name = "⚠️ イナゴマネー過熱度 (超小型)"

        # --- ① 需給の壁（岩盤）の算出 ---
        hist_6mo = hist.tail(125)
        price_bins = pd.cut(hist_6mo['Close'], bins=15)
        vol_profile = hist_6mo.groupby(price_bins, observed=False)['Volume'].sum()
        max_vol_price = vol_profile.idxmax().mid

        # --- ② お得度（上昇余地）の星評価ロジック ---
        upside_potential = 0
        is_blue_sky = False
        
        if current_price >= max_vol_price:
            is_blue_sky = True
        else:
            upside_potential = ((max_vol_price - current_price) / current_price) * 100

        star_rating = ""
        star_desc = ""
        base_logic = ""
        
        if is_blue_sky:
            star_rating = "★★★★★"
            star_desc = "青天井モード（上値抵抗なし！）"
            base_logic = "上値に目立った需給の壁（抵抗線）がありません。売り手が不在の真空地帯（青空）に突入しています。"
        elif upside_potential >= 30:
            star_rating = "★★★★☆"
            star_desc = f"激アツ（ターゲットまで +{upside_potential:.1f}%）"
            base_logic = f"最も分厚い需給の壁（{int(max_vol_price)}円付近）まで大きな「のり代」があります。"
        elif upside_potential >= 15:
            star_rating = "★★★☆☆"
            star_desc = f"有望（次の壁まで +{upside_potential:.1f}%）"
            base_logic = f"次の抵抗線（{int(max_vol_price)}円付近）まで堅実な上昇が見込める水準です。"
        elif upside_potential >= 5:
            star_rating = "★★☆☆☆"
            star_desc = f"普通（次の壁まで +{upside_potential:.1f}%）"
            base_logic = f"すぐ上に需給の壁（{int(max_vol_price)}円付近）が迫っています。突破できるかの激戦区です。"
        else:
            star_rating = "★☆☆☆☆"
            star_desc = f"頭打ち警戒（すぐ上に分厚い壁あり）"
            base_logic = f"現在値のすぐ上（{int(max_vol_price)}円付近）に強烈な「しこり玉（含み損勢）」が大量に待機しています。"

        # 時価総額に応じた解説のフレーバー追加
        flavor_logic = ""
        if cap_category == "large":
            flavor_logic = "時価総額が巨大なため『仕手筋の急騰仕掛け』は入りませんが、機関投資家や外国人投資家の資金流入をエンジンとした、強力で重厚なトレンドが期待できます。"
        elif cap_category == "target":
            flavor_logic = "ハゲタカが最も好む規模感であり、彼らが資金を投下すれば一気に株価が吹き飛ぶ（または壁を突破する）ポテンシャルを秘めています。"
        else:
            flavor_logic = "※ただし時価総額が小さすぎるため、プロは資金を入れづらい銘柄です。主に個人マネーによる『マネーゲーム（乱高下）』になりやすいため、ロットを落とした短期勝負に限定してください。"

        star_logic = base_logic + " " + flavor_logic

        # --- 各種指標 ---
        past_1y = hist[-250:]
        year_high = past_1y['High'].max()
        year_low = past_1y['Low'].min()
        position_score = 0.5
        if year_high != year_low:
            position_score = (current_price - year_low) / (year_high - year_low)
            
        has_dna = check_dna(hist)
        vol_ratio = current_vol / avg_vol_100 if avg_vol_100 > 0 else 0
        is_platinum = 500 <= market_cap_oku <= 2000

        # --- ③ 介入度（%）の計算と10%刻み化 ---
        intervention_score = 0
        
        if is_platinum: intervention_score += 35
        elif 100 <= market_cap_oku <= 5000: intervention_score += 15
        
        if vol_ratio >= 3.0: intervention_score += 40
        elif vol_ratio >= 1.5: intervention_score += 25
        
        if position_score <= 0.2: intervention_score += 15
        if has_dna: intervention_score += 10
        
        intervention_score = min(intervention_score, 100)
        intervention_score = int(round(intervention_score / 10.0)) * 10
        
        intervention_comment = ""
        if intervention_score >= 80:
            if cap_category == "large": intervention_comment = "🚨 【極めて濃厚】機関投資家の本格的な資金流入シグナルが点灯！"
            else: intervention_comment = "🚨 【極めて濃厚】大口（ハゲタカ）の介入シグナルが多数点灯！"
        elif intervention_score >= 50:
            intervention_comment = "👀 【予兆あり】水面下で玉（ぎょく）が集められている可能性があります。"
        else:
            intervention_comment = "💤 【静観】現在は目立った大口の動きは検出されません。"

        # --- 安全性 ---
        recent_14_low = hist['Low'][-14:].min()
        deviation = (current_price - recent_14_low) / recent_14_low * 100

        # --- 総合ランク ---
        total_rank = "D"
        if intervention_score >= 80 and (is_blue_sky or upside_potential >= 30): total_rank = "S"
        elif intervention_score >= 60: total_rank = "A"
        elif is_platinum and position_score <= 0.3: total_rank = "B"
        elif deviation > 20: total_rank = "注意"
        else: total_rank = "C"

        if current_price <= 300: total_rank = "E"
        if mode == "scan" and total_rank in ["E", "D", "注意"]: return None

        return {
            "コード": code_only,
            "銘柄名": jp_name,
            "現在値": int(current_price),
            "時価総額": market_cap_oku,
            "ランク": total_rank,
            "乖離率": deviation,
            "ヒストリ": hist,
            "max_vol_price": max_vol_price,
            "star_rating": star_rating,
            "star_desc": star_desc,
            "star_logic": star_logic,
            "intervention_name": intervention_name,
            "intervention_score": intervention_score,
            "intervention_comment": intervention_comment
        }
    except:
        return None

def draw_chart(row):
    hist_data = row['ヒストリ'].tail(150)
    max_vol_price = row['max_vol_price']
    
    # 価格帯別出来高の計算
    bins = 15
    hist_data_copy = hist_data.copy()
    hist_data_copy['price_bins'] = pd.cut(hist_data_copy['Close'], bins=bins)
    vol_profile = hist_data_copy.groupby('price_bins', observed=False)['Volume'].sum()
    bin_centers = [b.mid for b in vol_profile.index]
    bin_volumes = vol_profile.values
    
    # 2画面分割（左：ローソク足、右：価格帯別出来高）
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0)
    
    # 左：ローソク足チャート
    fig.add_trace(go.Candlestick(
        x=hist_data.index,
        open=hist_data['Open'], high=hist_data['High'],
        low=hist_data['Low'], close=hist_data['Close'],
        name="株価",
        showlegend=False
    ), row=1, col=1)
    
    # 右：価格帯別出来高（横棒グラフ）
    fig.add_trace(go.Bar(
        x=bin_volumes,
        y=bin_centers,
        orientation='h',
        marker_color='rgba(255, 165, 0, 0.6)',
        name="出来高ボリューム",
        showlegend=False,
        hoverinfo='y'
    ), row=1, col=2)
    
    # 需給の壁（両方のチャートを貫通する線）
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", annotation_text="🚧 需給の壁", row=1, col=1)
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", row=1, col=2)

    fig.update_layout(
        title=f"{row['銘柄名']} 日足 ＆ 価格帯別出来高",
        xaxis_rangeslider_visible=False,
        height=350,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    # 右側のX軸ラベルを消してスッキリさせる
    fig.update_xaxes(showticklabels=False, row=1, col=2)
    
    st.plotly_chart(fig, use_container_width=True)

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")
st.caption("Pro Version: 2026.02 | Target: VIP Members")

# --- 🔰 トリセツ（使い方ガイド） ---
with st.expander("🔰 【源太AI・各項目の見方と算出ロジック】 ※初めての方はお読みください"):
    st.markdown("""
    当ツールは、表向きのニュースや決算に騙されず、市場の裏側で暗躍する大口投資家（ハゲタカ）の『資金の足跡』を追跡するシステムです。
    
    #### ① 🦅 介入度（％メーター）
    **「今、大口投資家がこの株を狙っている可能性」**を示します。以下の厳格な物理法則に基づきAIが算出しています。
    * **規模的優位性:** ハゲタカが好む「プラチナチケット（500億〜2000億円）」に該当しているか。
    * **異常出来高の検知:** 個人投資家では作れない不自然な大商い（資金流入の痕跡）があるか。
    * **位置エネルギー:** 過去1年の最安値圏で株価が煮詰まっており、上に跳ねるエネルギーが充填されているか。
    * **仕手化のDNA:** 過去に短期間で株価が倍増した実績（＝同じ主が戻りやすい習性）があるか。
    ※時価総額が巨大な銘柄は、ハゲタカではなく「機関投資家動向」として自動判定します。
    
    #### ② 🌟 お得度（★マーク）
    決算の数字を使わず、**「過去に投資家がどこで買って捕まっているか」という純粋な需給の法則**だけで上値余地を導き出します。
    星が多いほど、上に邪魔者がおらずスルスルと上がりやすい「お宝銘柄」です。
    
    #### ③ 🚧 チャート ＆ 価格帯別出来高（右側の横棒）
    チャートの右側にある横向きの棒グラフは、**過去半年間で「どの価格帯でどれだけ取引されたか」**を表しています。
    一番棒が長い（取引が集中している）価格帯がオレンジの点線となり、株価が反発・反落しやすい**『強力な岩盤（需給の壁）』**として機能します。
    """)

tab1, tab2 = st.tabs(["🔍 複数銘柄一括診断", "🦅 全市場スキャン"])

# --- タブ1 ---
with tab1:
    st.markdown("##### 気になる銘柄を入力（スペース区切りで複数可）")
    with st.form(key='search_form'):
        input_code = st.text_area("銘柄コード", height=68, placeholder="例: 7011 7203 9984")
        search_btn = st.form_submit_button("🦅 ハゲタカAIで診断する")

    if search_btn and input_code:
        codes = normalize_input(input_code)
        if not codes:
            st.error("銘柄コードを入力してください")
        else:
            with st.spinner(f'🦅 {len(codes)}銘柄を精密検査中...'):
                for code in codes:
                    if not code.isdigit(): continue
                    data = evaluate_stock(f"{code}.T", mode="search")
                    
                    if data:
                        with st.container():
                            st.markdown("---")
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                rank_color = "red" if data['ランク'] == "S" else "orange" if data['ランク'] == "A" else "blue"
                                st.markdown(f"<h2 style='color:{rank_color};'>総合判定: {data['ランク']}</h2>", unsafe_allow_html=True)
                                st.write(f"**{data['コード']} {data['銘柄名']}**")
                                st.write(f"現在値: **{data['現在値']}** 円")
                                st.write(f"時価総額: **{int(data['時価総額'])}** 億円")
                                
                                st.markdown("---")
                                st.markdown(f"### {data['intervention_name']}: {data['intervention_score']}%")
                                st.progress(data['intervention_score'] / 100.0)
                                st.markdown(f"**{data['intervention_comment']}**")
                                
                            with c2:
                                st.markdown("##### 📋 AI診断カルテ")
                                
                                # 1. お得度（需給ターゲット）
                                st.markdown(f"#### {data['star_rating']} {data['star_desc']}")
                                # プルダウン式の解説
                                with st.expander("💡 算出ロジックとAIの解説を見る"):
                                    st.info(data['star_logic'])
                                
                                st.markdown("---")
                                
                                # 2. 安全性
                                msg_safe = f"🛡️ **安全性 (高値掴みリスク):** 底値乖離 {data['乖離率']:.1f}%"
                                st.write(msg_safe)
                                with st.expander("💡 安全性の見方"):
                                    st.caption("直近の底値から20%以内であれば勝負しやすい範囲です。高すぎる場合は利確の売り浴びせに注意してください。")

                            # チャート描画（価格帯別出来高付き）
                            draw_chart(data)
                    else:
                        st.error(f"❌ {code}: データ取得エラー")

# --- タブ2 ---
with tab2:
    st.markdown("##### ハゲタカが潜む銘柄を全市場から抽出します")
    
    if st.button("🚀 全市場スキャン開始（約5〜10分）", key="scan_btn"):
        st.warning("現在スキャン中です。完了するまでブラウザを閉じないでください...")
        
        target_codes = [c for c in jpx_codes if c != "4052"] # 除外設定
        
        if not target_codes:
            st.error("銘柄リストの取得に失敗しました。")
        else:
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total = len(target_codes)
            for i, code in enumerate(target_codes):
                status_text.text(f"スキャン中... {i+1} / {total} 銘柄完了")
                data = evaluate_stock(f"{code}.T", mode="scan")
                
                if data:
                    results.append(data)
                
                progress_bar.progress((i + 1) / total)
            
            status_text.text(f"スキャン完了！ 有望な {len(results)} 銘柄を発見しました。")
            
            if results:
                df = pd.DataFrame(results)
                rank_map = {"S": 5, "A": 4, "B": 3, "C": 2}
                df['score'] = df['ランク'].map(rank_map).fillna(0)
                df = df.sort_values(by=['score', 'intervention_score'], ascending=[False, False])

                for index, row in df.iterrows():
                    with st.expander(f"【{row['ランク']}】 {row['コード']} {row['銘柄名']} | {row['intervention_name']}: {row['intervention_score']}%"):
                        st.write(f"時価総額: {int(row['時価総額'])}億 | 乖離率: {row['乖離率']:.1f}%")
                        st.write(f"**お得度:** {row['star_rating']} {row['star_desc']}")
                        draw_chart(row)
            else:
                st.warning("条件に合致するお宝銘柄は発見されませんでした。")
