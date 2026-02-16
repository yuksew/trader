"""ポートフォリオ管理 - 銘柄追加/削除 + 損切りライン設定"""

import streamlit as st
import requests

from src.ui.config import API_BASE


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def _api_post(path: str, data: dict):
    try:
        resp = requests.post(f"{API_BASE}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"APIエラー: {e}")
        return None


def _api_delete(path: str):
    try:
        resp = requests.delete(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        st.error(f"APIエラー: {e}")
        return False


def render() -> None:
    st.title("ポートフォリオ管理")

    # --- ポートフォリオ作成 ---
    with st.expander("新規ポートフォリオを作成", expanded=False):
        name = st.text_input("ポートフォリオ名", placeholder="例: メインポートフォリオ")
        if st.button("作成", disabled=not name):
            result = _api_post("/api/portfolios", {"name": name})
            if result:
                st.success(f"ポートフォリオ「{name}」を作成しました。")
                st.rerun()

    # --- ポートフォリオ選択 ---
    portfolios = _api_get("/api/portfolios", [])
    if not portfolios:
        st.info("ポートフォリオがありません。上のフォームから作成してください。")
        return

    names = {p["id"]: p["name"] for p in portfolios}
    selected_id = st.selectbox(
        "ポートフォリオを選択",
        options=list(names.keys()),
        format_func=lambda x: names[x],
    )

    portfolio = _api_get(f"/api/portfolios/{selected_id}")
    if not portfolio:
        return

    # --- 銘柄追加 ---
    st.subheader("銘柄を追加")
    with st.form("add_holding", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("銘柄コード", placeholder="例: 7203.T")
        with col2:
            shares = st.number_input("保有株数", min_value=0.0, step=1.0)
        with col3:
            buy_price = st.number_input("取得価格", min_value=0.0, step=1.0)

        submitted = st.form_submit_button("追加")
        if submitted and ticker and shares > 0 and buy_price > 0:
            result = _api_post(
                f"/api/portfolios/{selected_id}/holdings",
                {"ticker": ticker.strip(), "shares": shares, "buy_price": buy_price},
            )
            if result:
                st.success(f"{ticker} を追加しました。")
                st.rerun()

    # --- 保有銘柄一覧 ---
    st.subheader("保有銘柄一覧")
    holdings = portfolio.get("holdings", [])
    if not holdings:
        st.info("保有銘柄がありません。")
        return

    for h in holdings:
        ticker_code = h.get("ticker", "")
        hname = h.get("name", ticker_code)
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            st.write(f"**{hname}** ({ticker_code})")
        with col2:
            st.write(f"保有: {h.get('shares', 0):,.0f}株")
        with col3:
            st.write(f"取得: {h.get('buy_price', 0):,.0f}円")
        with col4:
            if st.button("削除", key=f"del_{ticker_code}"):
                if _api_delete(f"/api/portfolios/{selected_id}/holdings/{ticker_code}"):
                    st.success(f"{ticker_code} を削除しました。")
                    st.rerun()

    # --- 損切りライン設定 ---
    st.divider()
    st.subheader("損切りライン設定")
    stop_loss = st.slider(
        "損切りライン（%）",
        min_value=-30,
        max_value=-3,
        value=-10,
        step=1,
        key="stop_loss_slider",
    )
    if st.button("損切りラインを更新"):
        st.success(f"損切りラインを{stop_loss}%に設定しました。")

    # --- ウォッチリスト ---
    st.divider()
    st.subheader("ウォッチリスト")

    with st.form("add_watchlist", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            wl_ticker = st.text_input("銘柄コード", placeholder="例: 6758.T", key="wl_ticker")
        with col2:
            wl_reason = st.text_input("追加理由", placeholder="例: 割安感あり", key="wl_reason")
        wl_submitted = st.form_submit_button("ウォッチリストに追加")
        if wl_submitted and wl_ticker:
            result = _api_post(
                "/api/watchlist",
                {"ticker": wl_ticker.strip(), "reason": wl_reason},
            )
            if result:
                st.success(f"{wl_ticker} をウォッチリストに追加しました。")
                st.rerun()

    watchlist = _api_get("/api/watchlist", [])
    if watchlist:
        for w in watchlist:
            wt = w.get("ticker", "")
            col1, col2, col3 = st.columns([2, 4, 1])
            with col1:
                st.write(f"**{wt}**")
            with col2:
                st.write(w.get("reason", ""))
            with col3:
                if st.button("削除", key=f"wdel_{wt}"):
                    if _api_delete(f"/api/watchlist/{wt}"):
                        st.rerun()
    else:
        st.info("ウォッチリストは空です。")
