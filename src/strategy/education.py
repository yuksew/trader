"""教育機能: XP管理、ステージ判定、バッジ判定ロジック.

ユーザーの行動ログに基づき XP を付与し、レベル・ステージの昇格と
バッジ獲得を判定する。連続ログイン管理も担当する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# レベル定義
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LevelDef:
    """レベル定義."""

    level: int
    name: str
    required_xp: int
    stage: int  # そのレベルが属するステージ (1〜4)


LEVEL_TABLE: list[LevelDef] = [
    LevelDef(level=1,  name="株の卵",           required_xp=0,     stage=1),
    LevelDef(level=2,  name="新芽の投資家",     required_xp=100,   stage=1),
    LevelDef(level=3,  name="歩き始めた投資家", required_xp=300,   stage=1),
    LevelDef(level=4,  name="市場の探検家",     required_xp=600,   stage=2),
    LevelDef(level=5,  name="見習いトレーダー", required_xp=1000,  stage=2),
    LevelDef(level=6,  name="銘柄ハンター",     required_xp=1500,  stage=2),
    LevelDef(level=7,  name="チャート読み",     required_xp=2200,  stage=3),
    LevelDef(level=8,  name="シグナル使い",     required_xp=3000,  stage=3),
    LevelDef(level=9,  name="戦略家の卵",       required_xp=4000,  stage=3),
    LevelDef(level=10, name="独立投資家",       required_xp=5500,  stage=4),
    LevelDef(level=11, name="ポートフォリオ職人", required_xp=7000, stage=4),
    LevelDef(level=12, name="マーケットメンター", required_xp=9000, stage=4),
    LevelDef(level=13, name="相場の達人",       required_xp=11500, stage=4),
    LevelDef(level=14, name="投資マスター",     required_xp=14500, stage=4),
    LevelDef(level=15, name="レジェンド",       required_xp=18000, stage=4),
]


# ---------------------------------------------------------------------------
# XP アクション定義
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class XpAction:
    """XP 獲得アクションの定義."""

    action_type: str
    xp: int
    daily_limit: int | None  # None = 無制限
    weekly_limit: int | None  # None = 無制限
    monthly_limit: int | None  # None = 無制限
    once_per_item: bool  # True = アイテムごとに1回だけ


XP_ACTIONS: dict[str, XpAction] = {
    "dashboard_open": XpAction(
        action_type="dashboard_open", xp=5,
        daily_limit=1, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
    "stock_detail_view": XpAction(
        action_type="stock_detail_view", xp=3,
        daily_limit=5, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
    "why_explanation_view": XpAction(
        action_type="why_explanation_view", xp=10,
        daily_limit=3, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
    "learning_card_view": XpAction(
        action_type="learning_card_view", xp=8,
        daily_limit=None, weekly_limit=None, monthly_limit=None,
        once_per_item=True,
    ),
    "weekly_report_view": XpAction(
        action_type="weekly_report_view", xp=15,
        daily_limit=None, weekly_limit=1, monthly_limit=None,
        once_per_item=False,
    ),
    "signal_hit": XpAction(
        action_type="signal_hit", xp=20,
        daily_limit=None, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
    "simulation_run": XpAction(
        action_type="simulation_run", xp=5,
        daily_limit=3, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
    "monthly_review": XpAction(
        action_type="monthly_review", xp=30,
        daily_limit=None, weekly_limit=None, monthly_limit=1,
        once_per_item=False,
    ),
    "daily_login": XpAction(
        action_type="daily_login", xp=3,  # 基本値。連続日数で上昇
        daily_limit=1, weekly_limit=None, monthly_limit=None,
        once_per_item=False,
    ),
}

# 連続ログインボーナスの XP テーブル
LOGIN_STREAK_XP: dict[int, int] = {
    1: 3,
    3: 5,
    7: 8,
    14: 10,
    30: 15,
}


# ---------------------------------------------------------------------------
# バッジ定義
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BadgeDef:
    """バッジ定義."""

    badge_id: str
    name: str
    description: str
    category: str  # "learning" | "action" | "achievement"


BADGE_DEFINITIONS: dict[str, BadgeDef] = {
    # 学習系
    "first_step": BadgeDef(
        badge_id="first_step",
        name="はじめの一歩",
        description="初めて「なぜ？」説明を閲覧した",
        category="learning",
    ),
    "seed_of_knowledge": BadgeDef(
        badge_id="seed_of_knowledge",
        name="知識の種",
        description="学習カードを10枚閲覧した",
        category="learning",
    ),
    "glossary_beginner": BadgeDef(
        badge_id="glossary_beginner",
        name="用語マスター初級",
        description="用語解説を10種閲覧した",
        category="learning",
    ),
    "glossary_intermediate": BadgeDef(
        badge_id="glossary_intermediate",
        name="用語マスター中級",
        description="用語解説を30種閲覧した",
        category="learning",
    ),
    "good_questioner": BadgeDef(
        badge_id="good_questioner",
        name="質問上手",
        description="「なぜ？」を30回閲覧した",
        category="learning",
    ),
    # 行動系
    "watcher": BadgeDef(
        badge_id="watcher",
        name="ウォッチャー",
        description="銘柄詳細を50回確認した",
        category="action",
    ),
    "regular_observer": BadgeDef(
        badge_id="regular_observer",
        name="定点観測者",
        description="7日連続でダッシュボードを開いた",
        category="action",
    ),
    "early_bird": BadgeDef(
        badge_id="early_bird",
        name="早起き投資家",
        description="朝9時前にダッシュボードを開いた（10回）",
        category="action",
    ),
    "habit_master": BadgeDef(
        badge_id="habit_master",
        name="習慣の達人",
        description="30日連続でログインした",
        category="action",
    ),
    "practice_addict": BadgeDef(
        badge_id="practice_addict",
        name="練習の虫",
        description="シミュレーションを20回実行した",
        category="action",
    ),
    # 成果系
    "first_profit": BadgeDef(
        badge_id="first_profit",
        name="初めての利益",
        description="初めて利益を確定した",
        category="achievement",
    ),
    "good_eye": BadgeDef(
        badge_id="good_eye",
        name="目利き",
        description="シグナルに従って購入し利益を得た（3回）",
        category="achievement",
    ),
    "value_hunter": BadgeDef(
        badge_id="value_hunter",
        name="割安ハンター",
        description="割安シグナルの銘柄で利益を得た",
        category="achievement",
    ),
    "trend_surfer": BadgeDef(
        badge_id="trend_surfer",
        name="トレンドサーファー",
        description="ゴールデンクロスシグナルの銘柄で利益を得た",
        category="achievement",
    ),
    "dividend_collector": BadgeDef(
        badge_id="dividend_collector",
        name="配当コレクター",
        description="配当金を3回受け取った",
        category="achievement",
    ),
    "strategist_debut": BadgeDef(
        badge_id="strategist_debut",
        name="戦略家デビュー",
        description="スクリーニング条件を初めてカスタマイズした",
        category="achievement",
    ),
}


# ---------------------------------------------------------------------------
# ステージ昇格条件
# ---------------------------------------------------------------------------

@dataclass
class StageRequirements:
    """ステージ昇格に必要な条件."""

    total_login_days: int
    why_views: int | None  # 「なぜ？」閲覧回数
    glossary_views: int | None  # 用語解説閲覧種類数
    card_views: int | None  # 学習カード閲覧枚数
    weekly_report_views: int | None  # 週次レポート閲覧回数
    simulation_runs: int | None  # シミュレーション利用回数
    screening_customized: bool  # スクリーニング条件カスタマイズ
    stop_loss_customized: bool  # 損切りルールカスタマイズ
    health_yellow_months: int | None  # 健全度黄以上維持月数
    review_views: int | None  # 振り返りレポート確認回数


STAGE_REQUIREMENTS: dict[int, StageRequirements] = {
    # Lv.1 -> Lv.2
    2: StageRequirements(
        total_login_days=30,
        why_views=3,
        glossary_views=5,
        card_views=10,
        weekly_report_views=5,
        simulation_runs=None,
        screening_customized=False,
        stop_loss_customized=False,
        health_yellow_months=None,
        review_views=None,
    ),
    # Lv.2 -> Lv.3
    3: StageRequirements(
        total_login_days=90,
        why_views=15,
        glossary_views=15,
        card_views=30,
        weekly_report_views=15,
        simulation_runs=3,
        screening_customized=False,
        stop_loss_customized=True,
        health_yellow_months=None,
        review_views=5,
    ),
    # Lv.3 -> Lv.4
    4: StageRequirements(
        total_login_days=180,
        why_views=None,
        glossary_views=None,
        card_views=None,
        weekly_report_views=None,
        simulation_runs=None,
        screening_customized=True,
        stop_loss_customized=False,
        health_yellow_months=3,
        review_views=10,
    ),
}


# ---------------------------------------------------------------------------
# ユーザープロフィール
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """ユーザーの教育プロフィール."""

    user_id: int
    stage: int = 1
    level: int = 1
    xp: int = 0
    safe_mode: bool = False
    login_streak: int = 0
    last_login_date: date | None = None
    total_login_days: int = 0
    stage_upgraded_at: datetime | None = None
    self_declared_stage: int | None = None
    created_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# XP 管理
# ---------------------------------------------------------------------------

@dataclass
class XpResult:
    """XP 付与結果."""

    granted: bool
    xp_earned: int
    reason: str  # 付与/非付与の理由
    new_total_xp: int
    level_up: bool
    new_level: int | None
    stage_up: bool
    new_stage: int | None
    badges_earned: list[str]


def _get_login_streak_xp(streak: int) -> int:
    """連続ログイン日数に応じた XP を返す."""
    result = 3  # 基本値
    for threshold, xp in sorted(LOGIN_STREAK_XP.items()):
        if streak >= threshold:
            result = xp
    return result


def check_frequency_limit(
    action_type: str,
    xp_logs: list[dict[str, Any]],
    now: datetime | None = None,
    item_id: str | None = None,
) -> tuple[bool, str]:
    """XP アクションの頻度制限をチェックする.

    Args:
        action_type: アクション種別
        xp_logs: ユーザーの既存 XP ログ。各要素は
            {"action_type", "created_at", "item_id"(optional)} を含む dict
        now: 現在日時 (テスト用)
        item_id: アイテム ID (once_per_item 用)

    Returns:
        (制限内か, 理由) のタプル
    """
    if now is None:
        now = datetime.now()

    action_def = XP_ACTIONS.get(action_type)
    if action_def is None:
        return False, f"不明なアクション種別: {action_type}"

    # once_per_item チェック
    if action_def.once_per_item and item_id is not None:
        for log in xp_logs:
            if (
                log.get("action_type") == action_type
                and log.get("item_id") == item_id
            ):
                return False, f"このアイテムは既に閲覧済みです"

    today = now.date()

    # 日次制限
    if action_def.daily_limit is not None:
        daily_count = sum(
            1 for log in xp_logs
            if log.get("action_type") == action_type
            and _to_date(log.get("created_at")) == today
        )
        if daily_count >= action_def.daily_limit:
            return False, f"本日の{action_type}の上限({action_def.daily_limit}回)に達しています"

    # 週次制限
    if action_def.weekly_limit is not None:
        week_start = today - timedelta(days=today.weekday())
        weekly_count = sum(
            1 for log in xp_logs
            if log.get("action_type") == action_type
            and _to_date(log.get("created_at")) is not None
            and _to_date(log.get("created_at")) >= week_start
        )
        if weekly_count >= action_def.weekly_limit:
            return False, f"今週の{action_type}の上限({action_def.weekly_limit}回)に達しています"

    # 月次制限
    if action_def.monthly_limit is not None:
        month_start = today.replace(day=1)
        monthly_count = sum(
            1 for log in xp_logs
            if log.get("action_type") == action_type
            and _to_date(log.get("created_at")) is not None
            and _to_date(log.get("created_at")) >= month_start
        )
        if monthly_count >= action_def.monthly_limit:
            return False, f"今月の{action_type}の上限({action_def.monthly_limit}回)に達しています"

    return True, "OK"


def _to_date(value: Any) -> date | None:
    """datetime/date/文字列を date に変換する."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


