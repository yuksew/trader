"""学習ページ - 用語集、学習カード一覧"""

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


def _render_glossary() -> None:
    """用語集タブを描画"""
    st.subheader("用語集")
    st.caption("投資に関する専門用語をやさしく解説します")

    search = st.text_input("用語を検索", placeholder="例: PER、ボラティリティ", key="glossary_search")

    glossary = _api_get("/api/glossary", [])
    if not glossary:
        st.info("用語集を読み込み中...")
        return

    user_stage = st.session_state.get("user_stage", 1)

    # 検索フィルタリング
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
        header = f"{term_name}（{reading}）" if reading else term_name

        with st.expander(header):
            # ステージ別表示
            if user_stage <= 1:
                plain = term.get("plain_description", term.get("description", ""))
                st.markdown(plain)
                metaphor = term.get("metaphor")
                if metaphor:
                    st.caption(f"イメージ: {metaphor}")
            elif user_stage == 2:
                plain = term.get("plain_description", "")
                formal = term.get("description", "")
                st.markdown(f"{plain}")
                if formal and formal != plain:
                    st.caption(f"専門的には: {formal}")
            else:
                st.markdown(term.get("description", ""))
                formula = term.get("formula")
                if formula:
                    st.code(formula, language=None)

            # XP記録
            _record_glossary_viewed(term.get("id", term_name))


def _render_learning_cards() -> None:
    """学習カード一覧タブを描画"""
    st.subheader("学習カード一覧")
    st.caption("投資の知識を少しずつ身につけましょう")

    # カテゴリフィルタ
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

    # 閲覧済みフラグの表示
    viewed_ids = st.session_state.get("viewed_card_ids", set())

    if not cards:
        st.info("このカテゴリにはカードがありません。")
        return

    for card in cards:
        card_id = card.get("id", 0)
        title = card.get("title", "")
        content = card.get("content", "")
        is_viewed = card_id in viewed_ids or card.get("viewed", False)

        icon = "white_check_mark" if is_viewed else "book"
        with st.expander(f":{icon}: {title}"):
            st.markdown(content)
            if not is_viewed:
                if st.button("読んだ", key=f"read_card_{card_id}"):
                    if "viewed_card_ids" not in st.session_state:
                        st.session_state["viewed_card_ids"] = set()
                    st.session_state["viewed_card_ids"].add(card_id)
                    _record_card_viewed(card_id)
                    st.rerun()


def _record_glossary_viewed(term_id) -> None:
    """用語閲覧をAPI記録"""
    try:
        requests.post(
            f"{API_BASE}/api/user/xp",
            json={"action_type": "glossary_viewed", "target_id": str(term_id)},
            timeout=5,
        )
    except Exception:
        pass


def _record_card_viewed(card_id: int) -> None:
    """カード閲覧をAPI記録"""
    try:
        requests.post(
            f"{API_BASE}/api/learning/cards/{card_id}/viewed",
            timeout=5,
        )
    except Exception:
        pass


def render() -> None:
    """学習ページを描画"""
    st.title("学習")

    tab_glossary, tab_cards = st.tabs(["用語集", "学習カード"])

    with tab_glossary:
        _render_glossary()

    with tab_cards:
        _render_learning_cards()
