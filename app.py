import streamlit as st
import random
import pandas as pd
import time

# 画面設定
st.set_page_config(page_title="PREMIUM LIGHT - 席替えアプリ", layout="wide")

# --- Session State の初期化（コード上部で行うことでバグを防ぎます） ---
if 'seat_map' not in st.session_state:
    st.session_state.seat_map = [[True for _ in range(6)] for _ in range(7)]
if 'final_df' not in st.session_state:
    st.session_state.final_df = None
if 'confirmed_seats' not in st.session_state:
    st.session_state.confirmed_seats = {}
if 'roulette_running' not in st.session_state:
    st.session_state.roulette_running = False

# --- バリアフリー ＆ クリーンライトCSS ＆ スクリプト ---
# ルーレット実行中かどうかでサイドバーの表示・非表示スタイルを切り替える
sidebar_display = "none !important" if st.session_state.roulette_running else "block"

st.markdown(f"""
    <style>
    /* 全体の背景とテキスト色の変更（白基調） */
    .stApp {{
        background-color: #ffffff !important;
        color: #0f172a !important;
    }}
    
    /* 🛠️ ルーレット実行中はサイドバーを完全非表示、それ以外は細く制限 */
    section[data-testid="stSidebar"] {{
        display: {sidebar_display};
        min-width: 180px !important;
        max-width: 240px !important;
    }}
    
    /* タブの見た目をライトモードに最適化 */
    button[data-baseweb="tab"] {{
        color: #64748b !important;
        font-size: 18px !important;
        font-weight: bold !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #0284c7 !important;
        border-bottom-color: #0284c7 !important;
    }}

    /* ボタンのカスタマイズ（高コントラスト設計） */
    div.stButton > button[kind="primary"] {{
        background-color: #10b981 !important; /* ユニバーサルグリーン */
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 20px !important;
        border: 2px solid #10b981 !important;
        border-radius: 8px;
        padding: 10px 20px !important;
    }}
    div.stButton > button[kind="secondary"] {{
        background-color: #ef4444 !important; /* ビビッドレッド */
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: 2px solid #ef4444 !important;
        border-radius: 8px;
    }}
    
    /* 教室のグリッド表示 */
    .classroom-grid {{
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 16px;
        margin-top: 20px;
    }}
    
    /* 座席ボックスの基本 */
    .seat-box {{
        border-radius: 12px;
        padding: 20px 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
        transition: all 0.2s;
    }}
    
    /* 演出：超巨大ルーレット画面 */
    .roulette-container {{
        background: linear-gradient(135deg, #f0fdf4, #e0f2fe);
        border-radius: 16px;
        padding: 50px 20px;
        text-align: center;
        color: #0f172a;
        box-shadow: 0 10px 25px rgba(2, 132, 199, 0.15);
        margin-bottom: 25px;
        border: 4px solid #0284c7;
    }}
    .roulette-target-seat {{
        font-size: 26px;
        font-weight: 800;
        color: #0284c7;
        letter-spacing: 1px;
        margin-bottom: 15px;
    }}
    .roulette-big-name {{
        font-size: 80px;
        font-weight: 900;
        letter-spacing: 4px;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 20px 0;
        min-height: 120px;
        display: flex;
        justify-content: center;
        align-items: center;
    }}
    .roulette-spinning {{
        animation: neon-pulse 0.1s infinite alternate;
        color: #b45309;
    }}
    @keyframes neon-pulse {{
        0% {{ transform: scale(0.98); }}
        100% {{ transform: scale(1.02); }}
    }}
    </style>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
    function downloadSeatMap() {{
        var element = window.parent.document.getElementById("download-area");
        if (element) {{
            html2canvas(element, {{ scale: 2, backgroundColor: "#ffffff" }}).then(function(canvas) {{
                var link = document.createElement("a");
                link.download = "席替え結果.png";
                link.href = canvas.toDataURL("image/png");
                link.click();
            }});
        }}
    }}
    </script>
""", unsafe_allow_html=True)

