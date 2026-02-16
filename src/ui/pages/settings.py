"""設定画面"""

import streamlit as st
import requests

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


def render() -> None:
    """設定ページを描画"""
    st.title("設定")

    # --- 損切りルール設定 ---
    st.subheader("損切りルール設定")

    portfolios = _api_get("/api/portfolios", [])
    if not portfolios:
        st.info("ポートフォリオが未作成です。")
        return

    names = {p["id"]: p["name"] for p in portfolios}
    selected_id = st.selectbox(
        "ポートフォリオを選択",
        options=list(names.keys()),
        format_func=lambda x: names[x],
        key="settings_portfolio",
    )

    portfolio = _api_get(f"/api/portfolios/{selected_id}")
    if not portfolio:
        return

    holdings = portfolio.get("holdings", [])
    if not holdings:
        st.info("保有銘柄がありません。")
        return

    st.caption("各銘柄の損切り閾値を設定します。")

    with st.form("stop_loss_form"):
        for h in holdings:
            ticker = h.get("ticker", "")
            name = h.get("name", ticker)
            buy_price = h.get("buy_price", 0)

            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"**{name}** ({ticker})")
                st.caption(f"取得価格: {buy_price:,.0f}円")
            with col2:
                st.slider(
                    "損切りライン (%)",
                    min_value=-30,
                    max_value=-5,
                    value=-10,
                    step=1,
                    key=f"sl_{ticker}",
                )
            with col3:
                st.checkbox(
                    "トレーリングストップ",
                    value=False,
                    key=f"ts_{ticker}",
                )

        if st.form_submit_button("損切りルールを保存"):
            for h in holdings:
                ticker = h.get("ticker", "")
                stop_pct = st.session_state.get(f"sl_{ticker}", -10)
                trailing = st.session_state.get(f"ts_{ticker}", False)
                _api_post(
                    f"/api/portfolios/{selected_id}/stop-loss",
                    {
                        "ticker": ticker,
                        "buy_price": h.get("buy_price", 0),
                        "stop_loss_pct": stop_pct,
                        "trailing_stop": trailing,
                    },
                )
            st.success("損切りルールを保存しました。")

    # --- リスク指標 ---
    st.divider()
    st.subheader("リスク指標")

    risk_metrics = _api_get(f"/api/portfolios/{selected_id}/risk-metrics")
    if risk_metrics:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("最大ドローダウン", f"{risk_metrics.get('max_drawdown', 0):.1f}%")
            st.metric("シャープレシオ", f"{risk_metrics.get('sharpe_ratio', 0):.2f}")
        with col2:
            st.metric("ボラティリティ", f"{risk_metrics.get('portfolio_volatility', 0):.1f}%")
            st.metric("集中度 (HHI)", f"{risk_metrics.get('hhi', 0):.3f}")
        with col3:
            st.metric("95% VaR", f"{risk_metrics.get('var_95', 0):.1f}%")
    else:
        st.info("リスク指標がまだ算出されていません。日次チェック実行後に表示されます。")

    # --- 集中度分析 ---
    st.divider()
    st.subheader("集中度分析")

    concentration = _api_get(f"/api/portfolios/{selected_id}/concentration")
    if concentration:
        st.json(concentration)
    else:
        st.info("集中度データがありません。")
