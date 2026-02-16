"""Streamlit メインアプリ - ページルーティング"""

import streamlit as st
import requests

st.set_page_config(
    page_title="traders-tool",
    page_icon=":vertical_traffic_light:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ユーザープロフィール初期化 ---
if "user_stage" not in st.session_state:
    try:
        resp = requests.get("http://localhost:8000/api/user/profile", timeout=5)
        resp.raise_for_status()
        profile = resp.json()
        st.session_state["user_stage"] = profile.get("stage", 1)
        st.session_state["user_level"] = profile.get("level", 1)
        st.session_state["user_xp"] = profile.get("xp", 0)
    except Exception:
        st.session_state["user_stage"] = 1
        st.session_state["user_level"] = 1
        st.session_state["user_xp"] = 0

# --- サイドバーナビゲーション ---
PAGES = {
    "ダッシュボード": "dashboard",
    "ポートフォリオ管理": "portfolio",
    "スクリーニング": "screening",
    "学習": "learning",
    "シミュレーション": "simulation",
    "プロフィール": "profile",
    "設定": "settings",
}

st.sidebar.title("traders-tool")
st.sidebar.caption("ずぼら x 低リスク 株式投資ツール")

# ステージバッジをサイドバーに表示
from src.ui.components.stage_indicator import render_stage_badge_compact, STAGE_NAMES, LEVEL_NAMES

stage = st.session_state.get("user_stage", 1)
level = st.session_state.get("user_level", 1)
stage_name = STAGE_NAMES.get(stage, "ビギナー")
level_name = LEVEL_NAMES.get(level, "株の卵")
st.sidebar.markdown(
    f"""<div style="
        background:linear-gradient(135deg,#667eea,#764ba2);
        color:white;
        padding:6px 10px;
        border-radius:6px;
        font-size:0.85em;
        text-align:center;
        margin-bottom:8px;
    ">
        Lv.{stage} {stage_name} | {level_name}
    </div>""",
    unsafe_allow_html=True,
)

st.sidebar.divider()

page = st.sidebar.radio(
    "メニュー",
    options=list(PAGES.keys()),
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("v0.2.0 Education")

# --- ページルーティング ---
selected = PAGES[page]

if selected == "dashboard":
    from src.ui.pages.dashboard import render
elif selected == "portfolio":
    from src.ui.pages.portfolio import render
elif selected == "screening":
    from src.ui.pages.screening import render
elif selected == "learning":
    from src.ui.pages.learning import render
elif selected == "simulation":
    from src.ui.pages.simulation import render
elif selected == "profile":
    from src.ui.pages.profile import render
elif selected == "settings":
    from src.ui.pages.settings import render

render()
