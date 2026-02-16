"""シグナルカードコンポーネント"""

import streamlit as st


_SIGNAL_TYPE_LABELS = {
    "golden_cross": {"icon": ":chart_with_upwards_trend:", "label": "ゴールデンクロス"},
    "volume_spike": {"icon": ":fire:", "label": "出来高急増"},
    "rsi_reversal": {"icon": ":arrows_counterclockwise:", "label": "RSI反転"},
    "value_opportunity": {"icon": ":gem:", "label": "割安チャンス"},
    "dividend_chance": {"icon": ":moneybag:", "label": "高配当チャンス"},
}

_PRIORITY_COLORS = {
    "high": "#e74c3c",
    "medium": "#f39c12",
    "low": "#3498db",
}


def render_signal_card(signals: list[dict]) -> None:
    """シグナルカードを描画する"""
    if not signals:
        st.info("現在、注目すべきシグナルはありません。")
        return

    st.markdown("### :chart_with_upwards_trend: 今日の注目銘柄 TOP5")

    for i, sig in enumerate(signals[:5], 1):
        sig_type = sig.get("signal_type", "")
        priority = sig.get("priority", "low")
        border_color = _PRIORITY_COLORS.get(priority, "#3498db")
        type_cfg = _SIGNAL_TYPE_LABELS.get(sig_type, {"icon": ":bell:", "label": sig_type})

        body = f"**{i}. {sig.get('ticker', '')}** {type_cfg['label']}"
        msg = sig.get("message", "")
        if msg:
            body += f"\n\n{msg}"

        if priority == "high":
            st.error(body)
        elif priority == "medium":
            st.warning(body)
        else:
            st.info(body)
