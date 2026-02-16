"""アラートバナーコンポーネント - Level 1-4対応 + 「なぜ危険？」ボタン"""

import streamlit as st

from src.ui.components.explanation_popup import render_why_alert


_LEVEL_LABEL = {
    4: "危険",
    3: "警告",
    2: "注意",
    1: "情報",
}


def render_alert_banner(alerts: list[dict], user_stage: int = 1) -> None:
    """アラートバナーを描画する"""
    if not alerts:
        return

    active = [a for a in alerts if not a.get("is_resolved")]
    if not active:
        return

    # レベル降順（高い=危険が先）でソート
    active.sort(key=lambda a: a.get("level", 1), reverse=True)

    st.markdown(f"### :warning: アラート ({len(active)}件)")

    for alert in active:
        level = alert.get("level", 1)
        label = _LEVEL_LABEL.get(level, "情報")
        ticker = alert.get("ticker", "")

        # ステージ別メッセージ選択
        if user_stage <= 1:
            msg = alert.get("message_lv1", alert.get("message", ""))
        else:
            msg = alert.get("message", "")

        action = alert.get("action_suggestion", "")

        # 本文を組み立て
        body = f"**[{label}]** {msg}"
        if action:
            body += f"\n\n推奨: {action}"

        # 根拠表示（Lv.2以上）
        if user_stage >= 2 and alert.get("detail"):
            body += f"\n\n根拠: {alert['detail']}"

        # レベルに応じたStreamlitコンポーネントを使用
        if level >= 4:
            st.error(body)
        elif level == 3:
            st.warning(body)
        elif level == 2:
            st.info(body)
        else:
            st.info(body)

        # 「なぜ危険？」ボタン
        alert_id = alert.get("id", 0)
        alert_type = alert.get("alert_type", "")
        col1, col2 = st.columns([1, 5])
        with col1:
            render_why_alert(alert_id, alert_type, key_suffix=f"_{alert_id}")
