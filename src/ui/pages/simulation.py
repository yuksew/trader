"""シミュレーション画面 - ペーパートレード、What-Ifシミュレーション"""

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


def _render_paper_trade() -> None:
    """ペーパートレード（仮想売買）タブ"""
    st.subheader("ペーパートレード")
    st.caption("仮想資金で株式売買を練習できます。実際のお金は使いません。")

    st.info("**練習モード** - 仮想のお金で取引の練習ができます")

    # 仮想ポートフォリオ取得
    paper = _api_get("/api/simulation/paper-portfolio", {})
    balance = paper.get("virtual_balance", 1_000_000) if paper else 1_000_000
    holdings = paper.get("holdings", []) if paper else []

    st.metric("仮想残高", f"{balance:,.0f}円")

    st.markdown("#### 売買注文")
    with st.form("paper_trade_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            ticker = st.text_input("銘柄コード", placeholder="例: 7203.T")
        with col2:
            quantity = st.number_input("数量（株）", min_value=1, step=1, value=100)
        with col3:
            action = st.selectbox("売買", ["買い", "売り"])

        submitted = st.form_submit_button("注文を実行")
        if submitted and ticker:
            action_en = "buy" if action == "買い" else "sell"
            result = _api_post(
                "/api/simulation/paper-trade",
                {"ticker": ticker.strip(), "quantity": quantity, "action": action_en},
            )
            if result:
                price = result.get("price", 0)
                st.success(
                    f"{ticker} を {quantity}株 {action} しました（約定価格: {price:,.0f}円）"
                )
                st.rerun()

    if holdings:
        st.markdown("#### 仮想保有銘柄")
        rows = []
        for h in holdings:
            current = h.get("current_value", 0)
            buy = h.get("avg_price", 0)
            qty = h.get("quantity", 0)
            pnl = current - (buy * qty) if buy and qty else 0
            rows.append({
                "銘柄": h.get("ticker", ""),
                "数量": qty,
                "平均取得価格": f"{buy:,.0f}",
                "評価額": f"{current:,.0f}",
                "損益": f"{pnl:+,.0f}",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("仮想保有銘柄はありません。上のフォームから練習取引を始めましょう。")


def _render_what_if() -> None:
    """What-Ifシミュレーションタブ"""
    st.subheader("What-If シミュレーション")
    st.caption("「もしこうだったら？」を試して、リスク管理の大切さを体感できます")

    scenarios = {
        "stop_loss": {
            "name": "もし損切りしなかったら？",
            "desc": "損切りラインを無視して保有し続けた場合のシミュレーション",
        },
        "concentration": {
            "name": "もし集中投資を続けたら？",
            "desc": "1銘柄に資金を集中させ続けた場合のリスク",
        },
    }

    for scenario_key, scenario in scenarios.items():
        with st.expander(f":warning: {scenario['name']}"):
            st.markdown(scenario["desc"])

            if st.button("シミュレーション実行", key=f"sim_{scenario_key}"):
                with st.spinner("計算中..."):
                    portfolio_id = st.session_state.get("portfolio_id")
                    result = _api_post(
                        "/api/simulation/what-if",
                        {
                            "scenario_type": scenario_key,
                            "portfolio_id": portfolio_id,
                        },
                    )
                    if result:
                        st.session_state[f"sim_result_{scenario_key}"] = result

            result = st.session_state.get(f"sim_result_{scenario_key}")
            if result:
                _render_simulation_result(result)


def _render_simulation_result(result: dict) -> None:
    """シミュレーション結果を描画"""
    summary = result.get("result_summary", "")
    if summary:
        st.markdown(f"**結果**: {summary}")

    data = result.get("result_data", {})
    if not data:
        return

    comparison = data.get("comparison")
    if comparison:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**現状**")
            current = comparison.get("current", {})
            for k, v in current.items():
                st.metric(k, v)
        with col2:
            st.markdown("**シミュレーション結果**")
            simulated = comparison.get("simulated", {})
            for k, v in simulated.items():
                st.metric(k, v)

    chart_data = data.get("chart")
    if chart_data:
        df = pd.DataFrame(chart_data)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
        st.line_chart(df)

    lesson = data.get("lesson")
    if lesson:
        st.info(f"**学び**: {lesson}")


def render() -> None:
    """シミュレーションページを描画"""
    st.title("シミュレーション")

    tab_paper, tab_whatif = st.tabs(["ペーパートレード", "What-If"])

    with tab_paper:
        _render_paper_trade()

    with tab_whatif:
        _render_what_if()
