import streamlit as st
import random
import pandas as pd
import time

# 画面設定
st.set_page_config(page_title="完全動作版・席替えアプリ", layout="wide")

# --- 演出用CSSインジェクション ---
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #00ff7f !important;
        color: #111 !important;
        font-weight: bold !important;
        border: none;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #cd5c5c !important;
        color: white !important;
        border: none;
    }
    
    .classroom-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 12px;
        margin-top: 15px;
    }
    .seat-box {
        background-color: #f8fafc;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        padding: 15px 5px;
        text-align: center;
        font-weight: bold;
        min-height: 75px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .seat-disabled {
        background-color: #f1f5f9;
        border: 2px dashed #cbd5e1;
        color: #94a3b8;
    }

    .roulette-container {
        background: linear-gradient(135deg, #1e3a8a, #0d9488);
        border-radius: 15px;
        padding: 40px;
        text-align: center;
        color: white;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        margin-bottom: 20px;
        border: 3px solid #ffd700;
    }
    .roulette-target-seat {
        font-size: 24px;
        font-weight: bold;
        color: #ffd700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        margin-bottom: 10px;
    }
    .roulette-big-name {
        font-size: 72px; 
        font-weight: 900;
        letter-spacing: 2px;
        text-shadow: 0 4px 10px rgba(0,0,0,0.7);
        margin: 20px 0;
        min-height: 108px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .roulette-spinning {
        animation: shake 0.1s infinite alternate;
        color: #ffff00;
    }
    @keyframes shake {
        0% { transform: translate(1px, 1px) rotate(0deg); }
        100% { transform: translate(-1px, -2px) rotate(0.5deg); }
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎰 BIGルーレット式 席替えエンタメシステム")

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
tab_setup, tab_csv, tab_run = st.tabs(["🪑 座席レイアウト設定", "📊 名簿CSV読込・調整", "🎲 ルーレット席替え"])

# --- タブ1：座席レイアウト設定 ---
with tab_setup:
    st.subheader("座席の配置設定")
    st.markdown("<div style='text-align:center; background:#1e293b; color:white; padding:12px; border-radius:5px; margin-bottom:20px; font-weight:bold;'>【 教 壇 】</div>", unsafe_allow_html=True)
    for r in range(7):
        cols = st.columns(6)
        for c in range(6):
            active = st.session_state.seat_map[r][c]
            b_type = "primary" if active else "secondary"
            b_label = f"座席 ({r+1}-{c+1})" if active else f"×"
            if cols[c].button(b_label, key=f"s_{r}_{c}", type=b_type, use_container_width=True):
                st.session_state.seat_map[r][c] = not active
                st.rerun()

# --- タブ2：CSVファイル読み込み・編集タブ ---
with tab_csv:
    st.subheader("名簿データのインポート")
    uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type=["csv"])
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
        st.info("💡 必要があれば、その場で点数をダブルクリックして書き換えられます。")
        st.session_state.final_df = st.data_editor(st.session_state.final_df, disabled=["出席番号"], hide_index=True, use_container_width=True)

# --- タブ3：ルーレット実行タブ ---
with tab_run:
    if st.session_state.final_df is None:
        st.error("先に『📊 名簿CSV読込・調整』タブで名簿データを読み込んでください。")
    else:
        active_coords = [(r, c) for r in range(7) for c in range(6) if st.session_state.seat_map[r][c]]
        df = st.session_state.final_df
        limit_count = min(len(active_coords), len(df))
        
        st.sidebar.header("ルーレット設定")
        num_students = st.sidebar.number_input("参加人数", 1, limit_count, limit_count)
        speed = st.sidebar.slider("ルーレットの回転速度（秒）", 0.05, 0.3, 0.08, step=0.01)
        
        # 画面構築用のプレースホルダー
        roulette_placeholder = st.empty()
        skip_btn_placeholder = st.empty()
        st.markdown("<div style='text-align:center; background:#1e293b; color:white; padding:10px; border-radius:5px; font-weight:bold;'>【 教 壇 】</div>", unsafe_allow_html=True)
        grid_placeholder = st.empty()
        
        # 座席グリッドの描画関数
        def draw_current_grid():
            html = "<div class='classroom-grid'>"
            for r in range(7):
                for c in range(6):
                    if st.session_state.seat_map[r][c]:
                        if (r, c) in st.session_state.confirmed_seats:
                            name = st.session_state.confirmed_seats[(r, c)]["name"]
                            score = st.session_state.confirmed_seats[(r, c)]["score"]
                            hue = 120 + int((score / 100) * 90) if score is not None else 210
                            html += f"<div class='seat-box' style='background-color: hsl({hue}, 80%, 90%); border: 2px solid hsl({hue}, 60%, 70%);'>{name}<br><span style='font-size:11px; color:#64748b;'>{score}点</span></div>"
                        else:
                            html += "<div class='seat-box' style='color:#94a3b8;'>🪑 空席</div>"
                    else:
                        html += "<div class='seat-box seat-disabled'>✖ 通路</div>"
            html += "</div>"
            grid_placeholder.html(html)

        # 常時、最新の座席状態を描画
        draw_current_grid()
        
        # 状態に応じた初期表示
        if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container'>
                    <div class='roulette-target-seat'>🎰 READY</div>
                    <div class='roulette-big-name' style='color: #94a3b8;'>サイドバーからルーレットを開始してください</div>
                </div>
            """)
        elif not st.session_state.roulette_running and st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container' style='background: #1e293b; border-color: #cbd5e1;'>
                    <div class='roulette-target-seat' style='color: #94a3b8;'>🎉 COMPLETE</div>
                    <div class='roulette-big-name' style='color: #ffffff; font-size: 54px;'>席替えが完了しました！</div>
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

        # ルーレット開始
        if st.sidebar.button("🎰 ルーレットスタート！", type="primary", use_container_width=True):
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
                
                skip_btn_placeholder.button("⚡ 演出をスキップして一気に完成させる", key=f"sk_{idx}", on_click=trigger_skip, use_container_width=True)
                
                for tick in range(12):
                    if not st.session_state.roulette_running:
                        break
                    dummy_name = random.choice(names_pool)
                    roulette_placeholder.html(f"""
                        <div class='roulette-container'>
                            <div class='roulette-target-seat'>🎯 第 {idx+1} 席 抽選中... 【 {r+1}列目 - {c+1}番 】</div>
                            <div class='roulette-big-name roulette-spinning'>{dummy_name}</div>
                        </div>
                    """)
                    time.sleep(speed)
                
                if not st.session_state.roulette_running:
                    break
                    
                roulette_placeholder.html(f"""
                    <div class='roulette-container' style='background: linear-gradient(135deg, #15803d, #166534); border-color: #00ff7f;'>
                        <div class='roulette-target-seat' style='color: #ffffff;'>✨ 第 {idx+1} 席 確定！ 【 {r+1}列目 - {c+1}番 】</div>
                        <div class='roulette-big-name' style='color: #00ff7f; font-size: 84px;'>👑 {winner}</div>
                    </div>
                """)
                
                st.session_state.confirmed_seats[(r, c)] = {"name": winner, "score": score_map[winner]}
                draw_current_grid()
                names_pool.remove(winner)
                time.sleep(0.5)

            st.session_state.roulette_running = False
            skip_btn_placeholder.empty()
            st.rerun()