# 🛠️ ルーレット実行中にJavaScriptでもサイドバーを閉じる補助命令を出す
if st.session_state.roulette_running:
    st.markdown("""
        <script>
        var sidebar = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        var button = window.parent.document.querySelector('button[aria-label="Collapse sidebar"]');
        if (sidebar && sidebar.getAttribute('aria-expanded') === 'true' && button) {
            button.click();
        }
        </script>
    """, unsafe_allow_html=True)

st.title("PREMIUM LIGHT 席替えシステム")
st.caption("【ユニバーサルデザイン設計】遠くからでも見やすい白基調 ＆ 単一カラーのスマート座席表")

# 🛠️ key="main_tabs" を指定してリラン時のタブ初期化バグを防ぐ
tab_setup, tab_csv, tab_run = st.tabs(["1. 座席の形を決める", "2. 名簿を読み込む", "3. ルーレットを回す"])

# --- タブ1：座席レイアウト設定 ---
with tab_setup:
    st.subheader("使用する座席をタップして指定してください")
    st.write("※ 通路にしたい場所をタップすると切り替わります。")
    st.markdown("<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:15px; border-radius:8px; margin-bottom:25px; font-weight:bold; font-size:20px; border: 2px solid #0284c7;'>【教卓】（こちらが前方です）</div>", unsafe_allow_html=True)
    
    for r in range(7):
        cols = st.columns(6)
        for c in range(6):
            active = st.session_state.seat_map[r][c]
            b_type = "primary" if active else "secondary"
            b_label = f"座席 ({r+1}-{c+1})" if active else f"通路"
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
        st.success("名簿の読み込みに成功しました。")
        st.info("数値を変更したい場合は、下の表のセルをダブルクリックして直接編集できます。")
        st.session_state.final_df = st.data_editor(st.session_state.final_df, disabled=["出席番号"], hide_index=True, use_container_width=True)

