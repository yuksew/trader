"""Streamlit メインアプリ - ページルーティング"""

import streamlit as st

st.set_page_config(
    page_title="traders-tool",
    page_icon=":vertical_traffic_light:",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGE_LABELS = ["ダッシュボード", "ポートフォリオ管理", "スクリーニング", "学習", "シミュレーション", "設定"]
PAGE_KEYS = ["dashboard", "portfolio", "screening", "learning", "simulation", "settings"]
_label_to_key = dict(zip(PAGE_LABELS, PAGE_KEYS))
_key_to_index = {k: i for i, k in enumerate(PAGE_KEYS)}

# URLからページを復元（リロード対応）
_qp = st.query_params.get("page", "dashboard")
_default_index = _key_to_index.get(_qp, 0)

st.sidebar.title("traders-tool")
st.sidebar.caption("ずぼら x 低リスク 株式投資ツール")
st.sidebar.divider()

page = st.sidebar.radio(
    "メニュー",
    options=PAGE_LABELS,
    index=_default_index,
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("v0.3.0")

selected = _label_to_key[page]

# URLバーを同期（リロード時にページ保持）
if st.query_params.get("page") != selected:
    st.query_params["page"] = selected

if selected == "dashboard":
    from src.ui.views.dashboard import render
elif selected == "portfolio":
    from src.ui.views.portfolio import render
elif selected == "screening":
    from src.ui.views.screening import render
elif selected == "learning":
    from src.ui.views.learning import render
elif selected == "simulation":
    from src.ui.views.simulation import render
elif selected == "settings":
    from src.ui.views.settings import render

render()
