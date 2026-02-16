"""Streamlit メインアプリ"""

import streamlit as st

from src.ui.views.dashboard import render as dashboard
from src.ui.views.learning import render as learning
from src.ui.views.portfolio import render as portfolio
from src.ui.views.screening import render as screening
from src.ui.views.settings import render as settings
from src.ui.views.simulation import render as simulation

st.set_page_config(
    page_title="traders-tool",
    page_icon=":vertical_traffic_light:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("traders-tool")
st.sidebar.caption("ずぼら x 低リスク 株式投資ツール")
st.sidebar.divider()

nav = st.navigation(
    [
        st.Page(dashboard, title="ダッシュボード", url_path="dashboard", default=True),
        st.Page(portfolio, title="ポートフォリオ管理", url_path="portfolio"),
        st.Page(screening, title="スクリーニング", url_path="screening"),
        st.Page(learning, title="学習", url_path="learning"),
        st.Page(simulation, title="シミュレーション", url_path="simulation"),
        st.Page(settings, title="設定", url_path="settings"),
    ]
)

st.sidebar.divider()
st.sidebar.caption("v0.3.0")

nav.run()
