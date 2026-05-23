import streamlit as st
import random
import pandas as pd
import time

# 画面設定
st.set_page_config(page_title="🎨 PREMIUM NEON - 席替えアプリ", layout="wide")

# --- 🧠 バリアフリー ＆ サイバーダークCSS ---
st.markdown("""
    <style>
    /* 全体の背景とテキスト色の変更 */
    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }
    
    /* タブの見た目をダークモードに最適化 */
    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom-color: #38bdf8 !important;
    }

    /* ボタンのカスタマイズ（直感的な記号と高コントラスト） */
    div.stButton > button[kind="primary"] {
        background-color: #00e676 !important; /* 鮮やかなユニバーサルグリーン */
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: 2px solid #00e676 !important;
        border-radius: 8px;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #ff3d00 !important; /* 識別しやすいビビッドレッド */
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: 2px solid #ff3d00 !important;
        border-radius: 8px;
    }
    
    /* 教室のグリッド表示 */
    .classroom-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 16px;
        margin-top: 20px;
    }
    
    /* 座席ボックスの基本（文字を大きく、認識しやすく） */
    .seat-box {
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px; /* 遠くからでも見える大きさ */
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        transition: all 0.2s;
    }
    
    /* 🔥 演出：超巨大ルーレット画面（ネオンサイバーテイスト） */
    .roulette-container {
        background: linear-gradient(135deg, #111827, #1e1b4b);
        border-radius: 16px;
        padding: 50px 20px;
        text-align: center;
        color: #ffffff;
        box-shadow: 0 0 30px rgba(56, 189, 248, 0.2);
        margin-bottom: 25px;
        border: 4px solid #38bdf8; /* ネオンブルーの枠線 */
    }
    .roulette-target-seat {
        font-size: 26px;
        font-weight: 800;
        color: #38bdf8;
        letter-spacing: 1px;
        margin-bottom: 15px;
    }
    .roulette-big-name {
        font-size: 80px; /* 圧倒的視認性 */
        font-weight: 900;
        letter-spacing: 4px;
        text-shadow: 0 0 20px rgba(255, 255, 255, 0.6);
        margin: 20px 0;
        min-height: 120px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .roulette-spinning {
        animation: neon-pulse 0.1s infinite alternate;
        color: #ccff00; /* 目立つ蛍光イエローグリーン */
    }
    @keyframes neon-pulse {
        0% { transform: scale(0.98); opacity: 0.9; }
        100% { transform: scale(1.02); opacity: 1; }
    }
    </style>
""", unsafe_allow_html=True)


# --- Session State の初期化 ---
if 'seat_map' not in st.session_state:
    st.session_state.seat_map = [[True for _ in range(6)] for _ in range(7)]
if 'final_df' not in st.session_state:
    st.session_state.final_df = None
if 'confirmed_seats' not in st.session_state:
    st.session_state.confirmed_seats = {}
if 'roulette_running' not in st.session_state:
    st.session_state.roulette_running = False

# タブ設定
tab_setup, tab_csv, tab_run = st.tabs(["🪑 ① 座席の形を決める", "📊 ② 名簿を読み込む", "🎲 ③ ルーレットを回す"])

# --- タブ1：座席レイアウト設定 ---
with tab_setup:
    st.subheader("使用する座席をタップして指定してください")
    st.write("※ 色覚に関わらず判別できるよう、文字（🟢/❌）を併記しています。")
    st.markdown("<div style='text-align:center; background:#1e293b; color:#38bdf8; padding:15px; border-radius:8px; margin-bottom:25px; font-weight:bold; font-size:20px; border: 2px solid #38bdf8;'>【 教 壇 】（こちらが前方です）</div>", unsafe_allow_html=True)
    
    for r in range(7):
        cols = st.columns(6)
        for c in range(6):
            active = st.session_state.seat_map[r][c]
            b_type = "primary" if active else "secondary"
            b_label = f"🟢 席 ({r+1}-{c+1})" if active else f"❌ 通路"
            if cols[c].button(b_label, key=f"s_{r}_{c}", type=b_type, use_container_width=True):
                st.session_state.seat_map[r][c] = not active
                st.rerun()

