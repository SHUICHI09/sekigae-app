import streamlit as st
import random
import pandas as pd
import time

# 画面設定
st.set_page_config(page_title="PREMIUM LIGHT - 席替えアプリ", layout="wide", initial_sidebar_state="expanded")

# --- CSS ＆ JS（サイドバー制御・画像保存） ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { min-width: 180px !important; max-width: 240px !important; }
    
    /* ボタンデザイン */
    div.stButton > button[kind="primary"] {
        background-color: #10b981 !important; color: #ffffff !important;
        font-weight: 900 !important; font-size: 20px !important;
        border-radius: 8px; padding: 10px 20px !important; width: 100%;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #ef4444 !important; color: #ffffff !important;
        font-weight: 900 !important; font-size: 18px !important;
        border-radius: 8px; width: 100%;
    }
    
    .classroom-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; margin-top: 20px; }
    .seat-box {
        border-radius: 12px; padding: 20px 10px; text-align: center; font-weight: bold;
        font-size: 20px; min-height: 90px; display: flex; flex-direction: column;
        justify-content: center; align-items: center; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }
    .roulette-container {
        background: linear-gradient(135deg, #f0fdf4, #e0f2fe); border-radius: 16px;
        padding: 50px 20px; text-align: center; color: #0f172a;
        box-shadow: 0 10px 25px rgba(2, 132, 199, 0.15); margin-bottom: 25px; border: 4px solid #0284c7;
    }
    .roulette-target-seat { font-size: 26px; font-weight: 800; color: #0284c7; margin-bottom: 15px; }
    .roulette-big-name {
        font-size: 80px; font-weight: 900; margin: 20px 0; min-height: 120px;
        display: flex; justify-content: center; align-items: center;
    }
    .roulette-spinning { animation: shake 0.1s infinite alternate; color: #b45309; }
    @keyframes shake { 0% { transform: scale(0.98); } 100% { transform: scale(1.02); } }
    </style>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
    function downloadSeatMap() {
        var element = window.parent.document.getElementById("download-area");
        if (element) {
            html2canvas(element, { scale: 2, backgroundColor: "#ffffff" }).then(function(canvas) {
                var link = document.createElement("a");
                link.download = "席替え結果.png";
                link.href = canvas.toDataURL("image/png");
                link.click();
            });
        }
    }
    // サイドバーを強制的に閉じる関数
    function closeSidebar() {
        const sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (sidebar && sidebar.getAttribute('aria-expanded') === 'true') {
            const button = window.parent.document.querySelector('button[aria-label="Collapse sidebar"]');
            if (button) button.click();
        }
    }
    </script>
""", unsafe_allow_html=True)

# --- Session State 初期化 ---
if 'seat_map' not in st.session_state:
    st.session_state.seat_map = [[True for _ in range(6)] for _ in range(7)]
if 'confirmed_seats' not in st.session_state:
    st.session_state.confirmed_seats = {}
if 'roulette_running' not in st.session_state:
    st.session_state.roulette_running = False

# --- 進行管理（タブ移動対策） ---
# 実行中の場合は強制的に「3.ルーレット」の画面を表示し続ける
if st.session_state.roulette_running:
    current_tab_idx = 2
else:
    current_tab_idx = 0

# --- メインレイアウト ---
# ルーレット中はタブ自体を表示せず、完了後や設定中のみタブを表示
if not st.session_state.roulette_running:
    tabs = st.tabs(["1. 座席の形を決める", "2. 名簿を読み込む", "3. ルーレットを回す"])
    tab_setup, tab_csv, tab_run = tabs
else:
    # 実行中はタブの代わりに「実行中画面」のみを表示
    tab_run = st.container()
    tab_setup = st.container()
    tab_csv = st.container()

# --- 1. 座席の形を決める ---
if not st.session_state.roulette_running:
    with tab_setup:
        st.subheader("使用する座席を指定してください")
        st.markdown("<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:15px; border-radius:8px; margin-bottom:25px; font-weight:bold; font-size:20px; border: 2px solid #0284c7;'>【教卓】</div>", unsafe_allow_html=True)
        for r in range(7):
            cols = st.columns(6)
            for c in range(6):
                active = st.session_state.seat_map[r][c]
                label = f"座席 ({r+1}-{c+1})" if active else "通路"
                if cols[c].button(label, key=f"s_{r}_{c}", type="primary" if active else "secondary"):
                    st.session_state.seat_map[r][c] = not active
                    st.rerun()

# --- 2. 名簿を読み込む ---
if not st.session_state.roulette_running:
    with tab_csv:
        st.subheader("名簿CSVデータの読み込み")
        uploaded_file = st.file_uploader("CSVをアップロード", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except:
                df = pd.read_csv(uploaded_file, encoding='shift_jis')
            if all(col in df.columns for col in ["出席番号", "名前", "点数"]):
                st.session_state.final_df = df
                st.success("名簿を読み込みました。")
                st.data_editor(st.session_state.final_df, use_container_width=True, hide_index=True)
            else:
                st.error("出席番号、名前、点数の列が必要です。")

# --- 3. ルーレットを回す ---
with tab_run:
    if 'final_df' not in st.session_state:
        st.warning("先に名簿を読み込んでください。")
    else:
        active_coords = [(r, c) for r in range(7) for c in range(6) if st.session_state.seat_map[r][c]]
        df = st.session_state.final_df
        limit = min(len(active_coords), len(df))

        st.sidebar.header("調整")
        num_students = st.sidebar.number_input("参加人数", 1, limit, limit)
        speed = st.sidebar.slider("速度", 0.04, 0.2, 0.06)

        # プレースホルダー
        roulette_placeholder = st.empty()
        skip_btn_placeholder = st.empty()
        save_btn_placeholder = st.empty()
        grid_area = st.empty()

        def draw_grid():
            html = f"<div id='download-area' style='padding:20px; background:#ffffff;'>"
            html += f"<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:12px; border-radius:8px; font-weight:bold; font-size:18px; border: 1px solid #e2e8f0; margin-bottom:20px;'>【教卓】</div>"
            html += "<div class='classroom-grid'>"
            for r in range(7):
                for c in range(6):
                    if st.session_state.seat_map[r][c]:
                        if (r, c) in st.session_state.confirmed_seats:
                            s = st.session_state.confirmed_seats[(r, c)]
                            html += f"<div class='seat-box' style='background-color:#e0f2fe; color:#0369a1; border:2px solid #0ea5e9;'>{s['name']}<br><span style='font-size:12px; color:#64748b;'>{s['score']}点</span></div>"
                        else:
                            html += "<div class='seat-box' style='background-color:#f8fafc; border:2px dashed #cbd5e1; color:#64748b;'>空席</div>"
                    else:
                        html += "<div class='seat-box' style='background-color:#ffffff; border:1px solid #f1f5f9; color:#cbd5e1; box-shadow:none;'>通路</div>"
            html += "</div></div>"
            grid_area.html(html)

        draw_grid()

        if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
            roulette_placeholder.html("<div class='roulette-container'><div class='roulette-target-seat'>READY</div><div class='roulette-big-name' style='color:#94a3b8; font-size:40px;'>開始ボタンを押してください</div></div>")
            if st.button("ルーレットを開始する", type="primary"):
                st.session_state.confirmed_seats = {}
                st.session_state.roulette_running = True
                # JSでサイドバーを閉じる
                st.markdown("<script>closeSidebar();</script>", unsafe_allow_html=True)
                st.rerun()

        elif st.session_state.roulette_running:
            # 抽選ロジック
            names_pool = df.head(num_students)["名前"].tolist()
            score_map = {row["名前"]: row["点数"] for _, row in df.iterrows()}
            
            # スキップ用関数
            def do_skip():
                st.session_state.roulette_running = False

            for idx, (r, c) in enumerate(active_coords):
                if not st.session_state.roulette_running or not names_pool: break
                
                # 重み計算
                curr_scores = [score_map[n] for n in names_pool]
                weights = [(max(curr_scores)+1) - s for s in curr_scores]
                winner = random.choices(names_pool, weights=weights, k=1)[0]
                
                skip_btn_placeholder.button("演出をスキップして完了", key=f"skip_{idx}", on_click=do_skip)
                
                # アニメーション
                for _ in range(10):
                    if not st.session_state.roulette_running: break
                    roulette_placeholder.html(f"<div class='roulette-container'><div class='roulette-target-seat'>{r+1}列-{c+1}番 抽選中</div><div class='roulette-big-name roulette-spinning'>{random.choice(names_pool)}</div></div>")
                    time.sleep(speed)
                
                if not st.session_state.roulette_running: break
                
                # 確定
                roulette_placeholder.html(f"<div class='roulette-container' style='border-color:#10b981; background:#ecfdf5;'><div class='roulette-target-seat' style='color:#10b981;'>確定！</div><div class='roulette-big-name' style='color:#10b981;'>{winner}</div></div>")
                st.session_state.confirmed_seats[(r, c)] = {"name": winner, "score": score_map[winner]}
                names_pool.remove(winner)
                draw_grid()
                time.sleep(0.4)

            # 終了後
            st.session_state.roulette_running = False
            st.rerun()

        elif st.session_state.confirmed_seats:
            roulette_placeholder.html("<div class='roulette-container' style='background:#f0fdf4; border-color:#10b981;'><div class='roulette-target-seat' style='color:#10b981;'>COMPLETE</div><div class='roulette-big-name' style='color:#14532d; font-size:50px;'>席替え完了</div></div>")
            if st.button("📷 この座席表を画像として保存"):
                st.markdown("<script>downloadSeatMap();</script>", unsafe_allow_html=True)
