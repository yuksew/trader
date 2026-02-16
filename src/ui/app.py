"""Streamlit メインアプリ - ページルーティング"""

import streamlit as st

st.set_page_config(
    page_title="traders-tool",
    page_icon=":vertical_traffic_light:",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "ダッシュボード": "dashboard",
    "ポートフォリオ管理": "portfolio",
    "スクリーニング": "screening",
    "学習": "learning",
    "シミュレーション": "simulation",
    "設定": "settings",
}

st.sidebar.title("traders-tool")
st.sidebar.caption("ずぼら x 低リスク 株式投資ツール")
st.sidebar.divider()

page = st.sidebar.radio(
    "メニュー",
    options=list(PAGES.keys()),
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("v0.3.0")

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
elif selected == "settings":
    from src.ui.pages.settings import render

render()