# --- タブ2：CSVファイル読み込み・編集タブ ---
with tab_csv:
    st.subheader("名簿CSVデータのインポート")
    uploaded_file = st.file_uploader("CSVファイルをここにドラッグ＆ドロップしてください", type=["csv"])
    if uploaded_file is not None:
        try:
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                df = pd.read_csv(uploaded_file, encoding='shift_jis')
            if all(col in df.columns for col in ["出席番号", "名前", "点数"]):
                st.session_state.final_df = df
            else:
                st.error("CSVに『出席番号』『名前』『点数』の列が必要です。")
        except Exception as e:
            st.error(f"エラー: {e}")

    if st.session_state.final_df is not None:
        st.success("名簿の読み込みに成功しました！")
        st.info("💡 数値を変更したい場合は、下の表のセルをダブルクリックして直接編集できます。")
        st.session_state.final_df = st.data_editor(st.session_state.final_df, disabled=["出席番号"], hide_index=True, use_container_width=True)

# --- タブ3：ルーレット実行タブ ---
with tab_run:
    if st.session_state.final_df is None:
        st.error("先に『📊 ② 名簿を読み込む』タブで名簿データを準備してください。")
    else:
        active_coords = [(r, c) for r in range(7) for c in range(6) if st.session_state.seat_map[r][c]]
        df = st.session_state.final_df
        limit_count = min(len(active_coords), len(df))
        
        st.sidebar.header("各種調整")
        num_students = st.sidebar.number_input("参加人数", 1, limit_count, limit_count)
        speed = st.sidebar.slider("シャッフル速度（秒）", 0.04, 0.2, 0.06, step=0.01)
        
        # 画面構築プレースホルダー
        roulette_placeholder = st.empty()
        skip_btn_placeholder = st.empty()
        st.markdown("<div style='text-align:center; background:#1e293b; color:#38bdf8; padding:12px; border-radius:8px; font-weight:bold; font-size:18px; border: 1px solid #38bdf8;'>【 教 壇 】</div>", unsafe_allow_html=True)
        grid_placeholder = st.empty()
        
        # 座席グリッドの描画（アクセシビリティ対応デザイン）
        def draw_current_grid():
            html = "<div class='classroom-grid'>"
            for r in range(7):
                for c in range(6):
                    if st.session_state.seat_map[r][c]:
                        if (r, c) in st.session_state.confirmed_seats:
                            name = st.session_state.confirmed_seats[(r, c)]["name"]
                            score = st.session_state.confirmed_seats[(r, c)]["score"]
                            
                            # 視認性の高いシアン（青緑系）のグラデーション
                            # 高得点ほど濃いシアン、低得点ほど明るいネオンシアン（白文字が見えやすいように調整）
                            lightness = 85 - int((score / 100) * 45) 
                            text_color = "#000000" if lightness > 50 else "#ffffff"
                            
                            html += f"<div class='seat-box' style='background-color: hsl(190, 90%, {lightness}%); color: {text_color}; border: 2px solid #38bdf8;'>👤 {name}<br><span style='font-size:12px; font-weight:bold; opacity:0.8;'>{score}点</span></div>"
                        else:
                            html += "<div class='seat-box' style='background-color: #1e293b; border: 2px dashed #475569; color: #94a3b8;'>🪑 空席</div>"
                    else:
                        html += "<div class='seat-box' style='background-color: #0f172a; border: 2px solid #1e293b; color: #475569; box-shadow:none;'>× 通路</div>"
            html += "</div>"
            grid_placeholder.html(html)

        draw_current_grid()
        
        # 初期状態のルーレット画面
        if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container'>
                    <div class='roulette-target-seat'>🎰 READY</div>
                    <div class='roulette-big-name' style='color: #475569; font-size: 45px;'>左メニューからスタートしてください</div>
                </div>
            """)
        elif not st.session_state.roulette_running and st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container' style='background: linear-gradient(135deg, #064e3b, #111827); border-color: #00e676;'>
                    <div class='roulette-target-seat' style='color: #00e676;'>🎉 COMPLETE</div>
                    <div class='roulette-big-name' style='color: #ffffff; font-size: 54px;'>✨ 席替え完了 ✨</div>
                </div>
            """)

        # スキップ処理
        def trigger_skip():
            if st.session_state.roulette_running:
                current_pool = df.head(num_students).copy()
                names_pool = current_pool["名前"].tolist()
                scores_pool = current_pool["点数"].tolist()
                score_map = {n: s for n, s in zip(names_pool, scores_pool)}
                
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                for name in already_chosen:
                    if name in names_pool:
                        names_pool.remove(name)
                
                for (r, c) in active_coords:
                    if (r, c) in st.session_state.confirmed_seats:
                        continue
                    if not names_pool:
                        break
                    
                    current_scores = [score_map[n] for n in names_pool]
                    max_score = max(current_scores) if current_scores else 100
                    weights = [(max_score + 1) - s for s in current_scores]
                    weights = [max(0.1, float(w)) for w in weights]
                    
                    winner = random.choices(names_pool, weights=weights, k=1)[0]
                    st.session_state.confirmed_seats[(r, c)] = {"name": winner, "score": score_map[winner]}
                    names_pool.remove(winner)
                
                st.session_state.roulette_running = False

        # ルーレット実行
        if st.sidebar.button("⚡ ルーレットを開始する", type="primary", use_container_width=True):
            st.session_state.confirmed_seats = {}
            st.session_state.roulette_running = True
            
            current_pool = df.head(num_students).copy()
            names_pool = current_pool["名前"].tolist()
            scores_pool = current_pool["点数"].tolist()
            score_map = {n: s for n, s in zip(names_pool, scores_pool)}

            for idx, (r, c) in enumerate(active_coords):
                if not st.session_state.roulette_running:
                    break
                if not names_pool:
                    break
                
                current_scores = [score_map[n] for n in names_pool]
                max_score = max(current_scores) if current_scores else 100
                weights = [(max_score + 1) - s for s in current_scores]
                weights = [max(0.1, float(w)) for w in weights]
                
                winner = random.choices(names_pool, weights=weights, k=1)[0]
                
                skip_btn_placeholder.button("⏩ 演出をスキップして一瞬で結果を見る", key=f"sk_{idx}", on_click=trigger_skip, use_container_width=True)
                
                for tick in range(12):
                    if not st.session_state.roulette_running:
                        break
                    dummy_name = random.choice(names_pool)
                    roulette_placeholder.html(f"""
                        <div class='roulette-container'>
                            <div class='roulette-target-seat'>🎯 【 {r+1}列目 - {c+1}番 】の抽選中...</div>
                            <div class='roulette-big-name roulette-spinning'>{dummy_name}</div>
                        </div>
                    """)
                    time.sleep(speed)
                
                if not st.session_state.roulette_running:
                    break
                    
                roulette_placeholder.html(f"""
                    <div class='roulette-container' style='background: linear-gradient(135deg, #1e1b4b, #064e3b); border-color: #00e676;'>
                        <div class='roulette-target-seat' style='color: #00e676;'>✨ 確定しました！</div>
                        <div class='roulette-big-name' style='color: #00e676; font-size: 85px;'>👑 {winner}</div>
                    </div>
                """)
                
                st.session_state.confirmed_seats[(r, c)] = {"name": winner, "score": score_map[winner]}
                draw_current_grid()
                names_pool.remove(winner)
                time.sleep(0.5)

            st.session_state.roulette_running = False
            skip_btn_placeholder.empty()
            st.rerun()
