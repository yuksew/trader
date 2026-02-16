"""学習ページ - 用語集、学習カード一覧"""

import streamlit as st
import requests

from src.ui.config import API_BASE


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def _render_glossary() -> None:
    """用語集タブを描画"""
    st.subheader("用語集")
    st.caption("投資に関する専門用語をやさしく解説します")

    search = st.text_input("用語を検索", placeholder="例: PER、ボラティリティ", key="glossary_search")

    glossary = _api_get("/api/glossary", [])
    if not glossary:
        st.info("用語集を読み込み中...")
        return

    if search:
        search_lower = search.lower()
        glossary = [
            g for g in glossary
            if search_lower in g.get("term", "").lower()
            or search_lower in g.get("reading", "").lower()
            or search_lower in g.get("description", "").lower()
        ]

    if not glossary:
        st.warning("該当する用語が見つかりませんでした。")
        return

    for term in glossary:
        term_name = term.get("term", "")
        reading = term.get("reading", "")
        display_name = term.get("display_name", "")
        header = f"{term_name}（{reading}）" if reading else term_name
        if display_name:
            header += f" - {display_name}"

        with st.expander(header):
            st.markdown(term.get("description", ""))
            metaphor = term.get("image_metaphor")
            if metaphor:
                st.caption(f"イメージ: {metaphor}")


def _render_learning_cards() -> None:
    """学習カード一覧タブを描画"""
    st.subheader("学習カード一覧")
    st.caption("投資の知識を少しずつ身につけましょう")

    categories = {
        "all": "すべて",
        "term": "用語",
        "chart": "チャート",
        "indicator": "指標",
        "strategy": "戦略",
        "risk": "リスク",
    }
    selected_cat = st.selectbox(
        "カテゴリ",
        options=list(categories.keys()),
        format_func=lambda x: categories[x],
        key="card_category",
    )

    cards = _api_get("/api/learning/cards", [])
    if not cards:
        st.info("学習カードを読み込み中...")
        return

    if selected_cat != "all":
        cards = [c for c in cards if c.get("category") == selected_cat]

    if not cards:
        st.info("このカテゴリにはカードがありません。")
        return

    for card in cards:
        title = card.get("title", "")
        content = card.get("content", "")

        with st.expander(f":book: {title}"):
            st.markdown(content)


def render() -> None:
    """学習ページを描画"""
    st.title("学習")

    tab_glossary, tab_cards = st.tabs(["用語集", "学習カード"])

    with tab_glossary:
        _render_glossary()

    with tab_cards:
        _render_learning_cards()