# ---------------------------------------------------------------------------
# レベル・ステージ判定
# ---------------------------------------------------------------------------

def determine_level(xp: int) -> LevelDef:
    """XP からレベルを判定する.

    Args:
        xp: 累計 XP

    Returns:
        該当する LevelDef
    """
    result = LEVEL_TABLE[0]
    for level_def in LEVEL_TABLE:
        if xp >= level_def.required_xp:
            result = level_def
        else:
            break
    return result


def get_xp_for_next_level(current_level: int) -> int | None:
    """次のレベルに必要な XP を返す.

    Args:
        current_level: 現在のレベル

    Returns:
        次のレベルの必要 XP。最大レベルの場合は None
    """
    for level_def in LEVEL_TABLE:
        if level_def.level == current_level + 1:
            return level_def.required_xp
    return None


def check_stage_promotion(
    current_stage: int,
    user_stats: dict[str, Any],
) -> tuple[bool, int, list[str]]:
    """ステージ昇格条件をチェックする.

    Args:
        current_stage: 現在のステージ (1〜4)
        user_stats: ユーザーの行動統計。以下のキーを含む dict:
            - total_login_days: 累計ログイン日数
            - why_views: 「なぜ？」閲覧回数
            - glossary_views: 用語解説閲覧種類数
            - card_views: 学習カード閲覧枚数
            - weekly_report_views: 週次レポート閲覧回数
            - simulation_runs: シミュレーション利用回数
            - screening_customized: スクリーニング条件カスタマイズ済みか
            - stop_loss_customized: 損切りルールカスタマイズ済みか
            - health_yellow_months: 健全度黄以上維持月数
            - review_views: 振り返りレポート確認回数

    Returns:
        (昇格可能か, 新ステージ, 未達条件リスト) のタプル
    """
    if current_stage >= 4:
        return False, 4, []

    next_stage = current_stage + 1
    reqs = STAGE_REQUIREMENTS.get(next_stage)
    if reqs is None:
        return False, current_stage, []

    unmet: list[str] = []

    if user_stats.get("total_login_days", 0) < reqs.total_login_days:
        unmet.append(
            f"累計利用日数: {user_stats.get('total_login_days', 0)}/{reqs.total_login_days}日"
        )

    if reqs.why_views is not None:
        if user_stats.get("why_views", 0) < reqs.why_views:
            unmet.append(
                f"「なぜ？」閲覧: {user_stats.get('why_views', 0)}/{reqs.why_views}回"
            )

    if reqs.glossary_views is not None:
        if user_stats.get("glossary_views", 0) < reqs.glossary_views:
            unmet.append(
                f"用語解説閲覧: {user_stats.get('glossary_views', 0)}/{reqs.glossary_views}種"
            )

    if reqs.card_views is not None:
        if user_stats.get("card_views", 0) < reqs.card_views:
            unmet.append(
                f"学習カード閲覧: {user_stats.get('card_views', 0)}/{reqs.card_views}枚"
            )

    if reqs.weekly_report_views is not None:
        if user_stats.get("weekly_report_views", 0) < reqs.weekly_report_views:
            unmet.append(
                f"週次レポート閲覧: {user_stats.get('weekly_report_views', 0)}/{reqs.weekly_report_views}回"
            )

    if reqs.simulation_runs is not None:
        if user_stats.get("simulation_runs", 0) < reqs.simulation_runs:
            unmet.append(
                f"シミュレーション利用: {user_stats.get('simulation_runs', 0)}/{reqs.simulation_runs}回"
            )

    if reqs.screening_customized and not user_stats.get("screening_customized", False):
        unmet.append("スクリーニング条件カスタマイズ: 未達")

    if reqs.stop_loss_customized and not user_stats.get("stop_loss_customized", False):
        unmet.append("損切りルールカスタマイズ: 未達")

    if reqs.health_yellow_months is not None:
        if user_stats.get("health_yellow_months", 0) < reqs.health_yellow_months:
            unmet.append(
                f"健全度黄以上維持: {user_stats.get('health_yellow_months', 0)}/{reqs.health_yellow_months}ヶ月"
            )

    if reqs.review_views is not None:
        if user_stats.get("review_views", 0) < reqs.review_views:
            unmet.append(
                f"振り返りレポート確認: {user_stats.get('review_views', 0)}/{reqs.review_views}回"
            )

    can_promote = len(unmet) == 0
    new_stage = next_stage if can_promote else current_stage
    return can_promote, new_stage, unmet