# --- タブ3：ルーレット実行タブ ---
with tab_run:
    if st.session_state.final_df is None:
        st.error("先に『2. 名簿を読み込む』タブで名簿データを準備してください。")
    else:
        active_coords = [(r, c) for r in range(7) for c in range(6) if st.session_state.seat_map[r][c]]
        df = st.session_state.final_df
        limit_count = min(len(active_coords), len(df))
        
        st.sidebar.header("各種調整")
        num_students = st.sidebar.number_input("参加人数", 1, limit_count, limit_count)
        speed = st.sidebar.slider("シャッフル速度（秒）", 0.04, 0.2, 0.06, step=0.01)
        
        # プレースホルダー類の準備
        start_btn_placeholder = st.empty()
        roulette_placeholder = st.empty()
        skip_btn_placeholder = st.empty()
        save_btn_placeholder = st.empty()
        
        # HTML画像ダウンロード対象エリアのプレースホルダー
        grid_area_placeholder = st.empty()
        
        # 座席グリッドの描画関数
        def draw_current_grid():
            html = "<div id='download-area' style='padding:20px; background:#ffffff;'>"
            html += "<div style='text-align:center; background:#f1f5f9; color:#0284c7; padding:12px; border-radius:8px; font-weight:bold; font-size:18px; border: 1px solid #e2e8f0; margin-bottom:15px;'>【教卓】</div>"
            html += "<div class='classroom-grid'>"
            for r in range(7):
                for c in range(6):
                    if st.session_state.seat_map[r][c]:
                        if (r, c) in st.session_state.confirmed_seats:
                            name = st.session_state.confirmed_seats[(r, c)]["name"]
                            score = st.session_state.confirmed_seats[(r, c)]["score"]
                            html += f"<div class='seat-box' style='background-color: #e0f2fe; color: #0369a1; border: 2px solid #0ea5e9;'>{name}<br><span style='font-size:12px; font-weight:bold; color: #64748b;'>{score}点</span></div>"
                        else:
                            html += "<div class='seat-box' style='background-color: #f8fafc; border: 2px dashed #cbd5e1; color: #64748b;'>空席</div>"
                    else:
                        html += "<div class='seat-box' style='background-color: #ffffff; border: 2px solid #f1f5f9; color: #cbd5e1; box-shadow:none;'>通路</div>"
            html += "</div></div>"
            grid_area_placeholder.html(html)

        draw_current_grid()
        
        # 初期状態・完了状態の表示制御
        if not st.session_state.roulette_running and not st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container'>
                    <div class='roulette-target-seat'>READY</div>
                    <div class='roulette-big-name' style='color: #94a3b8; font-size: 45px;'>「ルーレットを開始する」ボタンを押してください</div>
                </div>
            """)
        elif not st.session_state.roulette_running and st.session_state.confirmed_seats:
            roulette_placeholder.html("""
                <div class='roulette-container' style='background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-color: #10b981;'>
                    <div class='roulette-target-seat' style='color: #10b981;'>COMPLETE</div>
                    <div class='roulette-big-name' style='color: #14532d; font-size: 54px;'>席替え完了</div>
                </div>
            """)
            # 🛠️ 完了時に「画像として保存する」ボタンをメインエリアに表示
            if save_btn_placeholder.button("📷 この座席表を画像(PNG)として保存する", use_container_width=True):
                st.markdown("<script>downloadSeatMap();</script>", unsafe_allow_html=True)

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

        # 開始ボタンの表示
        if not st.session_state.roulette_running:
            start_trigger = start_btn_placeholder.button("ルーレットを開始する", type="primary", use_container_width=True)
        else:
            start_trigger = False

        # ルーレット開始のトリガー処理
        if start_trigger:
            st.session_state.confirmed_seats = {}
            st.session_state.roulette_running = True
            st.rerun()

    # バックグラウンドでのルーレットアニメーションループ処理
    if st.session_state.final_df is not None and st.session_state.roulette_running:
        current_pool = df.head(num_students).copy()
        names_pool = current_pool["名前"].tolist()
        scores_pool = current_pool["点数"].tolist()
        score_map = {n: s for n, s in zip(names_pool, scores_pool)}

        for idx, (r, c) in enumerate(active_coords):
            if not st.session_state.roulette_running or not names_pool:
                break
            
            current_scores = [score_map[n] for n in names_pool]
            max_score = max(current_scores) if current_scores else 100
            weights = [(max_score + 1) - s for s in current_scores]
            weights = [max(0.1, float(w)) for w in weights]
            
            winner = random.choices(names_pool, weights=weights, k=1)[0]
            
            skip_btn_placeholder.button("演出をスキップして一瞬で結果を見る", key=f"sk_{idx}", on_click=trigger_skip, use_container_width=True)
            
            for tick in range(12):
                if not st.session_state.roulette_running:
                    break
                dummy_name = random.choice(names_pool)
                roulette_placeholder.html(f"""
                    <div class='roulette-container'>
                        <div class='roulette-target-seat'>【 {r+1}列目 - {c+1}番 】の抽選中...</div>
                        <div class='roulette-big-name roulette-spinning'>{dummy_name}</div>
                    </div>
                """)
                time.sleep(speed)
            
            if not st.session_state.roulette_running:
                break
                
            roulette_placeholder.html(f"""
                <div class='roulette-container' style='background: linear-gradient(135deg, #ecfdf5, #f0fdf4); border-color: #10b981;'>
                    <div class='roulette-target-seat' style='color: #10b981;'>確定しました</div>
                    <div class='roulette-big-name' style='color: #10b981; font-size: 85px;'>{winner}</div>
                </div>
            """)
            
            st.session_state.confirmed_seats[(r, c)] = {"name": winner, "score": score_map[winner]}
            draw_current_grid()
            names_pool.remove(winner)
            time.sleep(0.5)

        st.session_state.roulette_running = False
        skip_btn_placeholder.empty()
        st.rerun()
