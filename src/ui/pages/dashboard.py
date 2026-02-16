"""ダッシュボード - メイン画面（1画面で全情報を把握）

優先順位:
1. ステージ・レベル表示（最上部）
2. 守り: 健全度スコア
3. 守り: アラート
4. 攻め: 注目銘柄・シグナル
5. 学習カード
6. 情報: ポートフォリオ一覧
7. 情報: セクター構成・ヒートマップ
"""

import streamlit as st
import requests
import pandas as pd

from src.ui.components.health_gauge import render_health_gauge
from src.ui.components.alert_banner import render_alert_banner
from src.ui.components.signal_card import render_signal_card
from src.ui.components.sector_heatmap import render_sector_heatmap
from src.ui.components.stage_indicator import render_stage_indicator
from src.ui.components.learning_card import render_learning_cards
from src.ui.components.explanation_popup import render_why_health_score

API_BASE = "http://localhost:8000"


def _api_get(path: str, default=None):
    """API GETリクエストのヘルパー"""
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def _get_portfolio_id() -> int | None:
    """選択中のポートフォリオIDを取得"""
    if "portfolio_id" not in st.session_state:
        portfolios = _api_get("/api/portfolios", [])
        if portfolios:
            st.session_state["portfolio_id"] = portfolios[0]["id"]
        else:
            return None
    return st.session_state["portfolio_id"]


def render() -> None:
    """ダッシュボードページを描画"""
    st.title("traders-tool")
    st.caption("ずぼら x 低リスク 株式投資ダッシュボード")

    # ========================================
    # 0. ステージ・レベル表示（NEW）
    # ========================================
    render_stage_indicator()

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

    user_stage = st.session_state.get("user_stage", 1)

    # ========================================
    # 1. 守り: 健全度スコア（最上部）
    # ========================================
    health_data = _api_get(f"/api/portfolios/{portfolio_id}/health")
    if health_data:
        # ステージ別表示制御
        if user_stage <= 1:
            # Lv.1: 信号機のみ（内訳なし）
            render_health_gauge(
                score=health_data.get("health_score", 0),
                details=None,
            )
        elif user_stage == 2:
            # Lv.2: + 内訳バー
            render_health_gauge(
                score=health_data.get("health_score", 0),
                details=health_data.get("details"),
            )
        else:
            # Lv.3+: + 数値詳細
            render_health_gauge(
                score=health_data.get("health_score", 0),
                details=health_data.get("details"),
            )
    else:
        render_health_gauge(score=0)

    # 「なぜこのスコア？」ボタン（NEW）
    render_why_health_score(portfolio_id)

    st.divider()

    # ========================================
    # 2. 守り: アラート
    # ========================================
    alerts = _api_get(f"/api/portfolios/{portfolio_id}/alerts", [])
    render_alert_banner(alerts, user_stage=user_stage)
    if alerts:
        st.divider()

    # ========================================
    # 3. 攻め: 注目銘柄・シグナル
    # ========================================
    signals = _api_get("/api/signals", [])
    render_signal_card(signals, user_stage=user_stage)

    st.divider()

    # ========================================
    # 4. 学習カード（NEW）
    # ========================================
    learning_cards = _api_get("/api/learning/cards?context=dashboard&limit=2", [])
    render_learning_cards(learning_cards)

    if learning_cards:
        st.divider()

    # ========================================
    # 5. 情報: ポートフォリオ一覧
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

            row = {
                "銘柄": h.get("name", h.get("ticker", "")),
                "コード": h.get("ticker", ""),
                "保有数": shares,
                "取得価格": f"{buy:,.0f}",
                "現在値": f"{current:,.0f}",
                "損益": f"{pnl:+,.0f}",
                "損益率": f"{pnl_pct:+.1f}%",
            }

            # Lv.3以上は追加指標を表示
            if user_stage >= 3:
                row["PER"] = h.get("per", "-")
                row["PBR"] = h.get("pbr", "-")

            rows.append(row)

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("保有銘柄がありません。ポートフォリオ管理から追加してください。")

    st.divider()

    # ========================================
    # 6. 情報: セクター構成・ヒートマップ
    # ========================================
    render_sector_heatmap(holdings)
