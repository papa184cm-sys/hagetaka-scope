import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    * 「主（ぬし）」が住み着いている証拠。
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
                if last_price and last_price <= 300:
                    return None
                mcap = getattr(fast, 'market_cap', None)
                if mcap:
                    mcap_oku = mcap / 100000000
                    if mcap_oku < 50 or mcap_oku > 10000:
                        return None
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

        if current_price <= 300:
            if mode == "scan": return None

        # --- ① お得度（上昇余地）の星評価ロジック ---
        past_1y = hist[-250:]
        year_high = past_1y['High'].max()
        year_low = past_1y['Low'].min()
        
        # BPS（1株当たり純資産）を取得。取得できない場合は直近1年高値を仮の理論株価とする
        bps = info.get('bookValue', 0)
        target_price = max(year_high, bps) if bps > 0 else year_high
        
        upside_potential = 0
        if current_price > 0 and target_price > current_price:
            upside_potential = ((target_price - current_price) / current_price) * 100

        star_rating = ""
        star_desc = ""
        star_logic = f"理論株価({int(target_price)}円)と現在値を比較した「お得度」です。"
        
        if upside_potential >= 50:
            star_rating = "★★★★★"
            star_desc = "お宝（上昇余地 +50% 以上）"
            star_logic += " 解散価値(PBR1倍)や過去高値から見て、強烈な割安水準に放置されています。"
        elif upside_potential >= 30:
            star_rating = "★★★★☆"
            star_desc = "激アツ（上昇余地 +30% 〜 +50%）"
            star_logic += " 大口が買い上げを狙うには十分すぎる「のり代」があります。"
        elif upside_potential >= 15:
            star_rating = "★★★☆☆"
            star_desc = "有望（上昇余地 +15% 〜 +30%）"
            star_logic += " 堅実な上昇が見込める、買い妙味のある水準です。"
        elif upside_potential >= 5:
            star_rating = "★★☆☆☆"
            star_desc = "普通（上昇余地 +5% 〜 +15%）"
            star_logic += " 適正価格に近く、大きな上値は期待しづらい状態です。"
        elif upside_potential > 0:
            star_rating = "★☆☆☆☆"
            star_desc = "トントン（上昇余地 0% 〜 +5%）"
            star_logic += " ほぼ理論株価に到達しており、旨味は少ないです。"
        else:
            star_rating = "☆☆☆☆☆"
            star_desc = "割高（上昇余地 0% 未満）"
            star_logic += " ※ただし、すでに活況入りしている可能性もあるため、トレンドを追う短期勝負の順張りならトライする価値はあります。"

        # --- ② 各種指標の取得 ---
        position_score = 0.5
        if year_high != year_low:
            position_score = (current_price - year_low) / (year_high - year_low)
            
        has_dna = check_dna(hist)
        vol_ratio = current_vol / avg_vol_100 if avg_vol_100 > 0 else 0
        is_platinum = 500 <= market_cap_oku <= 2000
        is_magma = vol_ratio > 1.5

        # --- ③ ハゲタカ介入度（%）メーターのロジック ---
        intervention_score = 0
        intervention_reasons = []

        # サイズ感（大口の狙いやすさ）
        if is_platinum:
            intervention_score += 35
            intervention_reasons.append("✓ プラチナレンジ：大口が最も仕掛けやすい黄金サイズ(500〜2000億)")
        elif 100 <= market_cap_oku <= 5000:
            intervention_score += 15
            intervention_reasons.append("✓ ターゲット圏内：機関投資家が売買可能な企業規模")

        # 資金流入（出来高異常）
        if vol_ratio >= 3.0:
            intervention_score += 40
            intervention_reasons.append(f"✓ 資金流入：出来高が平常時の{vol_ratio:.1f}倍！ステルス集積の疑い極めて濃厚")
        elif vol_ratio >= 1.5:
            intervention_score += 25
            intervention_reasons.append(f"✓ 資金流入：出来高急増({vol_ratio:.1f}倍)。ハゲタカ参戦の兆候あり")

        # 底値圏の煮詰まり・DNA
        if position_score <= 0.2:
            intervention_score += 15
            intervention_reasons.append("✓ 位置エネルギー：底値圏で煮詰まっており、反発のエネルギーが充填済み")
        if has_dna:
            intervention_score += 10
            intervention_reasons.append("✓ 急騰DNA：過去に短期間で倍増した実績（仕手化の習性）あり")

        # 上限100%に丸める
        intervention_score = min(intervention_score, 100)
        
        # 介入度の判定コメント
        intervention_comment = ""
        if intervention_score >= 80:
            intervention_comment = "🚨 【極めて濃厚】大口の介入シグナルが多数点灯しています！"
        elif intervention_score >= 50:
            intervention_comment = "👀 【予兆あり】水面下で集められている可能性があります。"
        else:
            intervention_comment = "💤 【静観】現在は目立った大口の動きは検出されません。"

        # --- 安全性（乖離率） ---
        recent_14_low = hist['Low'][-14:].min()
        deviation = (current_price - recent_14_low) / recent_14_low * 100

        # --- 総合ランク ---
        total_rank = "D"
        if intervention_score >= 80 and upside_potential >= 30: total_rank = "S"
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
            # お得度データ
            "star_rating": star_rating,
            "star_desc": star_desc,
            "star_logic": star_logic,
            "upside_potential": upside_potential,
            # 介入度データ
            "intervention_score": intervention_score,
            "intervention_comment": intervention_comment,
            "intervention_reasons": intervention_reasons,
            "is_platinum": is_platinum,
            "has_dna": has_dna
        }
    except:
        return None