# ---------------------------------------------------------------------------
# バッジ判定
# ---------------------------------------------------------------------------

def check_badge_eligibility(
    user_stats: dict[str, Any],
    earned_badges: set[str],
) -> list[str]:
    """新たに獲得可能なバッジを判定する.

    Args:
        user_stats: ユーザーの行動統計。以下のキーを含む dict:
            - why_views: 「なぜ？」閲覧回数
            - card_views: 学習カード閲覧枚数
            - glossary_views: 用語解説閲覧種類数
            - stock_detail_views: 銘柄詳細確認回数
            - login_streak: 現在の連続ログイン日数
            - early_logins: 朝9時前のダッシュボード閲覧回数
            - simulation_runs: シミュレーション実行回数
            - first_profit: 初利益確定済みか (bool)
            - signal_profits: シグナル追従利益回数
            - value_signal_profit: 割安シグナルで利益を得たか (bool)
            - golden_cross_profit: ゴールデンクロスで利益を得たか (bool)
            - dividends_received: 配当受取回数
            - screening_customized: スクリーニングカスタマイズ済みか (bool)
        earned_badges: 既に獲得済みのバッジ ID セット

    Returns:
        新たに獲得可能なバッジ ID のリスト
    """
    new_badges: list[str] = []

    def _check(badge_id: str, condition: bool) -> None:
        if badge_id not in earned_badges and condition:
            new_badges.append(badge_id)

    # 学習系
    _check("first_step", user_stats.get("why_views", 0) >= 1)
    _check("seed_of_knowledge", user_stats.get("card_views", 0) >= 10)
    _check("glossary_beginner", user_stats.get("glossary_views", 0) >= 10)
    _check("glossary_intermediate", user_stats.get("glossary_views", 0) >= 30)
    _check("good_questioner", user_stats.get("why_views", 0) >= 30)

    # 行動系
    _check("watcher", user_stats.get("stock_detail_views", 0) >= 50)
    _check("regular_observer", user_stats.get("login_streak", 0) >= 7)
    _check("early_bird", user_stats.get("early_logins", 0) >= 10)
    _check("habit_master", user_stats.get("login_streak", 0) >= 30)
    _check("practice_addict", user_stats.get("simulation_runs", 0) >= 20)

    # 成果系
    _check("first_profit", user_stats.get("first_profit", False) is True)
    _check("good_eye", user_stats.get("signal_profits", 0) >= 3)
    _check("value_hunter", user_stats.get("value_signal_profit", False) is True)
    _check("trend_surfer", user_stats.get("golden_cross_profit", False) is True)
    _check("dividend_collector", user_stats.get("dividends_received", 0) >= 3)
    _check("strategist_debut", user_stats.get("screening_customized", False) is True)

    return new_badges


