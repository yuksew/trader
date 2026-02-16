"""「なぜ？」「なぜ危険？」ポップアップコンポーネント"""

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


def render_why_signal(signal_id: int, signal_type: str, key_suffix: str = "") -> None:
    """シグナルの「なぜ注目？」ボタンとポップアップを描画

    Args:
        signal_id: シグナルID
        signal_type: シグナル種別
        key_suffix: Streamlitキーの一意性を保つためのサフィックス
    """
    with st.popover(f"なぜ注目？", use_container_width=False):
        explanation = _api_get(f"/api/signals/{signal_id}/explanation")
        if explanation:
            st.markdown(f"**{explanation.get('title', 'シグナルの理由')}**")
            st.markdown(explanation.get("text", "説明を取得できませんでした。"))
            detail = explanation.get("detail")
            if detail:
                with st.expander("もっと詳しく"):
                    st.markdown(detail)
        else:
            st.info("説明を読み込み中...")
        # XP記録
        _record_why_viewed("signal", signal_id)


def render_why_alert(alert_id: int, alert_type: str, key_suffix: str = "") -> None:
    """アラートの「なぜ危険？」ボタンとポップアップを描画

    Args:
        alert_id: アラートID
        alert_type: アラート種別
        key_suffix: Streamlitキーの一意性を保つためのサフィックス
    """
    with st.popover(f"なぜ危険？", use_container_width=False):
        explanation = _api_get(f"/api/alerts/{alert_id}/explanation")
        if explanation:
            st.markdown(f"**{explanation.get('title', 'なぜ危険なのか')}**")
            st.markdown(explanation.get("text", "説明を取得できませんでした。"))
            detail = explanation.get("detail")
            if detail:
                with st.expander("もっと詳しく"):
                    st.markdown(detail)
        else:
            st.info("説明を読み込み中...")
        _record_why_viewed("alert", alert_id)


def render_why_health_score(portfolio_id: int) -> None:
    """健全度スコアの「なぜこのスコア？」ボタンとポップアップを描画"""
    with st.popover("なぜこのスコア？", use_container_width=False):
        health = _api_get(f"/api/portfolios/{portfolio_id}/health")
        if health:
            score = health.get("health_score", 0)
            st.markdown(f"**健全度スコア: {score}/100**")
            details = health.get("details", {})
            labels = {
                "diversification": ("分散度", "銘柄やセクターの偏りが少ないほど高い"),
                "volatility": ("ボラティリティ", "値動きが穏やかなほど高い"),
                "drawdown": ("ドローダウン", "ピークからの下落が小さいほど高い"),
                "correlation": ("相関", "銘柄間の連動が低いほど高い"),
                "unrealized_loss": ("含み損", "含み損が少ないほど高い"),
            }
            for key, (name, desc) in labels.items():
                val = details.get(key, 0)
                user_stage = st.session_state.get("user_stage", 1)
                if user_stage >= 2:
                    st.markdown(f"- **{name}**: {val:.0f}/100 - {desc}")
                else:
                    st.markdown(f"- **{name}**: {'良好' if val >= 70 else '改善の余地あり'}")
        else:
            st.info("スコアの内訳を読み込み中...")
        _record_why_viewed("health_score", portfolio_id)


def _record_why_viewed(target_type: str, target_id: int) -> None:
    """「なぜ？」閲覧をXP記録する"""
    try:
        requests.post(
            f"{API_BASE}/api/user/xp",
            json={"action_type": f"why_{target_type}_viewed", "target_id": str(target_id)},
            timeout=5,
        )
    except Exception:
        pass