def draw_chart(row):
    hist_data = row['ヒストリ'].tail(150)
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
    fig.update_layout(title=f"{row['銘柄名']} 日足チャート", xaxis_rangeslider_visible=False, height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")
st.caption("Pro Version: 2026.02 | Target: VIP Members")

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
                        with st.expander(f"{data['ランク']}ランク | {data['コード']} {data['銘柄名']}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                rank_color = "red" if data['ランク'] == "S" else "orange" if data['ランク'] == "A" else "blue"
                                st.markdown(f"<h2 style='color:{rank_color};'>総合判定: {data['ランク']}</h2>", unsafe_allow_html=True)
                                st.write(f"現在値: **{data['現在値']}** 円")
                                st.write(f"時価総額: **{int(data['時価総額'])}** 億円")
                                
                                st.markdown("---")
                                # 介入度メーター表示
                                st.markdown(f"### 🦅 ハゲタカ介入度: {data['intervention_score']}%")
                                st.progress(data['intervention_score'] / 100.0)
                                st.markdown(f"**{data['intervention_comment']}**")
                                
                                # なぜその%なのかの理由
                                with st.expander("💡 算出ロジック（なぜこの数値？）"):
                                    st.write("大口投資家が仕掛けやすい条件が揃っているかを自動検出した独自指数です。")
                                    for reason in data['intervention_reasons']:
                                        st.caption(reason)
                                    if not data['intervention_reasons']:
                                        st.caption("現在、特筆すべき大口介入のシグナルはありません。")
                                
                            with c2:
                                st.markdown("##### 📋 AI診断カルテ")
                                
                                # 1. お得度（星評価）
                                st.markdown(f"#### {data['star_rating']} {data['star_desc']}")
                                st.info(f"💡 **AI解説:** {data['star_logic']}")
                                
                                st.markdown("---")
                                
                                # 2. 安全性
                                msg_safe = f"🛡️ **安全性 (高値掴みリスク):** 底値乖離 {data['乖離率']:.1f}%"
                                st.write(msg_safe)
                                st.caption("💡 **AI解説:** 直近の底値から20%以内であれば勝負しやすい範囲です。高すぎる場合は利確の売り浴びせに注意してください。")

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
                df = df.sort_values(by=['score', ' intervention_score'], ascending=[False, False])

                for index, row in df.iterrows():
                    with st.expander(f"【{row['ランク']}】 {row['コード']} {row['銘柄名']} | ハゲタカ介入度: {row['intervention_score']}%"):
                        st.write(f"時価総額: {int(row['時価総額'])}億 | 乖離率: {row['乖離率']:.1f}%")
                        st.write(f"**お得度:** {row['star_rating']} {row['star_desc']}")
                        draw_chart(row)
            else:
                st.warning("条件に合致するお宝銘柄は発見されませんでした。")