# ---------------------------------------------------------------------------
# 連続ログイン管理
# ---------------------------------------------------------------------------

def update_login_streak(
    profile: UserProfile,
    login_date: date | None = None,
) -> tuple[UserProfile, int]:
    """連続ログイン日数を更新し、ログインボーナス XP を返す.

    Args:
        profile: ユーザープロフィール (変更される)
        login_date: ログイン日 (テスト用。None の場合は今日)

    Returns:
        (更新後プロフィール, ログインボーナスXP) のタプル
    """
    if login_date is None:
        login_date = date.today()

    if profile.last_login_date is None:
        # 初回ログイン
        profile.login_streak = 1
        profile.total_login_days = 1
        profile.last_login_date = login_date
        return profile, _get_login_streak_xp(1)

    if login_date == profile.last_login_date:
        # 同日の再ログイン: XP 0 (既に付与済み)
        return profile, 0

    days_diff = (login_date - profile.last_login_date).days

    if days_diff == 1:
        # 連続ログイン
        profile.login_streak += 1
    elif days_diff > 1:
        # 連続途切れ
        profile.login_streak = 1
    else:
        # 過去の日付 (異常ケース): 何もしない
        return profile, 0

    profile.total_login_days += 1
    profile.last_login_date = login_date

    xp = _get_login_streak_xp(profile.login_streak)
    return profile, xp


