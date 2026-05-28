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
    
    /* Streamlit標準ボタンの共通スタイル調整 */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: bold !important;
    }
    
    div.stButton > button[kind="primary"] {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 20px !important;
        border: 2px solid #10b981 !important;
        padding: 10px 20px !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #ef4444 !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 16px !important;
        border: 2px solid #ef4444 !important;
    }
    
    .classroom-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 15px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    
    /* 💡 シャッフル中ボタン（ルーレット状態）専用のスタイルとアニメーション */
    div.stButton > button.spinning-btn {
        background-color: #fef3c7 !important;
        color: #d97706 !important;
        border: 2px solid #f59e0b !important;
        min-height: 85px !important;
        font-size: 16px !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        animation: seat-shake 0.15s infinite alternate;
        box-shadow: 0 3px 8px rgba(245, 158, 11, 0.2) !important;
    }
    div.stButton > button.spinning-btn:hover {
        background-color: #fffbeb !important;
        border-color: #d97706 !important;
        color: #b45309 !important;
    }
    
    @keyframes seat-shake {
        0% { transform: translateY(-1px) scale(0.99); }
        100% { transform: translateY(1px) scale(1.01); }
    }
    
    /* 確定済み・空席・通路の静的ボックス用スタイル */
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
            
            control_placeholder = st.empty()
            
            # 💡 座席クリック時の確定処理関数
            def stop_selected_seat(click_r, click_c):
                current_pool = df.head(num_students).copy()
                full_initial_list = current_pool["名前"].tolist()
                
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                names_pool = [n for n in full_initial_list if n not in already_chosen]
                
                num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
                score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}
                
                if names_pool and (click_r, click_c) not in st.session_state.confirmed_seats:
                    _, disp_num = get_seat_label(click_r, click_c)
                    
                    # 🔥 選択された座席位置と点数に基づく元のロジックで抽選
                    weights, prob_map = calculate_weights_and_probs_base40(names_pool, full_initial_list, score_map, disp_num)
                    winner = random.choices(names_pool, weights=weights, k=1)[0]
                    
                    st.session_state.confirmed_seats[(click_r, click_c)] = {
                        "name": winner, 
                        "num": num_map[winner],
                        "score": int(score_map[winner]),
                        "prob": prob_map[winner]
                    }
                    
                    # 残りの抽選が必要な席があるか確認
                    rem_seats = [coords for coords in st.session_state.shuffled_coords if coords not in st.session_state.confirmed_seats]
                    if not rem_seats or len(already_chosen) + 1 >= num_students:
                        st.session_state.roulette_running = False

            # 一括ストップ処理
            def skip_all_roulette():
                current_pool = df.head(num_students).copy()
                full_initial_list = current_pool["名前"].tolist()
                num_map = {row["名前"]: row["出席番号"] for _, row in current_pool.iterrows()}
                score_map = {row["名前"]: row["点数"] for _, row in current_pool.iterrows()}
                
                for (r, c) in st.session_state.shuffled_coords:
                    already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                    names_pool = [n for n in full_initial_list if n not in already_chosen]
                    
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
                        "score": int(score_map[winner]),
                        "prob": prob_map[winner]
                    }
                st.session_state.roulette_running = False

            # --- UIコントロール部分 ---
            if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                    if st.button("🎰 ルーレットを開始する（全席シャッフル）", type="primary", use_container_width=True):
                        st.session_state.confirmed_seats = {}
                        chosen_coords = active_coords[:limit_count]
                        st.session_state.shuffled_coords = chosen_coords
                        st.session_state.roulette_running = True
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                    
            elif st.session_state.roulette_running:
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto; text-align:center;'>", unsafe_allow_html=True)
                    st.markdown("<h3 style='color:#d97706; margin-bottom:5px;'>👉 止めたい座席を直接クリックしてください！</h3>", unsafe_allow_html=True)
                    st.button("⏩ 残りの席を一瞬で全部止める", on_click=skip_all_roulette, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                # 動いている席用にダミーの生徒名をランダム生成
                current_pool = df.head(num_students).copy()
                names_pool = current_pool["名前"].tolist()
                already_chosen = [v["name"] for v in st.session_state.confirmed_seats.values()]
                available_names = [n for n in names_pool if n not in already_chosen]
                
                for (r, c) in st.session_state.shuffled_coords:
                    if (r, c) not in st.session_state.confirmed_seats and available_names:
                        st.session_state.temp_display_names[(r, c)] = random.choice(available_names)
                        
            else:
                with control_placeholder.container():
                    st.markdown("<div style='max-width:900px; margin:0 auto;'>", unsafe_allow_html=True)
                    st.success("🎉 すべての座席が確定しました！")
                    if st.button("🔄 もう一度最初からやり直す", use_container_width=True):
                        st.session_state.confirmed_seats = {}
                        st.session_state.roulette_running = False
                        st.session_state.shuffled_coords = []
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            # --- 💡 座席グリッドの描画 (ボタン・カスタムボックスの混在レイアウト) ---
            st.markdown("<div class='classroom-container'>", unsafe_allow_html=True)
            st.markdown("<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:8px; border-radius:6px; font-weight:bold; font-size:16px; border: 1px solid #e2e8f0; margin-bottom:10px;'>【教卓】</div>", unsafe_allow_html=True)
            
            # st.columnsで6列のグリッドを構築
            for r in range(7):
                grid_cols = st.columns(6)
                for c in range(6):
                    with grid_cols[c]:
                        if st.session_state.seat_map[r][c]:
                            # 1. すでに確定済みの席 (静的HTML)
                            if (r, c) in st.session_state.confirmed_seats:
                                name = st.session_state.confirmed_seats[(r, c)]["name"]
                                num = st.session_state.confirmed_seats[(r, c)]["num"]
                                score = st.session_state.confirmed_seats[(r, c)]["score"]
                                prob = st.session_state.confirmed_seats[(r, c)]["prob"]
                                html_card = f"""
                                <div class='seat-box' style='background-color: #e0f2fe; color: #0369a1; border: 2px solid #0ea5e9;'>
                                    <span style='font-size:11px; font-weight:bold; color: #0284c7; margin-bottom:1px;'>{num}番 ({score}点)</span>
                                    <span style='font-size:18px;'>{name}</span>
                                    <span style='font-size:10px; color:#0284c7; font-weight:normal; margin-top:2px; background:#ffffff; padding:1px 5px; border-radius:20px; border:1px solid #bdf0ff;'>確率: {prob}%</span>
                                </div>
                                """
                                st.html(html_card)
                                
                            # 2. 現在ルーレット回転中の席 (クリック可能なカスタムボタン)
                            elif st.session_state.roulette_running:
                                disp_name = st.session_state.temp_display_names.get((r, c), "???")
                                # CSSクラス 'spinning-btn' を適用して揺らす
                                st.markdown('<div class="spinning-parent">', unsafe_allow_html=True)
                                if st.button(f"抽選中...\n{disp_name}", key=f"roll_{r}_{c}", use_container_width=True):
                                    stop_selected_seat(r, c)
                                    st.rerun()
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # CSSクラスをStreamlitのボタンへ強制インジェクション
                                st.markdown(f"""
                                    <script>
                                    var buttons = window.parent.document.querySelectorAll('button');
                                    buttons.forEach(function(btn) {{
                                        if(btn.innerText.toLowerString().indexOf('{disp_name}') !== -1 || btn.innerText.indexOf('抽選中') !== -1) {{
                                            btn.classList.add('spinning-btn');
                                        }}
                                    }});
                                    </script>
                                """, unsafe_allow_html=True)
                                
                            # 3. まだ始まっていない初期状態の空席 (静的HTML)
                            else:
                                st.html("<div class='seat-box' style='background-color: #f8fafc; border: 2px dashed #cbd5e1; color: #64748b;'>空席</div>")
                        else:
                            # 通路 (静的HTML)
                            st.html("<div class='seat-box' style='background-color: #ffffff; border: 1px solid #f1f5f9; color: #cbd5e1; box-shadow:none; min-height:85px;'>通路</div>")
            st.markdown("</div>", unsafe_allow_html=True)
            
            # ルーレット回転中は裏で名前をシャッフルし続けるため自動再描画
            if st.session_state.roulette_running:
                time.sleep(0.08)
                st.rerun()
