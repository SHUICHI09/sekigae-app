import streamlit as st
import random
import pandas as pd
import time

st.set_page_config(page_title="席替えアプリ", layout="wide")

# --- Session State の初期化 ---
if 'seat_map' not in st.session_state:
    st.session_state.seat_map = [[True for _ in range(6)] for _ in range(7)]
if 'final_df' not in st.session_state:
    st.session_state.final_df = None
if 'confirmed_seats' not in st.session_state:
    st.session_state.confirmed_seats = {}
if 'roulette_running' not in st.session_state:
    st.session_state.roulette_running = False

# --- 🛠️ サイドバー完全封鎖CSS ---
if st.session_state.roulette_running or st.session_state.confirmed_seats:
    sidebar_style = """
    <style>
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0px !important;
        min-width: 0px !important;
        max-width: 0px !important;
    }
    button[aria-label="Expand sidebar"] {
        display: none !important;
    }
    .stApp {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    </style>
    """
else:
    sidebar_style = """
    <style>
    .stApp {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] {
        min-width: 180px !important;
        max-width: 240px !important;
    }
    </style>
    """

st.markdown(sidebar_style, unsafe_allow_html=True)

# 共通パーツCSS（CSVアップローダー巨大化設定を追加）
st.markdown("""
    <style>
    button[data-baseweb="tab"] {
        color: #64748b !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0284c7 !important;
        border-bottom-color: #0284c7 !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 20px !important;
        border: 2px solid #10b981 !important;
        border-radius: 8px;
        padding: 10px 20px !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #ef4444 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: 2px solid #ef4444 !important;
        border-radius: 8px;
    }
    .classroom-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 16px;
        margin-top: 20px;
    }
    .seat-box {
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }
    .roulette-container {
        background: linear-gradient(135deg, #f0fdf4, #e0f2fe);
        border-radius: 16px;
        padding: 50px 20px;
        text-align: center;
        color: #0f172a;
        box-shadow: 0 10px 25px rgba(2, 132, 199, 0.15);
        margin-bottom: 25px;
        border: 4px solid #0284c7;
    }
    .roulette-target-seat {
        font-size: 26px;
        font-weight: 800;
        color: #0284c7;
        margin-bottom: 15px;
    }
    .roulette-big-name {
        font-size: 80px;
        font-weight: 900;
        margin: 10px 0;
        min-height: 120px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .roulette-spinning {
        animation: neon-pulse 0.1s infinite alternate;
        color: #b45309;
    }
    @keyframes neon-pulse {
        0% { transform: scale(0.98); }
        100% { transform: scale(1.02); }
    }
    
    /* 💡 CSVアップローダーの巨大化CSS */
    div[data-testid="stFileUploader"] {
        padding: 20px 0;
    }
    div[data-testid="stFileUploaderDropzone"] {
        padding: 40px 20px !important;
        border: 3px dashed #0284c7 !important;
        background-color: #f0f9ff !important;
        border-radius: 16px !important;
    }
    div[data-testid="stFileUploaderDropzone"] button {
        font-size: 20px !important;
        padding: 12px 24px !important;
        background-color: #0284c7 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
    }
    div[data-testid="stFileUploaderDropzone"] button:hover {
        background-color: #0369a1 !important;
    }
    /* ドラッグ＆ドロップの案内テキスト（大文字化） */
    div[data-testid="stFileUploaderDropzone"] data {
        font-size: 18px !important;
        color: #334155 !important;
        font-weight: bold !important;
    }
    /* 小さな制限事項テキスト（200MB制限など）を消すか大きくする */
    div[data-testid="stFileUploaderDropzone"] small {
        font-size: 14px !important;
        color: #64748b !important;
    }
    </style>
""", unsafe_allow_html=True)

def get_seat_label(r, c):
    display_col = 6 - c
    display_num = r + 1
    return display_col, display_num

main_container = st.container()

