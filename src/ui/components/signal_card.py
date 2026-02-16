"""シグナルカードコンポーネント - ステージ別表現切替 + 「なぜ注目？」ボタン"""

import streamlit as st

from src.ui.components.explanation_popup import render_why_signal


_SIGNAL_TYPE_LABELS = {
    "golden_cross": {"icon": ":chart_with_upwards_trend:", "label": "ゴールデンクロス"},
    "volume_spike": {"icon": ":fire:", "label": "出来高急増"},
    "rsi_reversal": {"icon": ":arrows_counterclockwise:", "label": "RSI反転"},
    "value_opportunity": {"icon": ":gem:", "label": "割安チャンス"},
    "dividend_chance": {"icon": ":moneybag:", "label": "高配当チャンス"},
}

# Lv.1向けの平易な表現
_SIGNAL_PLAIN_LABELS = {
    "golden_cross": "上がり始めています",
    "volume_spike": "注目が集まっています",
    "rsi_reversal": "売られすぎから戻り始めています",
    "value_opportunity": "お買い得かもしれません",
    "dividend_chance": "お小遣い（配当）が多い銘柄です",
}

_PRIORITY_COLORS = {
    "high": "#e74c3c",
    "medium": "#f39c12",
    "low": "#3498db",
}


def render_signal_card(signals: list[dict], user_stage: int = 1) -> None:
    """シグナルカードを描画する

    Args:
        signals: シグナル一覧。各要素:
            - id (int): シグナルID
            - ticker (str): 銘柄コード
            - signal_type (str): シグナル種別
            - priority (str): high/medium/low
            - message (str): メッセージ
            - message_lv1 (str, optional): Lv.1向け平易なメッセージ
            - score (float, optional): スコア
            - detail (dict, optional): 詳細データ
        user_stage: ユーザーのステージ（1-4）
    """
    if not signals:
        st.info("現在、注目すべきシグナルはありません。")
        return

    st.markdown("### :chart_with_upwards_trend: 今日の注目銘柄 TOP5")

    for i, sig in enumerate(signals[:5], 1):
        sig_type = sig.get("signal_type", "")
        priority = sig.get("priority", "low")
        border_color = _PRIORITY_COLORS.get(priority, "#3498db")
        signal_id = sig.get("id", 0)

        # ステージ別表示
        if user_stage <= 1:
            # Lv.1: 銘柄名 + 一言コメント（平易な表現）
            plain = sig.get("message_lv1", _SIGNAL_PLAIN_LABELS.get(sig_type, sig.get("message", "")))
            content_html = f"""
                <strong>{i}. {sig.get('ticker', '')}</strong>
                <br><span style="color:#555">{plain}</span>
            """
        elif user_stage == 2:
            # Lv.2: + スコア内訳、シグナル種別
            type_cfg = _SIGNAL_TYPE_LABELS.get(sig_type, {"icon": ":bell:", "label": sig_type})
            score = sig.get("score")
            score_str = f"スコア: {score:.0f}" if score is not None else ""
            plain = sig.get("message_lv1", "")
            technical = sig.get("message", "")
            msg = f"{plain}（{technical}）" if plain and technical and plain != technical else (technical or plain)
            content_html = f"""
                <strong>{i}. {sig.get('ticker', '')} {type_cfg['icon']} {type_cfg['label']}</strong>
                {"&nbsp;&nbsp;(" + score_str + ")" if score_str else ""}
                <br><span style="color:#555">{msg}</span>
            """
        elif user_stage == 3:
            # Lv.3: + 全指標、根拠データ
            type_cfg = _SIGNAL_TYPE_LABELS.get(sig_type, {"icon": ":bell:", "label": sig_type})
            score = sig.get("score")
            score_str = f"スコア: {score:.0f}" if score is not None else ""
            content_html = f"""
                <strong>{i}. {sig.get('ticker', '')} {type_cfg['icon']} {type_cfg['label']}</strong>
                {"&nbsp;&nbsp;(" + score_str + ")" if score_str else ""}
                <br><span style="color:#555">{sig.get('message', '')}</span>
            """
            detail = sig.get("detail", {})
            if detail:
                detail_parts = [f"{k}: {v}" for k, v in detail.items()]
                content_html += f"<br><small style='color:#888'>{' | '.join(detail_parts)}</small>"
        else:
            # Lv.4: + カスタム、信頼度
            type_cfg = _SIGNAL_TYPE_LABELS.get(sig_type, {"icon": ":bell:", "label": sig_type})
            score = sig.get("score")
            score_str = f"スコア: {score:.0f}" if score is not None else ""
            confidence = sig.get("confidence")
            conf_str = f"信頼度: {confidence:.0f}%" if confidence is not None else ""
            content_html = f"""
                <strong>{i}. {sig.get('ticker', '')} {type_cfg['icon']} {type_cfg['label']}</strong>
                {"&nbsp;&nbsp;(" + score_str + ")" if score_str else ""}
                {"&nbsp;&nbsp;[" + conf_str + "]" if conf_str else ""}
                <br><span style="color:#555">{sig.get('message', '')}</span>
            """
            detail = sig.get("detail", {})
            if detail:
                detail_parts = [f"{k}: {v}" for k, v in detail.items()]
                content_html += f"<br><small style='color:#888'>{' | '.join(detail_parts)}</small>"

        st.markdown(
            f"""<div style="
                border-left: 4px solid {border_color};
                padding: 8px 14px;
                margin-bottom: 6px;
                background: #fafafa;
                border-radius: 4px;
            ">
                {content_html}
            </div>""",
            unsafe_allow_html=True,
        )

        # 「なぜ注目？」ボタン（NEW）
        col1, col2 = st.columns([1, 5])
        with col1:
            render_why_signal(signal_id, sig_type, key_suffix=f"_{signal_id}")
