"""アラートバナーコンポーネント"""

import streamlit as st


_LEVEL_LABEL = {
    4: "危険",
    3: "警告",
    2: "注意",
    1: "情報",
}


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

        if level >= 4:
            st.error(body)
        elif level == 3:
            st.warning(body)
        else:
            st.info(body)
