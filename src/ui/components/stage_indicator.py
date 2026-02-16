"""ステージ・レベル・XPバー表示コンポーネント"""

import streamlit as st

STAGE_NAMES = {
    1: "ビギナー",
    2: "気づき",
    3: "アクティブ",
    4: "ストラテジスト",
}

LEVEL_NAMES = {
    1: "株の卵",
    2: "新芽の投資家",
    3: "歩き始めた投資家",
    4: "市場の探検家",
    5: "見習いトレーダー",
    6: "銘柄ハンター",
    7: "チャート読み",
    8: "シグナル使い",
    9: "戦略家の卵",
    10: "独立投資家",
    11: "熟練投資家",
    12: "マーケットマスター",
    13: "ベテラントレーダー",
    14: "投資の達人",
    15: "レジェンド",
}

LEVEL_XP_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2200,
    8: 3000,
    9: 4000,
    10: 5500,
    11: 7000,
    12: 9000,
    13: 11500,
    14: 14500,
    15: 18000,
}


def _get_user_profile() -> dict:
    """session_stateからユーザープロフィールを取得"""
    return {
        "stage": st.session_state.get("user_stage", 1),
        "level": st.session_state.get("user_level", 1),
        "xp": st.session_state.get("user_xp", 0),
    }


def _xp_progress(level: int, xp: int) -> tuple[int, int, float]:
    """現在レベルでのXP進捗を計算する

    Returns:
        (current_xp_in_level, xp_needed_for_next, progress_ratio)
    """
    current_threshold = LEVEL_XP_THRESHOLDS.get(level, 0)
    next_threshold = LEVEL_XP_THRESHOLDS.get(level + 1)
    if next_threshold is None:
        # 最大レベル
        return xp - current_threshold, 0, 1.0
    xp_in_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold
    progress = xp_in_level / xp_needed if xp_needed > 0 else 1.0
    return xp_in_level, xp_needed, min(progress, 1.0)


def render_stage_indicator() -> None:
    """ダッシュボード上部にステージ・レベル・XPバーを表示"""
    profile = _get_user_profile()
    stage = profile["stage"]
    level = profile["level"]
    xp = profile["xp"]

    stage_name = STAGE_NAMES.get(stage, "ビギナー")
    level_name = LEVEL_NAMES.get(level, "株の卵")
    xp_in_level, xp_needed, progress = _xp_progress(level, xp)

    next_threshold = LEVEL_XP_THRESHOLDS.get(level + 1)
    if next_threshold is not None:
        xp_text = f"XP: {xp} / {next_threshold}"
    else:
        xp_text = f"XP: {xp} (MAX)"

    st.markdown(
        f"""<div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 10px 16px;
            border-radius: 8px;
            color: white;
            margin-bottom: 8px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:1.1em;">
                    Lv.{stage} {stage_name} &nbsp;|&nbsp; Lv.{level} {level_name}
                </span>
                <span style="font-size:0.9em; opacity:0.9;">{xp_text}</span>
            </div>
            <div style="
                background: rgba(255,255,255,0.3);
                border-radius: 4px;
                height: 8px;
                margin-top: 6px;
                overflow: hidden;
            ">
                <div style="
                    background: white;
                    height: 100%;
                    width: {progress * 100:.0f}%;
                    border-radius: 4px;
                    transition: width 0.3s;
                "></div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_stage_badge_compact() -> str:
    """サイドバー用のコンパクトなステージバッジHTMLを返す"""
    profile = _get_user_profile()
    stage = profile["stage"]
    level_name = LEVEL_NAMES.get(profile["level"], "株の卵")
    stage_name = STAGE_NAMES.get(stage, "ビギナー")
    return f"Lv.{stage} {stage_name} | {level_name}"
