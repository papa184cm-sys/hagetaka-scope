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
import re

# === ⚙️ ページ設定 ===
st.set_page_config(
    page_title="源太AI・ハゲタカscope",
    page_icon="🦅",
    layout="wide"
)

# === 🦅 サイドバー：源太流・相場カレンダー ===
st.sidebar.title("🦅 ハゲタカ戦略室")

# サイドバーの記号解説：Ver 5.7の綺麗なHTML構造を完全復元
st.sidebar.markdown("""
<div style='border: 1px solid #ff4b4b; border-radius: 5px; padding: 15px; margin-bottom: 20px; background-color: rgba(255, 75, 75, 0.05);'>
<h3 style='margin-top: 0; margin-bottom: 15px; font-size: 1.1rem; color: #ff4b4b;'>🦅 記号の解説</h3>
<div style='font-size: 0.95rem; line-height: 1.6;'>
    <div style='margin-bottom: 12px;'>
        <b>💎 プラチナ (Platinum)</b><br>
        時価総額 500億～2000億円<br>
        <span style='color: #bbbbbb; font-size: 0.85rem;'>ハゲタカが最も好む黄金サイズ。</span>
    </div>
    <div style='margin-bottom: 12px;'>
        <b>🦅 ハゲタカ参戦？</b><br>
        出来高急増（平常時の1.5倍以上）<br>
        <span style='color: #bbbbbb; font-size: 0.85rem;'>水面下での「仕込み」疑惑あり。</span>
    </div>
    <div>
        <b>🧬 DNA（習性）</b><br>
        過去に短期間で急騰した実績あり<br>
        <span style='color: #bbbbbb; font-size: 0.85rem;'>「主（ぬし）」が住み着いている証拠。</span>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 2026年 戦略カレンダー")

current_month = datetime.now().month
strategy_text = {
    1: "⚠️ **1月：資金温存**\n外国人買いが入りますが、3月の暴落に備えて現金比率を高めましょう。",
    2: "⚠️ **2月：様子見**\n無理に動く時期ではありません。監視銘柄の選定に集中。",
    3: "📉 **3月：換金売り警戒＆仕込み**\n中旬の暴落は「優良株」を拾う最大のチャンス！",
    4: "🔥 **4月：ニューマネー流入**\n新年度予算で中小型株が吹き上がります。3月の仕込みを利益に。",
    5: "🔥 **5月：セルインメイは嘘**\n決算後の「材料出尽くし」急落は、ハゲタカの集め場です。",
    6: "💰 **6月：ボーナス・配当再投資**\n資金潤沢. 大型株へシフトする時期。",
    7: "💰 **7月：サマーラリー**\n夏枯れ前の最後のひと稼ぎ。",
    8: "🌊 **8月：夏枯れ・真空地帯**\nハゲタカ不在. AIによるフラッシュクラッシュ（急落）のみ警戒。",
    9: "📉 **9月：彼岸底**\n10月の大底に向けた調整。",
    10: "🔥 **10月：年内最後の大底**\nここから年末ラリーへ. 全力買いの急所。",
    11: "🍂 **11月：節税売り（タックスロス）**\n投げ売りされた銘柄を拾う。",
    12: "🎉 **12月：掉尾の一振**\n年末ラリーで全てを利益に変えて逃げ切る。"
}
st.sidebar.info(strategy_text.get(current_month, "戦略待機中"))

# === 🛠️ 関数定義 ===

@st.cache_data(ttl=86400)
def get_jpx_data():
    """JPXのサイトから最新の銘柄一覧Excelを自動探索（和名確保の要）"""
    try:
        html_url = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(html_url, headers=headers, timeout=10)
        match = re.search(r'href="([^"]+data_j\.xls)"', response.text)
        if not match: return {}, []
        file_url = "https://www.jpx.co.jp" + match.group(1)
        xls_response = requests.get(file_url, headers=headers, timeout=10)
        df = pd.read_excel(io.BytesIO(xls_response.content))
        df_tickers = df[df.iloc[:, 3].isin(['プライム', 'スタンダード', 'グロース'])]
        codes = df_tickers.iloc[:, 1].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','').isdigit() else "")
        return dict(zip(codes, df_tickers.iloc[:, 2])), list(codes)
    except:
        return {}, []

jpx_names, jpx_codes = get_jpx_data()

def format_market_cap(oku_val):
    oku_val = int(oku_val)
    if oku_val >= 10000:
        cho = oku_val // 10000
        oku = oku_val % 10000
        return f"{cho}兆{oku}億円" if oku > 0 else f"{cho}兆円"
    return f"{oku_val}億円"

def evaluate_stock(ticker, mode="search"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2y")
        if len(hist) < 30: return None

        current_price = hist['Close'].iloc[-1]
        current_vol = hist['Volume'].iloc[-1]
        avg_vol_100 = hist['Volume'][-100:].mean()
        info = stock.info
        
        market_cap_oku = info.get('marketCap', 0) / 100000000
        code_only = ticker.replace(".T", "")
        
        # 和名取得ロジック（バックアップ付き復元）
        jp_name = jpx_names.get(code_only)
        if not jp_name or re.search(r'[a-zA-Z]', jp_name):
            try:
                url_yfjp = f"https://finance.yahoo.co.jp/quote/{code_only}.T"
                res_yfjp = requests.get(url_yfjp, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                match = re.search(r'<title>(.+?)(?:\(株\))?【', res_yfjp.text)
                jp_name = match.group(1).strip() if match else info.get('longName', ticker)
            except:
                jp_name = info.get('longName', ticker)

        # 配当情報
        dividend_amt = info.get('dividendRate', 0)
        payout_ratio = info.get('payoutRatio', 0)
        formatted_div = f"{dividend_amt}円" if dividend_amt else "なし"
        formatted_payout = f"{round(payout_ratio * 100, 1)}%" if payout_ratio else "-"

        # 需給・底値計算
        hist_6mo = hist.tail(125)
        price_bins = pd.cut(hist_6mo['Close'], bins=15)
        vol_profile = hist_6mo.groupby(price_bins, observed=False)['Volume'].sum()
        max_vol_price = vol_profile.idxmax().mid
        recent_20_low = hist['Low'][-20:].min()
        deviation = (current_price - recent_20_low) / recent_20_low * 100

        # フラグ・アイコン判定
        vol_ratio = current_vol / avg_vol_100 if avg_vol_100 > 0 else 0
        is_platinum = 500 <= market_cap_oku <= 2000
        is_magma = vol_ratio >= 1.5
        has_dna = check_dna(hist)
        
        icons_list = []
        if has_dna: icons_list.append("🧬")
        if is_platinum: icons_list.append("💎")
        if is_magma: icons_list.append("🦅")
        icons_str = " ".join(icons_list)

        # 介入度スコア
        intervention_score = 0
        if is_platinum: intervention_score += 35
        elif 100 <= market_cap_oku <= 5000: intervention_score += 15
        if vol_ratio >= 3.0: intervention_score += 40
        elif vol_ratio >= 1.5: intervention_score += 25
        if has_dna: intervention_score += 10
        intervention_score = int(round(min(intervention_score, 100) / 10.0)) * 10
        
        # 安全性判定（丁寧な文章を復元）
        safe_judgment = ""
        safe_explain = ""
        if deviation <= 3.0:
            safe_judgment = "★ 絶好：底値煮詰まり完了の可能性"
            safe_explain = "直近1ヶ月の最安値からほぼ無乖離です。反発に向けてエネルギーが溜まっていると推測されます。"
        elif deviation <= 5.0:
            safe_judgment = "★ 有望：勝負しやすいエントリー位置"
            safe_explain = "底値からの誤差範囲内であり、資金流入が始まれば上値を追いやすい状態と言えます。"
        elif deviation <= 10.0:
            safe_judgment = "✓ 及第点：トレンド発生の兆候あり"
            safe_explain = "月足目線の調整を終え、再度上を目指す展開が期待できる状態です。"
        elif deviation <= 20.0:
            safe_judgment = "⚠️ 限界範囲：高値掴みに注意"
            safe_explain = "当ツールが一般的な勝負圏内と判断する目安の限界です。これ以上の価格追いはリスクが高まる傾向にあります。"
        else:
            safe_judgment = "💀 高度な警戒：上級者向けの過熱圏"
            safe_explain = "短期的な高値掴みとなる可能性が高い水準です。新規参戦は極めて慎重に行う必要があり、上級者向けと言えます。"

        # ランク判定
        total_rank = "C"
        if intervention_score >= 80 and (current_price >= max_vol_price or (max_vol_price-current_price)/current_price >= 0.3): total_rank = "S"
        elif intervention_score >= 60: total_rank = "A"
        elif deviation > 20: total_rank = "注意"

        return {
            "コード": code_only, "銘柄名": jp_name, "現在値": int(current_price),
            "時価総額_表示": format_market_cap(market_cap_oku), "ランク": total_rank,
            "乖離率": round(deviation, 1), "hist": hist, "max_vol_price": max_vol_price,
            "recent_20_low": recent_20_low, "icons_str": icons_str,
            "intervention_score": intervention_score,
            "年間配当": formatted_div, "配当性向": formatted_payout,
            "safe_judgment": safe_judgment, "safe_explain": safe_explain
        }
    except: return None

def check_dna(hist):
    try:
        pct_change = hist['Close'].pct_change(periods=60)
        return pct_change.max() >= 0.8
    except: return False

def draw_chart(row):
    hist_data = row['hist'].tail(150)
    max_vol_price = int(row['max_vol_price'])
    recent_20_low = int(row['recent_20_low'])
    
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0)
    fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name="株価", showlegend=False), row=1, col=1)
    
    hist_data_copy = hist_data.copy()
    hist_data_copy['price_bins'] = pd.cut(hist_data_copy['Close'], bins=15)
    vol_profile = hist_data_copy.groupby('price_bins', observed=False)['Volume'].sum()
    fig.add_trace(go.Bar(x=vol_profile.values, y=[b.mid for b in vol_profile.index], orientation='h', marker_color='rgba(255, 165, 0, 0.6)', showlegend=False), row=1, col=2)
    
    # チャート上の価格ラベル表示（Ver 5.7の復元）
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", 
                  annotation_text=f" {max_vol_price}円 🚧 需給の壁 ", annotation_position="top left", annotation_font_color="orange", row=1, col=1)
    fig.add_hline(y=recent_20_low, line_width=1.5, line_dash="dot", line_color="cyan", 
                  annotation_text=f" {recent_20_low}円 🔵 直近底値 ", annotation_position="bottom left", annotation_font_color="cyan", row=1, col=1)

    fig.update_layout(xaxis_rangeslider_visible=False, height=380, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_xaxes(showticklabels=True, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=2)
    st.plotly_chart(fig, use_container_width=True)

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")

with st.expander("🔰 【源太AI・各項目の見方と算出ロジック】"):
    st.markdown("""
    #### ① 🦅 介入度（％メーター）
    大口投資家がこの株を狙っている可能性を示します。
    #### ② 🌟 お得度（★マーク）
    上値の需給の壁（しこり玉）までどれくらい上昇の余地があるかを示します。
    #### ③ 🛡️ 安全性（底値乖離）
    直近20営業日（約1ヶ月）の底値からの離れ具合です。20%を超えると高値掴みのリスクとなります。
    """)

tab1, tab2 = st.tabs(["🔍 複数銘柄一括診断", "🦅 全市場スキャン"])

with tab1:
    with st.form(key='search_form'):
        input_code = st.text_area("銘柄コード入力", height=68, placeholder="例: 7011 7203")
        search_btn = st.form_submit_button("🦅 ハゲタカAIで診断する")

    if search_btn and input_code:
        codes = [c.strip() for c in input_code.replace(',', ' ').replace('\n', ' ').split()]
        for code in codes:
            data = evaluate_stock(f"{code}.T")
            if data:
                with st.container():
                    st.markdown("---")
                    # 1. 銘柄名を最上部に大きく表示
                    st.markdown(f"## {data['コード']} {data['銘柄名']}")
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        # 2. 総合判定と記号を横並びに配置
                        rank_color = "orange" if data['ランク'] != "注意" else "red"
                        st.markdown(f"#### 総合判定: <span style='color:{rank_color};'>{data['ランク']}</span> &nbsp;&nbsp;&nbsp; <span style='font-size: 1.5rem;'>{data['icons_str']}</span>", unsafe_allow_html=True)
                        
                        with st.expander("💡 総合判定の基準"):
                            st.caption("S:介入80%以上+余地大 / A:介入60%以上 / B:プラチナ+底値 / 注意:乖離20%超")
                        
                        st.write(f"現在値: **{data['現在値']}** 円")
                        st.write(f"時価総額: **{data['時価総額_表示']}**")
                        st.write(f"年間配当: **{data['年間配当']}**")
                        st.write(f"配当性向: **{data['配当性向']}**")
                        
                        st.markdown(f"**介入度: {data['intervention_score']}%**")
                        st.progress(data['intervention_score'] / 100.0)

                    with c2:
                        # 3. 安全性のタイトル強調と赤文字AI解説を復元
                        st.markdown(f"<h3 style='font-size: 1.2rem; font-weight: bold;'>🛡️ 安全性（高値掴みリスク）: {data['乖離率']}%</h3>", unsafe_allow_html=True)
                        st.markdown(f"<div style='color: #ff4b4b; background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>💡 AI解説:</strong> {data['safe_explain']}</div>", unsafe_allow_html=True)
                        st.markdown(f"**（判定: {data['safe_judgment']}）**")
                        
                        draw_chart(data)

with tab2:
    st.markdown("##### 有望な銘柄を自動抽出します")
    if st.button("🚀 スキャン開始"):
        results = []
        progress = st.progress(0)
        for i, code in enumerate(jpx_codes[:100]): # デモ用に制限
            d = evaluate_stock(f"{code}.T", mode="scan")
            if d: results.append(d)
            progress.progress((i+1)/100)
        
        if results:
            for r in results:
                with st.expander(f"【{r['ランク']}】 {r['icons_str']} {r['コード']} {r['銘柄名']}"):
                    st.write(f"現在値: {r['現在値']}円 | 介入度: {r['intervention_score']}% | {r['safe_judgment']}")
                    draw_chart(r)
