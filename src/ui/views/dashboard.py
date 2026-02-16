"""ダッシュボード - メイン画面（1画面で全情報を把握）"""

import streamlit as st
import requests
import pandas as pd

from src.ui.components.health_gauge import render_health_gauge
from src.ui.components.alert_banner import render_alert_banner
from src.ui.components.signal_card import render_signal_card
from src.ui.components.sector_heatmap import render_sector_heatmap

from src.ui.config import API_BASE


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def _get_portfolio_id() -> int | None:
    if "portfolio_id" not in st.session_state:
        portfolios = _api_get("/api/portfolios", [])
        if portfolios:
            st.session_state["portfolio_id"] = portfolios[0]["id"]
        else:
            return None
    return st.session_state["portfolio_id"]


def render() -> None:
    st.title("traders-tool")
    st.caption("ずぼら x 低リスク 株式投資ダッシュボード")

    portfolio_id = _get_portfolio_id()

    if portfolio_id is None:
        st.warning("ポートフォリオが未作成です。サイドバーからポートフォリオ管理を開いて作成してください。")
        return

    # --- ポートフォリオ切替 ---
    portfolios = _api_get("/api/portfolios", [])
    if len(portfolios) > 1:
        names = {p["id"]: p["name"] for p in portfolios}
        selected = st.selectbox(
            "ポートフォリオ",
            options=list(names.keys()),
            format_func=lambda x: names[x],
            index=list(names.keys()).index(portfolio_id),
            label_visibility="collapsed",
        )
        if selected != portfolio_id:
            st.session_state["portfolio_id"] = selected
            st.rerun()

    # ========================================
    # 1. 守り: 健全度スコア
    # ========================================
    health_data = _api_get(f"/api/portfolios/{portfolio_id}/health")
    if health_data:
        render_health_gauge(
            score=health_data.get("health_score", 0),
            details=health_data.get("breakdown"),
        )
    else:
        render_health_gauge(score=0)

    st.divider()

    # ========================================
    # 2. 守り: アラート
    # ========================================
    alerts = _api_get(f"/api/portfolios/{portfolio_id}/alerts", [])
    render_alert_banner(alerts)
    if alerts:
        st.divider()

    # ========================================
    # 3. 攻め: 注目銘柄・シグナル
    # ========================================
    signals = _api_get("/api/signals", [])
    render_signal_card(signals)

    st.divider()

    # ========================================
    # 4. 情報: ポートフォリオ一覧
    # ========================================
    st.markdown("### :briefcase: ポートフォリオ")
    portfolio_detail = _api_get(f"/api/portfolios/{portfolio_id}")
    holdings = portfolio_detail.get("holdings", []) if portfolio_detail else []

    if holdings:
        rows = []
        for h in holdings:
            current = h.get("current_price", h.get("buy_price", 0))
            buy = h.get("buy_price", 0)
            shares = h.get("shares", 0)
            pnl = (current - buy) * shares
            pnl_pct = ((current - buy) / buy * 100) if buy else 0
            rows.append({
                "銘柄": h.get("name", h.get("ticker", "")),
                "コード": h.get("ticker", ""),
                "保有数": shares,
                "取得価格": f"{buy:,.0f}",
                "現在値": f"{current:,.0f}",
                "損益": f"{pnl:+,.0f}",
                "損益率": f"{pnl_pct:+.1f}%",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("保有銘柄がありません。ポートフォリオ管理から追加してください。")

    st.divider()

    # ========================================
    # 5. 情報: セクター構成・ヒートマップ
    # ========================================
    render_sector_heatmap(holdings)
