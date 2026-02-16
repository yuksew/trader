"""プロフィールページ - レベル、バッジ、成長グラフ"""

import streamlit as st
import requests

from src.ui.components.stage_indicator import (
    STAGE_NAMES,
    LEVEL_NAMES,
    LEVEL_XP_THRESHOLDS,
    _xp_progress,
)

API_BASE = "http://localhost:8000"


def _api_get(path: str, default=None):
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return default


def _api_put(path: str, data: dict):
    try:
        resp = requests.put(f"{API_BASE}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _render_level_section(profile: dict) -> None:
    """レベル・ステージ情報セクション"""
    stage = profile.get("stage", 1)
    level = profile.get("level", 1)
    xp = profile.get("xp", 0)

    stage_name = STAGE_NAMES.get(stage, "ビギナー")
    level_name = LEVEL_NAMES.get(level, "株の卵")
    xp_in_level, xp_needed, progress = _xp_progress(level, xp)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("ステージ", f"Lv.{stage} {stage_name}")
        st.metric("レベル", f"Lv.{level} {level_name}")
    with col2:
        st.metric("累計XP", f"{xp:,}")
        next_threshold = LEVEL_XP_THRESHOLDS.get(level + 1)
        if next_threshold:
            st.metric("次のレベルまで", f"{next_threshold - xp:,} XP")
        else:
            st.metric("次のレベルまで", "MAX到達!")

    # XPプログレスバー
    next_threshold = LEVEL_XP_THRESHOLDS.get(level + 1)
    if next_threshold:
        st.progress(progress, text=f"XP: {xp:,} / {next_threshold:,}")
    else:
        st.progress(1.0, text=f"XP: {xp:,} (MAX)")

    # ステージ昇格条件
    with st.expander("ステージ昇格条件を確認"):
        conditions = profile.get("stage_conditions", {})
        if conditions:
            for cond_name, cond_data in conditions.items():
                current = cond_data.get("current", 0)
                required = cond_data.get("required", 0)
                met = cond_data.get("met", False)
                icon = ":white_check_mark:" if met else ":black_large_square:"
                st.markdown(f"{icon} **{cond_name}**: {current} / {required}")
        else:
            st.info("昇格条件のデータを取得中...")


def _render_badges_section(badges: list[dict]) -> None:
    """バッジセクション"""
    st.subheader("実績バッジ")

    # バッジカテゴリ定義
    badge_categories = {
        "learning": {"name": "学習系", "badges": [
            "first_step", "knowledge_seed", "term_beginner", "term_intermediate", "good_questioner",
        ]},
        "action": {"name": "行動系", "badges": [
            "watcher", "regular_observer", "early_bird", "habit_master", "practice_bug",
        ]},
        "achievement": {"name": "成果系", "badges": [
            "first_profit", "good_eye", "value_hunter", "trend_surfer", "dividend_collector", "strategist_debut",
        ]},
    }

    earned_ids = {b.get("badge_id") for b in badges}

    for cat_key, cat_info in badge_categories.items():
        st.markdown(f"**{cat_info['name']}**")
        cols = st.columns(min(len(cat_info["badges"]), 5))
        for i, badge_id in enumerate(cat_info["badges"]):
            earned = badge_id in earned_ids
            badge_data = next((b for b in badges if b.get("badge_id") == badge_id), {})
            with cols[i % len(cols)]:
                if earned:
                    st.markdown(
                        f"""<div style="
                            text-align:center;
                            background:#fff3cd;
                            border:2px solid #ffc107;
                            border-radius:8px;
                            padding:8px;
                        ">
                            <div style="font-size:1.5em;">&#127942;</div>
                            <div style="font-size:0.8em; font-weight:bold;">{badge_data.get('name', badge_id)}</div>
                            <div style="font-size:0.7em; color:#666;">{badge_data.get('earned_at', '')[:10]}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""<div style="
                            text-align:center;
                            background:#f0f0f0;
                            border:2px solid #ddd;
                            border-radius:8px;
                            padding:8px;
                            opacity:0.5;
                        ">
                            <div style="font-size:1.5em;">&#128274;</div>
                            <div style="font-size:0.8em;">{badge_id}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )


def _render_growth_section(progress_data: dict) -> None:
    """成長グラフセクション"""
    st.subheader("成長の記録")

    xp_history = progress_data.get("xp_history", [])
    if xp_history:
        import pandas as pd
        df = pd.DataFrame(xp_history)
        if "date" in df.columns and "xp" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            st.line_chart(df.set_index("date")["xp"])
    else:
        st.info("まだ成長データがありません。使い続けると記録されていきます。")

    # 統計サマリ
    stats = progress_data.get("stats", {})
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("累計ログイン", f"{stats.get('total_login_days', 0)}日")
        with col2:
            st.metric("連続ログイン", f"{stats.get('login_streak', 0)}日")
        with col3:
            st.metric("学習カード閲覧", f"{stats.get('cards_viewed', 0)}枚")
        with col4:
            st.metric("なぜ？閲覧", f"{stats.get('why_viewed', 0)}回")


def _render_settings_section(profile: dict) -> None:
    """設定セクション"""
    st.subheader("設定")

    # セーフモード
    safe_mode = profile.get("safe_mode", False)
    new_safe = st.toggle("セーフモード（全ガードレールON）", value=safe_mode, key="safe_mode_toggle")
    if new_safe != safe_mode:
        result = _api_put("/api/user/safe-mode", {"enabled": new_safe})
        if result:
            st.session_state["safe_mode"] = new_safe
            st.success("セーフモードを更新しました。")
            st.rerun()

    # 経験者スキップ
    stage = profile.get("stage", 1)
    if stage == 1:
        st.divider()
        st.markdown("**経験者の方へ**")
        st.caption("投資経験がある場合、一部のガイドをスキップできます。")
        if st.button("経験者としてスタート（Lv.3へ）"):
            result = _api_put("/api/user/safe-mode", {"self_declared_stage": 3})
            if result:
                st.session_state["user_stage"] = 3
                st.success("Lv.3（アクティブ）に設定しました。")
                st.rerun()


def render() -> None:
    """プロフィールページを描画"""
    st.title("プロフィール")

    # ユーザープロフィール取得
    profile = _api_get("/api/user/profile", {})
    if profile:
        # session_stateに同期
        st.session_state["user_stage"] = profile.get("stage", 1)
        st.session_state["user_level"] = profile.get("level", 1)
        st.session_state["user_xp"] = profile.get("xp", 0)

    tab_level, tab_badges, tab_growth, tab_settings = st.tabs(
        ["レベル", "バッジ", "成長の記録", "設定"]
    )

    with tab_level:
        _render_level_section(profile or {})

    with tab_badges:
        badges = _api_get("/api/user/badges", [])
        _render_badges_section(badges)

    with tab_growth:
        progress_data = _api_get("/api/user/progress", {})
        _render_growth_section(progress_data)

    with tab_settings:
        _render_settings_section(profile or {})
