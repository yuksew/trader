"""学習カードコンポーネント"""

import streamlit as st


def render_learning_card(card: dict) -> None:
    """学習カードを1枚表示する"""
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

    st.info(f"**:{icon}: {title}**\n\n{content}")
    if st.button("x 閉じる", key=f"close_card_{card_id}"):
        st.session_state[dismiss_key] = True
        st.rerun()


def render_learning_cards(cards: list[dict]) -> None:
    """学習カードセクションを描画する"""
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
