"""アラートバナーコンポーネント"""

import requests
import streamlit as st

from src.ui.config import API_BASE

_LEVEL_LABEL = {
    4: "危険",
    3: "警告",
    2: "注意",
    1: "情報",
}


def _resolve_alert(alert_id: int) -> bool:
    """APIを呼んでアラートを解決済みにする。"""
    try:
        resp = requests.put(f"{API_BASE}/api/alerts/{alert_id}/resolve", timeout=10)
        resp.raise_for_status()
        return True
    except Exception:
        return False


def render_alert_banner(alerts: list[dict]) -> None:
    """アラートバナーを描画する"""
    if not alerts:
        return

    active = [a for a in alerts if not a.get("is_resolved")]
    if not active:
        return

    active.sort(key=lambda a: a.get("level", 1), reverse=True)

    st.markdown(f"### :warning: アラート ({len(active)}件)")

    for alert in active:
        alert_id = alert.get("id")
        level = alert.get("level", 1)
        label = _LEVEL_LABEL.get(level, "情報")

        msg = alert.get("message", "")
        action = alert.get("action_suggestion", "")

        body = f"**[{label}]** {msg}"
        if action:
            body += f"\n\n推奨: {action}"

        detail = alert.get("detail")
        if detail:
            body += f"\n\n根拠: {detail}"

        col_body, col_btn = st.columns([5, 1])
        with col_body:
            if level >= 4:
                st.error(body)
            elif level == 3:
                st.warning(body)
            else:
                st.info(body)
        with col_btn:
            if alert_id is not None and st.button(
                "解決", key=f"resolve_{alert_id}"
            ):
                if _resolve_alert(alert_id):
                    st.rerun()
                else:
                    st.error("解決に失敗しました")
