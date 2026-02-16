"""学習カードコンポーネント - スワイプ（×ボタン）で閉じられる"""

import streamlit as st


def render_learning_card(card: dict) -> None:
    """学習カードを1枚表示する

    Args:
        card: 学習カード情報
            - id (int): カードID
            - card_key (str): カード識別子
            - title (str): タイトル
            - content (str): ステージに応じた内容（API側で選択済み）
            - category (str): term/chart/indicator/strategy/risk
    """
    card_id = card.get("id", 0)
    dismiss_key = f"card_dismissed_{card_id}"

    if st.session_state.get(dismiss_key):
        return

    category_icons = {
        "term": "book",
        "chart": "bar_chart",
        "indicator": "straight_ruler",
        "strategy": "dart",
        "risk": "shield",
    }
    cat = card.get("category", "term")
    icon = category_icons.get(cat, "bulb")

    title = card.get("title", "")
    content = card.get("content", "")

    with st.container():
        st.markdown(
            f"""<div style="
                background: #f0f7ff;
                border: 1px solid #b3d4fc;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 8px;
                position: relative;
            ">
                <div style="font-weight:bold; margin-bottom:4px;">
                    :{icon}: {title}
                </div>
                <div style="color:#333; font-size:0.95em;">
                    {content}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("x 閉じる", key=f"close_card_{card_id}"):
            st.session_state[dismiss_key] = True
            # カード閲覧記録をAPIに送信
            _record_card_viewed(card_id)
            st.rerun()


def render_learning_cards(cards: list[dict]) -> None:
    """学習カードセクションを描画する

    Args:
        cards: 表示する学習カードのリスト
    """
    if not cards:
        return

    visible = [
        c for c in cards
        if not st.session_state.get(f"card_dismissed_{c.get('id', 0)}")
    ]
    if not visible:
        return

    st.markdown("### :bulb: 学習カード")
    for card in visible:
        render_learning_card(card)


def _record_card_viewed(card_id: int) -> None:
    """カード閲覧をAPIに記録する"""
    import requests
    try:
        requests.post(
            f"http://localhost:8000/api/learning/cards/{card_id}/viewed",
            timeout=5,
        )
    except Exception:
        pass
