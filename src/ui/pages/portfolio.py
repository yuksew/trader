"""ポートフォリオ管理 - 銘柄追加/削除 + ステージ別ガードレール制御"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"


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


def _check_guardrails(portfolio_id: int, ticker: str, shares: float, buy_price: float) -> dict:
    """ガードレールチェック。ブロック/警告/確認の判定を返す

    Returns:
        {"blocked": bool, "warnings": list[str], "confirm_required": bool, "confirm_message": str}
    """
    user_stage = st.session_state.get("user_stage", 1)
    safe_mode = st.session_state.get("safe_mode", False)

    result = {"blocked": False, "warnings": [], "confirm_required": False, "confirm_message": ""}

    # ガードレール情報をAPIから取得
    guardrails = _api_get(f"/api/user/guardrails", {})
    health_data = _api_get(f"/api/portfolios/{portfolio_id}/health")
    health_score = health_data.get("health_score", 100) if health_data else 100

    # 健全度チェック
    if health_score < 40:
        if user_stage <= 1 or safe_mode:
            result["blocked"] = True
            result["warnings"].append(
                "ポートフォリオの健全度が低い状態です。"
                "安全のため、新しい銘柄の購入は現在できません。"
                "まずはポートフォリオの改善を行いましょう。"
            )
        elif user_stage == 2:
            result["confirm_required"] = True
            result["confirm_message"] = (
                "ポートフォリオの健全度が40未満です。"
                "この状態で新規購入を行うとリスクが高まります。本当に購入しますか？"
            )
        elif user_stage == 3:
            result["warnings"].append("健全度が40未満です。新規購入にはご注意ください。")

    # 集中度チェック
    portfolio = _api_get(f"/api/portfolios/{portfolio_id}")
    holdings = portfolio.get("holdings", []) if portfolio else []
    total_value = sum(
        h.get("current_price", h.get("buy_price", 0)) * h.get("shares", 0)
        for h in holdings
    )
    new_value = buy_price * shares
    if total_value > 0:
        concentration = new_value / (total_value + new_value) * 100
    else:
        concentration = 100.0

    concentration_limit = {1: 30, 2: 30, 3: 40, 4: 50}.get(user_stage, 30)
    if safe_mode:
        concentration_limit = 30

    if concentration > concentration_limit:
        if user_stage <= 1 or safe_mode:
            result["blocked"] = True
            result["warnings"].append(
                f"この銘柄を購入すると、1銘柄への集中度が{concentration:.0f}%になります。"
                f"分散投資のため、{concentration_limit}%を超える集中は制限されています。"
            )
        elif user_stage == 2:
            result["confirm_required"] = True
            result["confirm_message"] = (
                f"1銘柄への集中度が{concentration:.0f}%になります。"
                f"分散投資の観点から推奨されません。本当に購入しますか？"
            )
        else:
            result["warnings"].append(
                f"集中度が{concentration:.0f}%になります。分散をご検討ください。"
            )

    return result


def render() -> None:
    """ポートフォリオ管理ページを描画"""
    st.title("ポートフォリオ管理")

    user_stage = st.session_state.get("user_stage", 1)

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

    # --- 銘柄追加（ガードレール付き） ---
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
            # ガードレールチェック（NEW）
            guard = _check_guardrails(selected_id, ticker.strip(), shares, buy_price)

            if guard["blocked"]:
                for w in guard["warnings"]:
                    st.error(w)
            elif guard["confirm_required"]:
                st.session_state["pending_holding"] = {
                    "ticker": ticker.strip(),
                    "shares": shares,
                    "buy_price": buy_price,
                    "portfolio_id": selected_id,
                }
                st.warning(guard["confirm_message"])
                for w in guard["warnings"]:
                    st.warning(w)
            else:
                for w in guard["warnings"]:
                    st.warning(w)
                result = _api_post(
                    f"/api/portfolios/{selected_id}/holdings",
                    {"ticker": ticker.strip(), "shares": shares, "buy_price": buy_price},
                )
                if result:
                    st.success(f"{ticker} を追加しました。")
                    st.rerun()

    # 確認ダイアログ処理
    pending = st.session_state.get("pending_holding")
    if pending and pending.get("portfolio_id") == selected_id:
        st.warning(f"**確認**: {pending['ticker']} を {pending['shares']:.0f}株 追加しますか？")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("はい、追加する", key="confirm_add"):
                result = _api_post(
                    f"/api/portfolios/{selected_id}/holdings",
                    {"ticker": pending["ticker"], "shares": pending["shares"], "buy_price": pending["buy_price"]},
                )
                if result:
                    st.success(f"{pending['ticker']} を追加しました。")
                    del st.session_state["pending_holding"]
                    st.rerun()
        with col_no:
            if st.button("キャンセル", key="cancel_add"):
                del st.session_state["pending_holding"]
                st.rerun()

    # --- 保有銘柄一覧 ---
    st.subheader("保有銘柄一覧")
    holdings = portfolio.get("holdings", [])
    if not holdings:
        st.info("保有銘柄がありません。")
        return

    for h in holdings:
        ticker_code = h.get("ticker", "")
        name = h.get("name", ticker_code)
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            st.write(f"**{name}** ({ticker_code})")
        with col2:
            st.write(f"保有: {h.get('shares', 0):,.0f}株")
        with col3:
            st.write(f"取得: {h.get('buy_price', 0):,.0f}円")
        with col4:
            if st.button("削除", key=f"del_{ticker_code}"):
                if _api_delete(f"/api/portfolios/{selected_id}/holdings/{ticker_code}"):
                    st.success(f"{ticker_code} を削除しました。")
                    st.rerun()

    # --- 損切りライン設定（ステージ別） ---
    st.divider()
    st.subheader("損切りライン設定")
    if user_stage <= 1:
        st.info("損切りラインは自動で-10%に設定されています（変更不可）。")
        st.caption("ステージが上がると、損切りラインをカスタマイズできるようになります。")
    elif user_stage == 2:
        stop_loss = st.slider(
            "損切りライン（%）",
            min_value=-20,
            max_value=-5,
            value=-10,
            step=1,
            key="stop_loss_slider",
        )
        st.caption("損切りラインを変更する場合、理由を入力してください。")
        reason = st.text_input("変更理由", key="stop_loss_reason")
        if st.button("損切りラインを更新") and reason:
            st.success(f"損切りラインを{stop_loss}%に設定しました。")
    elif user_stage == 3:
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
    else:
        stop_loss = st.number_input(
            "損切りライン（%）",
            value=-10.0,
            step=0.5,
            key="stop_loss_input",
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
