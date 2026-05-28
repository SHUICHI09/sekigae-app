import streamlit as st
import random
import pandas as pd
import time

# 画面設定
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
if 'shuffled_coords' not in st.session_state:
    st.session_state.shuffled_coords = []
if 'current_match_idx' not in st.session_state:
    st.session_state.current_match_idx = 0
if 'temp_display_names' not in st.session_state:
    st.session_state.temp_display_names = {}

# --- サイドバー表示制御CSS ---
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
    .stApp { background-color: #ffffff !important; color: #0f172a !important; }
    </style>
    """
else:
    sidebar_style = """
    <style>
    .stApp { background-color: #ffffff !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { min-width: 180px !important; max-width: 240px !important; }
    </style>
    """
st.markdown(sidebar_style, unsafe_allow_html=True)

# デザインCSS
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
        font-size: 16px !important;
        border: 2px solid #ef4444 !important;
        border-radius: 8px;
    }
    
    .classroom-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 15px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    .classroom-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 12px;
        margin-top: 15px;
    }
    .seat-box {
        border-radius: 10px;
        padding: 12px 6px;
        text-align: center;
        font-weight: bold;
        font-size: 16px;
        min-height: 85px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 3px 8px rgba(15, 23, 42, 0.05);
    }
    
    /* 💡 座席がシャッフル中（ルーレット状態）の時のアニメーション効果 */
    .seat-spinning {
        background-color: #fef3c7 !important;
        color: #d97706 !important;
        border: 2px solid #f59e0b !important;
        animation: seat-shake 0.15s infinite alternate;
    }
    @keyframes seat-shake {
        0% { transform: translateY(-1px) scale(0.99); }
        100% { transform: translateY(1px) scale(1.01); }
    }
    
    /* CSVアップローダー用 */
    div[data-testid="stFileUploaderDropzone"] {
        padding: 40px 20px !important;
        border: 3px dashed #0284c7 !important;
        background-color: #f0f9ff !important;
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
        tab_setup, tab_csv, tab_run = st.tabs(["1. 座席の数を決める", "2. 名簿を読み込む", "3. ルーレットを回す"])
    else:
        tab_run = st.container()

    # --- タブ1：座席レイアウト設定 ---
    if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
        with tab_setup:
            st.subheader("使用する座席をタップして指定してください")
            st.markdown("<div style='max-width:900px; margin:0 auto 15px auto; text-align:center; background:#f1f5f9; color:#0284c7; padding:10px; border-radius:8px; font-weight:bold; font-size:18px; border: 2px solid #0284c7;'>【教卓】（こちらが前方です）</div>", unsafe_allow_html=True)
            st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
            for r in range(7):
                cols = st.columns(6)
                for c in range(6):
                    active = st.session_state.seat_map[r][c]
                    b_type = "primary" if active else "secondary"
                    disp_col, disp_num = get_seat_label(r, c)
                    b_label = f"{disp_col}-{disp_num}" if active else f"空席"
                    if cols[c].button(b_label, key=f"s_{r}_{c}", type=b_type, use_container_width=True):
                        st.session_state.seat_map[r][c] = not active
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- タブ2：CSVファイル読み込み ---
    if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
        with tab_csv:
            st.subheader("名簿CSVデータのインポート")
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
                st.session_state.saved_num_students = num_students
            else:
                num_students = st.session_state.saved_num_students
            
            # 操作用プレースホルダー
            control_placeholder = st.empty()
            grid_area_placeholder = st.empty()
            
            # 💡 座席ボックス自体の表示を変化させるグリッド関数
            def draw_current_grid():
                html = "<div class='classroom-container'>"
                html += "<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:8px; border-radius:6px; font-weight:bold; font-size:16px; border: 1px solid #e2e8f0; margin-bottom:10px;'>【教卓】</div>"
                html += "<div class='classroom-grid'>"
                for r in range(7):
                    for c in range(6):
                        if st.session_state.seat_map[r][c]:
                            # 1. すでに確定済みの席
                            if (r, c) in st.session_state.confirmed_seats:
                                name = st.session_state.confirmed_seats[(r, c)]["name"]
                                num = st.session_state.confirmed_seats[(r, c)]["num"]
                                score = st.session_state.confirmed_seats[(r, c)]["score"]
                                prob = st.session_state.confirmed_seats[(r, c)]["prob"]
                                html += f"""
                                <div class='seat-box' style='background-color: #e0f2fe; color: #0369a1; border: 2px solid #0ea5e9;'>
                                    <span style='font-size:11px; font-weight:bold; color: #0284c7; margin-bottom:1px;'>{num}番 ({score}点)</span>
                                    <span style='font-size:18px;'>{name}</span>
                                    <span style='font-size:10px; color:#0284c7; font-weight:normal; margin-top:2px; background:#ffffff; padding:1px 5px; border-radius:20px; border:1px solid #bdf0ff;'>確率: {prob}%</span>
                                </div>
                                """
                            # 2. 現在ルーレット回転中（シャッフル中）の席
                            elif st.session_state.roulette_running:
                                disp_name = st.session_state.temp_display_names.get((r, c), "???")
                                html += f"""
                                <div class='seat-box seat-spinning'>
                                    <span style='font-size:11px; color:#b45309;'>抽選中...</span>
                                    <span style='font-size:18px;'>{disp_name}</span>
                                </div>
                                """
                            # 3. まだ始まっていない初期状態の空席
                            else:
                                html += "<div class='seat-box' style='background-color: #f8fafc; border: 2px dashed #cbd5e1; color: #64748b;'>空席</div>"
                        else:
                            html += "<div class='seat-box' style='background-color: #ffffff; border: 1px solid #f1f5f9; color: #cbd5e1; box-shadow:none; min-height:85px;'>通路</div>"
                html += "</div></div>"
                grid_area_placeholder.html(html)

            # 点数に応じた確率重み計算ロジック
            def calculate_weights_and_probs_base40(names_list, full_initial_list, score_map, disp_num):
                all_scores = list(score_map.values())
                max_score = max(all_scores) if all_scores else 100
                min_score = min(all_scores) if all_scores else 0
                score_range = max(1, max_score - min_score)
                seat_ratio = (disp_num - 1) / 6.0
                
                full_weights = []
                for name in full_initial_list:
                    student_score = float(score_map[name])
                    norm_score = (student_score - min_score) / score_range
                    base_match = (seat_ratio * norm_score) + ((1.0 - seat_ratio) * (1.0 - norm_score))
                    match_factor = base_match ** 4
                    full_weights.append(max(0.001, match_factor))
                
                total_full_w = sum(full_weights) if sum(full_weights) > 0 else 1.0
                prob_map = {name: round((full_weights[idx] / total_full_w) * 100, 1) for idx, name in enumerate(full_initial_list)}
                
                current_weights = []
                for name in names_list:
                    student_score = float(score_map[name])
                    norm_score = (student_score - min_score) / score_range
                    base_match = (seat_ratio * norm_score) + ((1.0 - seat_ratio) * (1.0 - norm_score))
                    match_factor = base_match ** 4
                    current_weights.append(max(0.001, match_factor))
                    
                return current_weights, prob_map

            # --- 💡 クリック（タップ）して1席ずつ止める処理 ---
            def stop_next_seat():
                current_pool = df.head(num_students).copy()
                full_initial_list = current_pool["名前"].tolist()
                
                # まだ選ばれていない生徒のプールを作成
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                names_pool = [n for n in full_initial_list if n not in already_chosen]
                
                num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
                score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}
                
                idx = st.session_state.current_match_idx
                
                if idx < len(st.session_state.shuffled_coords) and names_pool:
                    r, c = st.session_state.shuffled_coords[idx]
                    _, disp_num = get_seat_label(r, c)
                    
                    # 💥 もともとの点数と座席位置に基づいた確率で抽選！
                    weights, prob_map = calculate_weights_and_probs_base40(names_pool, full_initial_list, score_map, disp_num)
                    winner = random.choices(names_pool, weights=weights, k=1)[0]
                    
                    # 席を確定
                    st.session_state.confirmed_seats[(r, c)] = {
                        "name": winner, 
                        "num": num_map[winner],
                        "score": int(score_map[winner]),
                        "prob": prob_map[winner]
                    }
                    
                    # シャッフル用の一時表示名リストを更新（確定したものはプールから外す）
                    names_pool.remove(winner)
                    st.session_state.current_match_idx += 1
                    
                    # すべての席が埋まったら終了
                    if st.session_state.current_match_idx >= len(st.session_state.shuffled_coords) or not names_pool:
                        st.session_state.roulette_running = False
                else:
                    st.session_state.roulette_running = False

            # 一括スキップ処理
            def skip_all_roulette():
                current_pool = df.head(num_students).copy()
                full_initial_list = current_pool["名前"].tolist()
                num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
                score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}
                
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                names_pool = [n for n in full_initial_list if n not in already_chosen]
                
                for i in range(st.session_state.current_match_idx, len(st.session_state.shuffled_coords)):
                    if not names_pool:
                        break
                    r, c = st.session_state.shuffled_coords[i]
                    _, disp_num = get_seat_label(r, c)
                    weights, prob_map = calculate_weights_and_probs_base40(names_pool, full_initial_list, score_map, disp_num)
                    winner = random.choices(names_pool, weights=weights, k=1)[0]
                    
                    st.session_state.confirmed_seats[(r, c)] = {
                        "name": winner, 
                        "num": num_map[winner],
                        "score": int(score_map[winner]),
                        "prob": prob_map[winner]
                    }
                    names_pool.remove(winner)
                    
                st.session_state.roulette_running = False

            # --- UIコントロール部分 ---
            if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                    if st.button("🎰 ルーレットを開始する（全席シャッフル）", type="primary", use_container_width=True):
                        st.session_state.confirmed_seats = {}
                        chosen_coords = active_coords[:limit_count]
                        random.shuffle(chosen_coords) # 抽選される座席の順番をランダム化
                        st.session_state.shuffled_coords = chosen_coords
                        st.session_state.current_match_idx = 0
                        st.session_state.roulette_running = True
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                    
            elif st.session_state.roulette_running:
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                    col1, col2 = st.columns([3, 1])
                    col1.button("👇 次の座席をストップ！", type="primary", on_click=stop_next_seat, use_container_width=True)
                    col2.button("⏩ 全部一瞬で止める", on_click=skip_all_roulette, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                # 回転中の席にダミーの生徒名を設定してリアルタイムにシャッフル感を出す
                current_pool = df.head(num_students).copy()
                full_initial_list = current_pool["名前"].tolist()
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                names_pool = [n for n in full_initial_list if n not in already_chosen]
                
                for i in range(st.session_state.current_match_idx, len(st.session_state.shuffled_coords)):
                    r, c = st.session_state.shuffled_coords[i]
                    if names_pool:
                        st.session_state.temp_display_names[(r, c)] = random.choice(names_pool)
                        
            else:
                # 席替え完了状態
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                    st.success("🎉 すべての座席が確定しました！")
                    if st.button("🔄 もう一度最初からやり直す", use_container_width=True):
                        st.session_state.confirmed_seats = {}
                        st.session_state.roulette_running = False
                        st.session_state.shuffled_coords = []
                        st.session_state.current_match_idx = 0
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            # 最後に現在の座席グリッドを描画
            draw_current_grid()
            
            # ルーレット回転中は高速で再描画をループさせる
            if st.session_state.roulette_running:
                time.sleep(0.08)
                st.rerun()