with main_container:
    if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
        tab_setup, tab_csv, tab_run = st.tabs(["1. 座席の形を決める", "2. 名簿を読み込む", "3. ルーレットを回す"])
    else:
        tab_run = st.container()

    # --- タブ1：座席レイアウト設定 ---
    if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
        with tab_setup:
            st.subheader("使用する座席をタップして指定してください")
            st.markdown("<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:15px; border-radius:8px; margin-bottom:25px; font-weight:bold; font-size:20px; border: 2px solid #0284c7;'>【教卓】（こちらが前方です）</div>", unsafe_allow_html=True)
            for r in range(7):
                cols = st.columns(6)
                for c in range(6):
                    active = st.session_state.seat_map[r][c]
                    b_type = "primary" if active else "secondary"
                    disp_col, disp_num = get_seat_label(r, c)
                    b_label = f"座席 ({disp_col}-{disp_num})" if active else f"通路"
                    if cols[c].button(b_label, key=f"s_{r}_{c}", type=b_type, use_container_width=True):
                        st.session_state.seat_map[r][c] = not active
                        st.rerun()

    # --- タブ2：CSVファイル読み込み（巨大化適用） ---
    if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
        with tab_csv:
            st.subheader("名簿CSVデータのインポート")
            uploaded_file = st.file_uploader("ここにCSVファイルをドラッグ＆ドロップするか、ボタンから選択してください", type=["csv"])
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
                st.success("名簿の読み込みに成功しました。")
                st.session_state.final_df = st.data_editor(st.session_state.final_df, disabled=["出席番号"], hide_index=True, use_container_width=True)

    # --- タブ3：ルーレット実行タブ ---
    with tab_run:
        if st.session_state.final_df is None:
            st.error("先に『2. 名簿を読み込む』タブで名簿データを準備してください。")
        else:
            active_coords = []
            for c in reversed(range(6)):
                for r in range(7):
                    if st.session_state.seat_map[r][c]:
                        active_coords.append((r, c))
                        
            df = st.session_state.final_df
            limit_count = min(len(active_coords), len(df))
            
            if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
                st.sidebar.header("各種調整")
                num_students = st.sidebar.number_input("参加人数", 1, limit_count, limit_count)
                speed = st.sidebar.slider("シャッフル速度（秒）", 0.04, 0.2, 0.06, step=0.01)
                st.session_state.saved_num_students = num_students
                st.session_state.saved_speed = speed
            else:
                num_students = st.session_state.saved_num_students
                speed = st.session_state.saved_speed
            
            start_btn_placeholder = st.empty()
            roulette_placeholder = st.empty()
            skip_btn_placeholder = st.empty()
            
            reset_ui_placeholder = st.container()
            grid_area_placeholder = st.empty()
            
            def draw_current_grid():
                html = "<div style='padding:20px; background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; width:100%;'>"
                html += "<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:12px; border-radius:8px; font-weight:bold; font-size:18px; border: 1px solid #e2e8f0; margin-bottom:15px;'>【教卓】</div>"
                html += "<div class='classroom-grid'>"
                for r in range(7):
                    for c in range(6):
                        if st.session_state.seat_map[r][c]:
                            if (r, c) in st.session_state.confirmed_seats:
                                name = st.session_state.confirmed_seats[(r, c)]["name"]
                                num = st.session_state.confirmed_seats[(r, c)]["num"]
                                prob = st.session_state.confirmed_seats[(r, c)]["prob"]
                                html += f"<div class='seat-box' style='background-color: #e0f2fe; color: #0369a1; border: 2px solid #0ea5e9;'><span style='font-size:13px; font-weight:bold; color: #0284c7; margin-bottom:2px;'>{num}番</span>{name}<span style='font-size:12px; color:#0284c7; font-weight:normal; margin-top:4px; background:#ffffff; padding:1px 8px; border-radius:20px; border:1px solid #bdf0ff;'>確率: {prob}%</span></div>"
                            else:
                                html += "<div class='seat-box' style='background-color: #f8fafc; border: 2px dashed #cbd5e1; color: #64748b;'>空席</div>"
                        else:
                            html += "<div class='seat-box' style='background-color: #ffffff; border: 2px solid #f1f5f9; color: #cbd5e1; box-shadow:none; min-height:110px;'>通路</div>"
                html += "</div></div>"
                grid_area_placeholder.html(html)

            draw_current_grid()
            
            if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
                roulette_placeholder.html("<div class='roulette-container'><div class='roulette-target-seat'>READY</div><div class='roulette-big-name' style='color: #94a3b8; font-size: 45px;'>「ルーレットを開始する」ボタンを押してください</div></div>")
            elif not st.session_state.roulette_running and st.session_state.confirmed_seats:
                roulette_placeholder.html("<div class='roulette-container' style='background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-color: #10b981;'><div class='roulette-target-seat' style='color: #10b981;'>COMPLETE</div><div class='roulette-big-name' style='color: #14532d; font-size: 54px;'>席替え完了</div></div>")
                
                with reset_ui_placeholder:
                    if st.button("🔄 もう一度最初からやり直す", use_container_width=True):
                        st.session_state.confirmed_seats = {}
                        st.session_state.roulette_running = False
                        st.rerun()

            def calculate_weights_and_probs_base40(names_list, full_initial_list, score_map, disp_num):
                all_scores = list(score_map.values())
                max_score = max(all_scores) if all_scores else 100
                min_score = min(all_scores) if all_scores else 0
                score_range = max(1, max_score - min_score)
                
                full_weights = []
                for name in full_initial_list:
                    student_score = float(score_map[name])
                    norm_score = (student_score - min_score) / score_range
                    seat_ratio = (disp_num - 1) / 6.0
                    match_factor = (seat_ratio * norm_score) + ((1.0 - seat_ratio) * (1.0 - norm_score))
                    full_weights.append(max(0.05, match_factor))
                
                total_full_w = sum(full_weights) if sum(full_weights) > 0 else 1.0
                
                prob_map = {}
                for idx, name in enumerate(full_initial_list):
                    prob_map[name] = round((full_weights[idx] / total_full_w) * 100, 1)
                
                current_weights = []
                for name in names_list:
                    student_score = float(score_map[name])
                    norm_score = (student_score - min_score) / score_range
                    seat_ratio = (disp_num - 1) / 6.0
                    match_factor = (seat_ratio * norm_score) + ((1.0 - seat_ratio) * (1.0 - norm_score))
                    current_weights.append(max(0.05, match_factor))
                    
                return current_weights, prob_map

            def trigger_skip():
                if st.session_state.roulette_running:
                    current_pool = df.head(num_students).copy()
                    full_initial_list = current_pool["名前"].tolist()
                    names_pool = full_initial_list.copy()
                    num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
                    score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}
                    
                    already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                    for name in already_chosen:
                        if name in names_pool:
                            names_pool.remove(name)
                    
                    for (r, c) in active_coords:
                        if (r, c) in st.session_state.confirmed_seats:
                            continue
                        if not names_pool:
                            break
                        
                        _, disp_num = get_seat_label(r, c)
                        weights, prob_map = calculate_weights_and_probs_base40(names_pool, full_initial_list, score_map, disp_num)
                        
                        winner = random.choices(names_pool, weights=weights, k=1)[0]
                        st.session_state.confirmed_seats[(r, c)] = {
                            "name": winner, 
                            "num": num_map[winner],
                            "prob": prob_map[winner]
                        }
                        names_pool.remove(winner)
                    st.session_state.roulette_running = False

            if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
                if start_btn_placeholder.button("ルーレットを開始する", type="primary", use_container_width=True):
                    st.session_state.confirmed_seats = {}
                    st.session_state.roulette_running = True
                    st.rerun()

        # --- ルーレットアニメーション処理 ---
        if st.session_state.final_df is not None and st.session_state.roulette_running:
            current_pool = df.head(num_students).copy()
            full_initial_list = current_pool["名前"].tolist()
            names_pool = full_initial_list.copy()
            num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
            score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}

            for idx, (r, c) in enumerate(active_coords):
                if not st.session_state.roulette_running or not names_pool:
                    break
                
                disp_col, disp_num = get_seat_label(r, c)
                weights, prob_map = calculate_weights_and_probs_base40(names_pool, full_initial_list, score_map, disp_num)
                
                winner = random.choices(names_pool, weights=weights, k=1)[0]
                winner_prob = prob_map[winner]
                
                skip_btn_placeholder.button("演出をスキップして一瞬で結果を見る", key=f"sk_{idx}", on_click=trigger_skip, use_container_width=True)
                
                for tick in range(12):
                    if not st.session_state.roulette_running:
                        break
                    dummy_name = random.choice(names_pool)
                    roulette_placeholder.html(f"<div class='roulette-container'><div class='roulette-target-seat'>【 {disp_col}列目 - {disp_num}番 】の抽選中...</div><div class='roulette-big-name roulette-spinning'>{dummy_name}</div></div>")
                    time.sleep(speed)
                
                if not st.session_state.roulette_running:
                    break
                
                roulette_placeholder.html(f"<div class='roulette-container' style='background: linear-gradient(135deg, #ecfdf5, #f0fdf4); border-color: #10b981;'><div class='roulette-target-seat' style='color: #10b981;'>【{disp_col}列-{disp_num}番】に {winner_prob}% の確率で当選！</div><div class='roulette-big-name' style='color: #10b981; font-size: 85px;'>{winner}</div></div>")
                
                st.session_state.confirmed_seats[(r, c)] = {
                    "name": winner, 
                    "num": num_map[winner],
                    "prob": winner_prob
                }
                draw_current_grid()
                names_pool.remove(winner)
                time.sleep(0.7)

            st.session_state.roulette_running = False
            skip_btn_placeholder.empty()
            st.rerun()
