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
import random

# === ⚙️ ページ設定 ===
st.set_page_config(
    page_title="源太AI・ハゲタカscope",
    page_icon="🦅",
    layout="wide"
)

# === 🦅 サイドバー：源太流・相場カレンダー ===
st.sidebar.title("🦅 ハゲタカ戦略室")

st.sidebar.markdown("""
<div style='border: 1px solid #ff4b4b; border-radius: 5px; padding: 15px; margin-bottom: 20px; background-color: rgba(255, 75, 75, 0.05);'>
<h3 style='margin-top: 0; margin-bottom: 10px; font-size: 1.1rem; color: #ff4b4b;'>🦅 記号の解説</h3>
<ul style='padding-left: 20px; margin-bottom: 0; font-size: 0.9rem; line-height: 1.6;'>
    <li style='margin-bottom: 8px;'><b>💎 プラチナ (Platinum)</b><br>時価総額 <b>500億～2000億円</b><br><span style='color: #dddddd;'>ハゲタカが最も仕掛けやすい黄金サイズ。</span></li>
    <li style='margin-bottom: 8px;'><b>🦅 ハゲタカ参戦？</b><br>出来高急増（平常時の1.5倍以上）<br><span style='color: #dddddd;'>水面下での「仕込み」疑惑あり。</span></li>
    <li><b>🧬 DNA（習性）</b><br>過去に短期間で急騰した実績あり。<br><span style='color: #dddddd;'>「主（ぬし）」が住み着いている証拠。</span></li>
</ul>
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
    try:
        html_url = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(html_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        match = re.search(r'href="([^"]+data_j\.xls)"', response.text)
        if not match: return {}, []
            
        file_url = "https://www.jpx.co.jp" + match.group(1)
        xls_response = requests.get(file_url, headers=headers, timeout=10)
        xls_response.raise_for_status()
        
        df = pd.read_excel(io.BytesIO(xls_response.content))
        df_tickers = df[df.iloc[:, 3].isin(['プライム', 'スタンダード', 'グロース'])]
        
        codes = df_tickers.iloc[:, 1].apply(lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','').isdigit() else "")
        name_map = dict(zip(codes, df_tickers.iloc[:, 2]))
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

def format_market_cap(oku_val):
    oku_val = int(oku_val)
    if oku_val >= 10000:
        cho = oku_val // 10000
        oku = oku_val % 10000
        if oku == 0:
            return f"{cho}兆円"
        else:
            return f"{cho}兆{oku}億円"
    else:
        return f"{oku_val}億円"

def evaluate_stock(ticker, mode="search"):
    try:
        stock = yf.Ticker(ticker)

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
        
        formatted_mcap = format_market_cap(market_cap_oku)

        dividend_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0
        payout_ratio = info.get('payoutRatio') or 0
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or 0

        if dividend_rate > 0:
            payout_str = f"{payout_ratio * 100:.1f}%" if payout_ratio > 0 else "-"
            yield_str = f"{div_yield * 100:.2f}%" if div_yield > 0 else "-"
            dividend_text = f"{dividend_rate}円 （利回り: {yield_str} / 配当性向: {payout_str}）"
        else:
            dividend_text = "無配"

        code_only = ticker.replace(".T", "")
        jp_name = jpx_names.get(code_only)
        if not jp_name or re.search(r'[a-zA-Z]', jp_name):
            try:
                url_yfjp = f"https://finance.yahoo.co.jp/quote/{code_only}.T"
                res_yfjp = requests.get(url_yfjp, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                match = re.search(r'<title>(.+?)(?:\(株\))?【', res_yfjp.text)
                if match: jp_name = match.group(1).strip()
                else: jp_name = info.get('longName', ticker)
            except:
                jp_name = info.get('longName', ticker)

        if current_price <= 300 and mode == "scan": return None

        if market_cap_oku >= 5000:
            cap_category = "large"
            intervention_name = "🏢 機関投資家・大口流入度"
        elif market_cap_oku >= 50:
            cap_category = "target"
            intervention_name = "🦅 ハゲタカ介入度"
        else:
            cap_category = "small"
            intervention_name = "⚠️ イナゴマネー過熱度 (超小型)"

        hist_6mo = hist.tail(125)
        price_bins = pd.cut(hist_6mo['Close'], bins=15)
        vol_profile = hist_6mo.groupby(price_bins, observed=False)['Volume'].sum()
        max_vol_price = vol_profile.idxmax().mid

        upside_potential = 0
        is_blue_sky = False
        
        if current_price >= max_vol_price:
            is_blue_sky = True
        else:
            upside_potential = ((max_vol_price - current_price) / current_price) * 100

        recent_20_low = hist['Low'][-20:].min()
        deviation = (current_price - recent_20_low) / recent_20_low * 100

        # 🎯 新機能：上値余地（ポテンシャル）のベースレベルを判定
        if is_blue_sky:
            pot_level = 4
        elif upside_potential >= 30:
            pot_level = 3
        elif upside_potential >= 15:
            pot_level = 2
        elif upside_potential >= 5:
            pot_level = 1
        else:
            pot_level = 0

        # 🎯 新機能：乖離率（高値掴みリスク）による星の最大数制限（キャップ）
        if deviation <= 10.0:
            max_stars = 5
        elif deviation <= 20.0:
            max_stars = 4
        else:
            max_stars = 3

        # 最終的な星数を決定（ポテンシャルレベル+1 が本来の星数。それを最大数で制限する）
        raw_stars = pot_level + 1
        final_stars = min(raw_stars, max_stars)
        star_rating = "★" * final_stars + "☆" * (5 - final_stars)

        # 🎯 修正：星の制限有無に応じた、コンプライアンス対応済みの30パターンテキスト
        if raw_stars > final_stars:
            # 【制限がかかった場合（過熱感あり）の専用テキスト】
            if final_stars == 4:
                patterns = [
                    ("【上昇トレンド・高値警戒】", "上値の壁は薄いものの、直近底値からの上昇が続いており、新規参入は短期目線での対応が無難な水準です。"),
                    ("【モメンタム継続・押し目待ち】", "強い勢いを保っていますが、やや過熱感が出てきました。リスクを抑えるなら押し目を待つのが一案です。"),
                    ("【高値圏の順張り局面】", "上値余地はありますが、すでに一定の上昇を遂げています。利益確定売りに警戒しつつの判断が求められます。")
                ]
            else: # final_stars == 3
                patterns = [
                    ("【高値圏のモメンタム相場】", "上値を抑える壁はなく強いトレンドですが、乖離率が高く高値掴みのリスクがあります。短期戦と割り切った対応が求められる水準です。"),
                    ("【急騰後・リスクリワード低下】", "勢いは非常に強いものの、今からの新規エントリーはリスクとリターンのバランスが取りにくくなっています。慎重な判断が必要です。"),
                    ("【過熱気味の上昇波】", "上値余地を残しつつも、テクニカル的には過熱感が漂います。無理に深追いせず、冷静に状況を見極めたい局面です。")
                ]
        else:
            # 【制限がかからなかった場合（通常）のテキスト】
            if pot_level == 4:
                patterns = [
                    ("【青天井モード】", "上値に目立った需給の壁（抵抗線）がなく、売り手が不在の真空地帯に突入しています。"),
                    ("【上値抵抗クリア】", "過去の重いしこり玉（含み損）エリアを突破しており、需給が好転している局面です。"),
                    ("【真空地帯への突入】", "目立った戻り売り圧力が少なく、トレンドに逆らわない順張りが有効な水準です。"),
                    ("【売り手不在の快晴】", "上値での迷いが生じにくく、資金流入がストレートに株価に反映されやすい帯域にいます。"),
                    ("【需給良好・上値追い】", "過去の取引の壁を抜けました。ただし、急ピッチな上昇時は利食いにも留意してください。"),
                    ("【視界良好チャート】", "上値を抑えつける強固な壁が見当たりません。資金の逃げ足にだけ注意して波に乗りたい位置です。")
                ]
            elif pot_level == 3:
                patterns = [
                    ("【大幅な上値余地】", "強固な抵抗線まで距離があり、大きな値幅取りが狙えるポテンシャルを秘めています。"),
                    ("【上値余地：特大】", "最大の壁まで十分な空間が開いており、大口の仕掛けが入りやすいエリアです。"),
                    ("【リバウンド妙味】", "上値の重い水準まで距離があるため、反発トレンドに乗れた際のリターンが大きくなりやすい形状です。"),
                    ("【ターゲット遠方】", "主要なヤレヤレ売りが降ってくる水準まで、軽快な足取りが期待できます。"),
                    ("【絶好の上昇空間】", "次の大きな節目まで邪魔する壁がなく、買い圧力が素直に効きやすいチャートです。"),
                    ("【値幅取り期待ゾーン】", "出来高の壁まで距離的余裕があり、トレンド発生時の爆発力に期待が持てる位置取りです。")
                ]
            elif pot_level == 2:
                patterns = [
                    ("【堅実な上値余地】", "次の抵抗帯まで適度な距離があり、セオリー通りの着実な上昇が見込めます。"),
                    ("【上値余地：中】", "極端な遠さではありませんが、壁に到達するまで十分に利益を狙える水準にあります。"),
                    ("【標準的なターゲット】", "最も分厚い出来高の壁に向けて、じわじわと水準を切り上げる展開が期待されます。"),
                    ("【ステップアップ局面】", "まずは直上の壁を目標に、資金の流入に伴って堅調に推移しやすい位置です。"),
                    ("【適度な空間】", "壁までの距離感として「ちょうど狙いやすい」位置取り。押し目があれば拾いたい形状です。"),
                    ("【トレンド追従向きの局面】", "上値抵抗までの道のりは見えており、無理のない範囲で波に乗るのが有効な局面です。")
                ]
            elif pot_level == 1:
                patterns = [
                    ("【抵抗帯接近】", "すぐ上に出来高の壁が迫っています。ここを突破できるかが目先の最大の焦点となります。"),
                    ("【激戦区への突入】", "過去の取引が密集するエリアが間近です。売り買いが交錯しやすく、乱高下に注意が必要です。"),
                    ("【上値の壁テスト】", "分厚い壁へのアタック局面。跳ね返されるリスクも考慮し、打診買いから入りたい水準です。"),
                    ("【ブレイク前夜警戒】", "すぐ上の抵抗線を明確に上抜ければ景色が一変しますが、現状はまだ重い壁の下に位置しています。"),
                    ("【上値余地：小】", "ターゲットまでの距離が短く、ここから新規で大きな値幅を狙うにはややリスクが伴う位置です。"),
                    ("【壁打ち反落リスク】", "壁にぶつかって反落する「壁打ち」になりやすい位置。突破を確認してからの参戦でも遅くありません。")
                ]
            else:
                patterns = [
                    ("【頭打ち警戒】", "現在値のすぐ上に強烈なしこり玉が大量待機しており、上値が極めて重い状態です。"),
                    ("【岩盤到達・上値重し】", "過去最大の出来高を記録した価格帯に突入しています。大量の戻り売りを消化する莫大なパワーが必要です。"),
                    ("【ヤレヤレ売り集中エリア】", "「買値に戻ったら売ろう」と待っていた投資家の売りが降り注ぐ、最も苦しい価格帯です。"),
                    ("【上値抵抗MAX】", "需給面での障壁が一番高いエリアです。好材料などの強力なエンジンがない限り、突破は困難です。"),
                    ("【ブレイクアウト待ちが一案】", "この分厚い壁の中での勝負は分が悪いです。明確に上抜けて真空地帯に入るのを待つのが賢明です。"),
                    ("【撤退ラインの徹底が重要】", "壁に跳ね返されて急落するリスクが高い水準です。保有している場合は利益確定も視野に入る位置と言えます。")
                ]

        selected_pattern = random.choice(patterns)
        star_desc = selected_pattern[0]
        base_logic = selected_pattern[1]

        flavor_logic = ""
        if cap_category == "large":
            flavor_logic = "時価総額が巨大なため『仕手筋の急騰仕掛け』は入りませんが、機関投資家や外国人投資家の資金流入をエンジンとした、強力で重厚なトレンドが期待できます。"
        elif cap_category == "target":
            flavor_logic = "ハゲタカが最も好む規模感であり、彼らが資金を投下すれば一気に株価が吹き飛ぶ（または壁を突破する）ポテンシャルを秘めています。"
        else:
            flavor_logic = "※ただし時価総額が小さすぎるため、プロは資金を入れづらい銘柄です。主に個人マネーによる『マネーゲーム（乱高下）』になりやすいため、ロットを落とした短期勝負に限定してください。"

        star_logic = base_logic + "<br><br>" + flavor_logic

        past_1y = hist[-250:]
        year_high = past_1y['High'].max()
        year_low = past_1y['Low'].min()
        position_score = 0.5
        if year_high != year_low:
            position_score = (current_price - year_low) / (year_high - year_low)
            
        has_dna = check_dna(hist)
        vol_ratio = current_vol / avg_vol_100 if avg_vol_100 > 0 else 0
        
        is_platinum = 500 <= market_cap_oku <= 2000
        is_magma = vol_ratio >= 1.5

        # 🎯 修正：コンプライアンス対応（安全性の判定文言からも「推奨」を排除）
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
        elif deviation <= 15.0:
            safe_judgment = "✓ 短期なら：スピード勝負の領域"
            safe_explain = "トレンドは発生中ですが、ここからは短期目線での対応が求められます。深追いには注意が必要です。"
        elif deviation <= 20.0:
            safe_judgment = "⚠️ 限界範囲：高値掴みに注意"
            safe_explain = "当ツールが一般的な勝負圏内と判断する目安の限界です。これ以上の価格追いはリスクが高まる傾向にあります。"
        elif deviation <= 30.0:
            safe_judgment = "❌ 警戒：短期的な過熱感あり"
            safe_explain = "すでに大きく動いており、大口の利益確定売りに押されるリスクが高まっています。"
        else:
            safe_judgment = "💀 高度な警戒：上級者向けの過熱圏"
            safe_explain = "短期的な高値掴みとなる可能性が高い水準です。新規参戦は極めて慎重に行う必要があり、上級者向けのタイミングと言えます。"

        intervention_score = 0
        if is_platinum: intervention_score += 35
        elif 100 <= market_cap_oku <= 5000: intervention_score += 15
        if vol_ratio >= 3.0: intervention_score += 40
        elif vol_ratio >= 1.5: intervention_score += 25
        if position_score <= 0.2: intervention_score += 15
        if has_dna: intervention_score += 10
        
        intervention_score = int(round(min(intervention_score, 100) / 10.0)) * 10
        
        intervention_comment = ""
        if intervention_score >= 80:
            intervention_comment = "🚨 【極めて濃厚】大口（機関 investment）の介入シグナルが点灯！"
        elif intervention_score >= 50:
            intervention_comment = "👀 【予兆あり】水面下で玉（ぎょく）が集められている可能性があります."
        else:
            intervention_comment = "💤 【静観】現在は目立った大口の動きは検出されません."

        base_rank = "D"
        if intervention_score >= 80 and (is_blue_sky or upside_potential >= 30): base_rank = "S"
        elif intervention_score >= 60: base_rank = "A"
        elif is_platinum and position_score <= 0.3: base_rank = "B"
        else: base_rank = "C"

        if current_price <= 300: base_rank = "E"
        
        if mode == "scan" and base_rank in ["D", "E"]: return None

        warning_text = ""
        if deviation > 20:
            warning_text = "【注意】※安全性を要確認"

        icons_list = []
        if has_dna: icons_list.append("🧬")
        if is_platinum: icons_list.append("💎")
        if is_magma: icons_list.append("🦅")
        icons_str = " ".join(icons_list)

        return {
            "コード": code_only,
            "銘柄名": jp_name,
            "現在値": int(current_price),
            "時価総額": market_cap_oku,
            "時価総額_表示": formatted_mcap,
            "dividend_text": dividend_text,
            "ランク": base_rank,
            "警告": warning_text,
            "乖離率": deviation,
            "hist": hist,
            "max_vol_price": max_vol_price,
            "recent_20_low": recent_20_low,
            "star_rating": star_rating,
            "star_desc": star_desc,
            "star_logic": star_logic,
            "intervention_name": intervention_name,
            "intervention_score": intervention_score,
            "intervention_comment": intervention_comment,
            "safe_judgment": safe_judgment,
            "safe_explain": safe_explain,
            "icons_str": icons_str
        }
    except:
        return None

def draw_chart(row):
    hist_data = row['hist'].tail(150)
    max_vol_price = row['max_vol_price']
    recent_20_low = row['recent_20_low']
    
    bins = 15
    hist_data_copy = hist_data.copy()
    hist_data_copy['price_bins'] = pd.cut(hist_data_copy['Close'], bins=bins)
    vol_profile = hist_data_copy.groupby('price_bins', observed=False)['Volume'].sum()
    bin_centers = [b.mid for b in vol_profile.index]
    bin_volumes = vol_profile.values
    
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0)
    fig.add_trace(go.Candlestick(x=hist_data.index, open=hist_data['Open'], high=hist_data['High'], low=hist_data['Low'], close=hist_data['Close'], name="株価", showlegend=False), row=1, col=1)
    fig.add_trace(go.Bar(x=bin_volumes, y=bin_centers, orientation='h', marker_color='rgba(255, 165, 0, 0.6)', name="出来高ボリューム", showlegend=False, hoverinfo='y'), row=1, col=2)
    
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", 
                  annotation_text=f" {int(max_vol_price)}円 🚧 需給の壁 ", 
                  annotation_position="top left", annotation_font_color="orange", row=1, col=1)
    fig.add_hline(y=max_vol_price, line_width=2, line_dash="dash", line_color="orange", row=1, col=2)
    
    fig.add_hline(y=recent_20_low, line_width=1.5, line_dash="dot", line_color="cyan", 
                  annotation_text=f" 直近底値(1ヶ月) 🔵 {int(recent_20_low)}円 ", 
                  annotation_position="bottom right", annotation_font_color="cyan", row=1, col=1)
    fig.add_hline(y=recent_20_low, line_width=1.5, line_dash="dot", line_color="cyan", row=1, col=2)

    fig.update_layout(title=f"{row['銘柄名']} 日足 ＆ 価格帯別出来高", xaxis_rangeslider_visible=False, height=350, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_xaxes(showticklabels=False, row=1, col=2)
    st.plotly_chart(fig, use_container_width=True)

# === 🖥️ メイン画面 ===
st.title("🦅 源太AI・ハゲタカscope")
st.caption("Pro Version: 2026.02 | Target: VIP Members")

with st.expander("🔰 【源太AI・各項目の見方と算出ロジック】"):
    st.markdown("""
    #### ① 🦅 介入度（％メーター）
    **「今、大口投資家がこの株を狙っている可能性」**を示します. (軽すぎず重すぎない規模、異常出来高、底値煮詰まり、急騰DNAから算出).
    
    #### ② 🌟 上値余地（★マーク）
    **「上値の需給の壁までどれくらい上昇する余地があるか」**を示します. 星が多いほど邪魔者がおらずスルスル上がりやすい「お宝状態」です.
    
    #### ③ 🚧 安全性（底値乖離）
    **「直近の底値（過去20営業日・約1ヶ月の最安値）から何%離れているか」**を示します. 20%を超えると「過熱圏」として高値掴みのリスクが高まります.
    
    #### ④ 📊 チャート ＆ 価格帯別出来高（右側の横棒）
    チャートの右側は、**過去半年間で「どの価格帯でどれだけ取引されたか」**を表します. 一番棒が長いオレンジの点線が**『強力な岩盤（需給の壁）』**です.
    <span style='color: #ffaa00; font-weight: bold;'>⚠️注意: オレンジの線を下回った場合は、含み損を抱えた投資家の「パニック売り（投げ売り）」が出やすくなるため、割ってはならない『下値支持線』としての目安にもなります。</span>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 複数銘柄一括診断", "🦅 全市場スキャン"])

with tab1:
    st.markdown("##### 気になる銘柄を入力（スペース区切りで複数可）")
    with st.form(key='search_form'):
        input_code = st.text_area("銘柄コード", height=68, placeholder="例: 7011 7203 9984")
        search_btn = st.form_submit_button("🦅 ハゲタカAIで診断する")

    if search_btn and input_code:
        codes = normalize_input(input_code)
        if not codes: st.error("銘柄コードを入力してください")
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
                                st.markdown(f"<h2 style='margin-bottom: 0px;'>{data['icons_str']} {data['コード']} {data['銘柄名']}</h2>", unsafe_allow_html=True)
                                
                                base_rank = data['ランク']
                                warning = data['警告']
                                rank_color = "red" if base_rank == "S" else "orange" if base_rank == "A" else "blue"
                                
                                if warning:
                                    rank_html = f"<h3 style='color:{rank_color}; margin-top: 5px;'>総合判定: {base_rank} <span style='color:#ff4b4b; font-size:0.8em;'>{warning}</span></h3>"
                                else:
                                    rank_html = f"<h3 style='color:{rank_color}; margin-top: 5px;'>総合判定: {base_rank}</h3>"
                                
                                st.markdown(rank_html, unsafe_allow_html=True)
                                
                                with st.expander("💡 総合判定の基準を見る"):
                                    st.markdown("""
                                    * **【Sランク】** 大口介入度80%以上 ＋ お得度(上昇余地)30%以上
                                    * **【Aランク】** 大口介入度60%以上（資金流入のサイン点灯）
                                    * **【Bランク】** プラチナサイズ(500〜2000億) ＋ 底値圏で煮詰まり
                                    * **【Cランク】** 上記以外の標準的な状態
                                    * **【注意】** 底値乖離が20%を超えている場合、安全面のアラートが表示されます
                                    """)

                                st.write(f"現在値: **{data['現在値']}** 円")
                                st.write(f"時価総額: **{data['時価総額_表示']}**")
                                st.write(f"配当情報: **{data['dividend_text']}**")
                                
                                st.markdown("---")
                                st.markdown(f"### {data['intervention_name']}: {data['intervention_score']}%")
                                st.progress(data['intervention_score'] / 100.0)
                                st.markdown(f"**{data['intervention_comment']}**")
                                
                            with c2:
                                st.markdown("##### 📋 AI診断カルテ")
                                
                                st.markdown(f"#### {data['star_rating']} {data['star_desc']}")
                                
                                st.markdown(f"""
                                <div style="background-color: rgba(75, 139, 255, 0.08); padding: 15px; border-left: 5px solid #4b8bff; border-radius: 5px; margin-bottom: 15px; font-size: 0.95rem; line-height: 1.6;">
                                {data['star_logic']}
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.markdown("---")
                                
                                st.markdown(f"<h3 style='font-size: 1.2rem; font-weight: bold;'>🛡️ 安全性（高値掴みリスク）: {data['乖離率']:.1f}%</h3>", unsafe_allow_html=True)
                                st.markdown(f"<div style='color: red; background-color: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 5px;'><strong>💡 AI解説:</strong> {data['safe_explain']}</div>", unsafe_allow_html=True)
                                st.markdown(f"**（判定: {data['safe_judgment']}）**")
                                
                                with st.expander("💡 安全性（底値乖離）の見方を見る"):
                                    safe_explain_html = f"""
                                    <div style='color: white; font-size: 0.95rem; line-height: 1.6;'>
                                    当ツールでは、源太流の月足ベースの「煮詰まり」を判定するため、<strong>過去20営業日（約1ヶ月）の最安値</strong>を「直近の底値（チャート上の青い点線）」と定義しています。<br>
                                    この底値から今の株価がどれだけ離れているか（乖離率%）を見て、高値掴みのリスクを判定します。<br><br>
                                    <span style='color: #ffaa00; font-weight: bold;'>【⚠️警告】需給の壁（オレンジの線）を下回った場合は、含み損を抱えた投資家の「投げ売り（パニック売り）」が出やすくなります。この線は『割ってはならない下値支持線（最終防衛ライン）』としての目安にもなります。</span><br><br>
                                    <strong>【AIの判定基準一覧】</strong><br>
                                    ・<strong>3.0%以内 【★ 絶好】</strong> 底値煮詰まり完了の可能性<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>直近最安値からほぼ無乖離です。反発に向けてエネルギーが溜まっていると推測されます。</span><br>
                                    ・<strong>5.0%以内 【★ 有望】</strong> 勝負しやすいエントリー位置<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>底値からの誤差範囲内であり、資金流入が始まれば上値を追いやすい状態と言えます。</span><br>
                                    ・<strong>10.0%以内 【✓ 及第点】</strong> トレンド発生の兆候あり<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>月足目線の調整を終え、再度上を目指す展開が期待できる状態です。</span><br>
                                    ・<strong>15.0%以内 【✓ 短期なら】</strong> スピード勝負の領域<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>トレンドは発生中ですが、ここからは短期目線での対応が求められます。深追いには注意が必要です。</span><br>
                                    ・<strong>20.0%以内 【⚠️ 限界範囲】</strong> 高値掴みに注意<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>当ツールが一般的な勝負圏内と判断する目安の限界です。これ以上の価格追いはリスクが高まる傾向にあります。</span><br>
                                    ・<strong>30.0%以内 【❌ 警戒】</strong> 短期的な過熱感あり<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>すでに大きく動いており、大口の利益確定売りに押されるリスクが高まっています.</span><br>
                                    ・<strong>30.1%以上 【💀 高度な警戒】</strong> 上級者向けの過熱圏<br>
                                    　<span style='color: #dddddd; font-size: 0.85rem;'>短期的な高値掴みとなる可能性が高い水準です。新規参戦は極めて慎重に行う必要があり、上級者向けのタイミングと言えます.</span>
                                    </div>
                                    """
                                    st.markdown(safe_explain_html, unsafe_allow_html=True)

                            draw_chart(data)
                    else: st.error(f"❌ {code}: データ取得エラー")

with tab2:
    st.markdown("##### ハゲタカが潜む銘柄を自動抽出します")
    
    st.markdown("""
    <div style='display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;'>
        <div style='background-color: rgba(0, 150, 255, 0.1); padding: 5px 10px; border-radius: 15px; font-size: 0.85rem;'>💎 プラチナ (黄金サイズ)</div>
        <div style='background-color: rgba(255, 100, 0, 0.1); padding: 5px 10px; border-radius: 15px; font-size: 0.85rem;'>🦅 ハゲタカ参戦？ (仕込み疑惑)</div>
        <div style='background-color: rgba(100, 255, 0, 0.1); padding: 5px 10px; border-radius: 15px; font-size: 0.85rem;'>🧬 DNA (習性) (過去の急騰)</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 スキャン開始", key="scan_btn"):
        st.warning("スキャン中です... ブラウザを閉じないでください...")
        target_codes = [c for c in jpx_codes if c != "4052"]
        if not target_codes: st.error("銘柄リストの取得に失敗しました。時間をおいて再度お試しください。")
        else:
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            total = len(target_codes)
            for i, code in enumerate(target_codes):
                status_text.text(f"スキャン中... {i+1} / {total} 銘柄完了")
                data = evaluate_stock(f"{code}.T", mode="scan")
                if data: results.append(data)
                progress_bar.progress((i + 1) / total)
            status_text.text(f"スキャン完了！ 有望な {len(results)} 銘柄を発見しました。")
            
            if results:
                df = pd.DataFrame(results)
                rank_map = {"S": 5, "A": 4, "B": 3, "C": 1}
                df['score'] = df['ランク'].map(rank_map).fillna(0)
                df = df.sort_values(by=['score', 'intervention_score'], ascending=[False, False])
                for index, row in df.iterrows():
                    warning_display = f" <span style='color:#ff4b4b; font-size:0.9em;'>{row['警告']}</span>" if row['警告'] else ""
                    with st.expander(f"【{row['ランク']}】{row['icons_str']} {row['コード']} {row['銘柄名']} | {row['intervention_name']}: {row['intervention_score']}%", expanded=False):
                        st.markdown(f"**時価総額:** {row['時価総額_表示']} | **配当:** {row['dividend_text']} | {row['safe_judgment']}{warning_display}", unsafe_allow_html=True)
                        draw_chart(row)
            else: st.warning("条件に合致するお宝銘柄は発見されませんでした。")