# ---------------------------------------------------------------------------
# XP 付与統合処理
# ---------------------------------------------------------------------------

def grant_xp(
    profile: UserProfile,
    action_type: str,
    xp_logs: list[dict[str, Any]],
    user_stats: dict[str, Any],
    earned_badges: set[str],
    now: datetime | None = None,
    item_id: str | None = None,
) -> XpResult:
    """XP を付与し、レベル・ステージ昇格とバッジ獲得を判定する.

    Args:
        profile: ユーザープロフィール (変更される)
        action_type: アクション種別
        xp_logs: 既存の XP ログ
        user_stats: ユーザーの行動統計
        earned_badges: 既に獲得済みのバッジ ID セット
        now: 現在日時 (テスト用)
        item_id: アイテム ID (once_per_item 用)

    Returns:
        XpResult
    """
    if now is None:
        now = datetime.now()

    # 頻度制限チェック
    allowed, reason = check_frequency_limit(
        action_type, xp_logs, now=now, item_id=item_id,
    )
    if not allowed:
        return XpResult(
            granted=False,
            xp_earned=0,
            reason=reason,
            new_total_xp=profile.xp,
            level_up=False,
            new_level=None,
            stage_up=False,
            new_stage=None,
            badges_earned=[],
        )

    # XP 算出
    action_def = XP_ACTIONS.get(action_type)
    if action_def is None:
        return XpResult(
            granted=False,
            xp_earned=0,
            reason=f"不明なアクション種別: {action_type}",
            new_total_xp=profile.xp,
            level_up=False,
            new_level=None,
            stage_up=False,
            new_stage=None,
            badges_earned=[],
        )

    xp_earned = action_def.xp

    # 連続ログインの場合はボーナス XP
    if action_type == "daily_login":
        xp_earned = _get_login_streak_xp(profile.login_streak)

    old_level = profile.level
    old_stage = profile.stage

    # XP 加算
    profile.xp += xp_earned

    # レベル判定
    new_level_def = determine_level(profile.xp)
    profile.level = new_level_def.level
    level_up = new_level_def.level > old_level

    # ステージ判定 (降格なし)
    can_promote, new_stage, _ = check_stage_promotion(profile.stage, user_stats)
    if can_promote and new_stage > profile.stage:
        profile.stage = new_stage
        profile.stage_upgraded_at = now

    stage_up = profile.stage > old_stage

    # バッジ判定
    new_badges = check_badge_eligibility(user_stats, earned_badges)

    return XpResult(
        granted=True,
        xp_earned=xp_earned,
        reason="OK",
        new_total_xp=profile.xp,
        level_up=level_up,
        new_level=new_level_def.level if level_up else None,
        stage_up=stage_up,
        new_stage=profile.stage if stage_up else None,
        badges_earned=new_badges,
    )
