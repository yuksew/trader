"""Education endpoints: profile, XP, badges, glossary, learning cards, explanations."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import (
    AlertExplanationResponse,
    BadgeResponse,
    CardViewedResponse,
    GuardrailsResponse,
    LearningCardResponse,
    GlossaryTermResponse,
    SafeModeRequest,
    SafeModeResponse,
    SignalExplanationResponse,
    UserProfileResponse,
    UserProgressResponse,
    XPAddRequest,
    XPAddResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Level / Stage definitions
# ---------------------------------------------------------------------------

LEVEL_TABLE: list[dict] = [
    {"level": 1,  "name": "株の卵",         "xp": 0,     "stage": 1},
    {"level": 2,  "name": "新芽の投資家",   "xp": 100,   "stage": 1},
    {"level": 3,  "name": "歩き始めた投資家","xp": 300,   "stage": 1},
    {"level": 4,  "name": "市場の探検家",   "xp": 600,   "stage": 2},
    {"level": 5,  "name": "見習いトレーダー","xp": 1000,  "stage": 2},
    {"level": 6,  "name": "銘柄ハンター",   "xp": 1500,  "stage": 2},
    {"level": 7,  "name": "チャート読み",   "xp": 2200,  "stage": 3},
    {"level": 8,  "name": "シグナル使い",   "xp": 3000,  "stage": 3},
    {"level": 9,  "name": "戦略家の卵",     "xp": 4000,  "stage": 3},
    {"level": 10, "name": "独立投資家",     "xp": 5500,  "stage": 4},
    {"level": 11, "name": "マーケット職人", "xp": 7000,  "stage": 4},
    {"level": 12, "name": "ベテラン投資家", "xp": 9000,  "stage": 4},
    {"level": 13, "name": "相場の達人",     "xp": 11500, "stage": 4},
    {"level": 14, "name": "投資マスター",   "xp": 14500, "stage": 4},
    {"level": 15, "name": "伝説の投資家",   "xp": 18000, "stage": 4},
]

STAGE_NAMES = {1: "ビギナー", 2: "気づき", 3: "アクティブ", 4: "ストラテジスト"}

XP_ACTIONS: dict[str, dict] = {
    "dashboard_open":   {"xp": 5,  "daily_limit": 1},
    "stock_detail":     {"xp": 3,  "daily_limit": 5},
    "why_viewed":       {"xp": 10, "daily_limit": 3},
    "card_viewed":      {"xp": 8,  "daily_limit": None},
    "weekly_report":    {"xp": 15, "daily_limit": None},
    "signal_hit":       {"xp": 20, "daily_limit": None},
    "simulation_run":   {"xp": 5,  "daily_limit": 3},
    "monthly_review":   {"xp": 30, "daily_limit": None},
    "login_streak":     {"xp": 3,  "daily_limit": 1},
}

# ---------------------------------------------------------------------------
# Glossary data (in-memory, matching spec section 4.1)
# ---------------------------------------------------------------------------

GLOSSARY: list[dict] = [
    {
        "term": "PER",
        "reading": "ピーイーアール",
        "display_name_lv1": "お買い得度",
        "description_lv1": "利益の何倍の値段がついているかを示します。低いほどお買い得かもしれません。",
        "description_lv2": "株価収益率（PER）は、株価を1株あたり利益で割ったもの。業界平均と比べて低ければ割安の可能性があります。",
        "description_lv3": "PER = 株価 / EPS。同業他社比較、過去PERレンジとの比較で割安度を判定。成長株は高PERでも正当化されることがある。",
        "description_lv4": "Price-to-Earnings Ratio。Forward PER / Trailing PERの区別、PEG Ratioとの併用分析が有効。",
        "image_metaphor": "利益の何倍の値段か",
        "related_features": ["screening", "signals"],
    },
    {
        "term": "PBR",
        "reading": "ピービーアール",
        "display_name_lv1": "資産に対する割安度",
        "description_lv1": "会社の持ち物に対して株価が安いかどうかを見ます。",
        "description_lv2": "株価純資産倍率（PBR）は、株価を1株あたり純資産で割ったもの。1倍以下は帳簿上の資産より安く買える状態です。",
        "description_lv3": "PBR = 株価 / BPS。解散価値との比較。ただしBPSには含み益/含み損が反映されないケースもある。",
        "description_lv4": "Price-to-Book Ratio。ROEとの関係（PBR = PER x ROE）で理論PBRを導出可能。",
        "image_metaphor": "会社の持ち物に対して安いか",
        "related_features": ["screening"],
    },
    {
        "term": "RSI",
        "reading": "アールエスアイ",
        "display_name_lv1": "買われすぎ/売られすぎメーター",
        "description_lv1": "株がどれくらい買われすぎ・売られすぎかを示す温度計のようなものです。",
        "description_lv2": "相対力指数（RSI）は0〜100の値。70以上は買われすぎ、30以下は売られすぎのサインとされます。",
        "description_lv3": "RSI(14) = 100 - 100/(1+RS)。ダイバージェンスの検出やサポートラインとの組み合わせが有効。",
        "description_lv4": "Relative Strength Index。Wilder方式の平滑化。RSIのRSIやStochastic RSIとの併用で精度向上。",
        "image_metaphor": "温度計のようなもの",
        "related_features": ["signals", "chart"],
    },
    {
        "term": "ボラティリティ",
        "reading": "ぼらてぃりてぃ",
        "display_name_lv1": "値動きの激しさ",
        "description_lv1": "株価がどれくらい激しく上下するかを示します。ジェットコースター度のようなものです。",
        "description_lv2": "価格変動の大きさ。高いほどリスクが大きいが、リターンの機会も大きい。",
        "description_lv3": "ヒストリカル・ボラティリティは過去の日次リターンの標準偏差（年率換算）。20日/60日HVが一般的。",
        "description_lv4": "HV / IV区別。VIXとの相関分析。GARCH modelによるボラティリティ予測が可能。",
        "image_metaphor": "ジェットコースター度",
        "related_features": ["risk", "alerts"],
    },
    {
        "term": "ドローダウン",
        "reading": "どろーだうん",
        "display_name_lv1": "ピークからの下がり幅",
        "description_lv1": "一番高い所からどれだけ落ちたかを示します。",
        "description_lv2": "最高値からの下落率。最大ドローダウンが大きいほど、過去に大きな損失を経験したことを示します。",
        "description_lv3": "Max Drawdown = (谷の値 - 直前のピーク) / 直前のピーク。回復期間の分析も重要。",
        "description_lv4": "MDD。Calmar Ratio（年率リターン/MDD）で効率性評価。Conditional DDも考慮。",
        "image_metaphor": "一番高い所からどれだけ落ちたか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "シャープレシオ",
        "reading": "しゃーぷれしお",
        "display_name_lv1": "リスクに見合ったリターンか",
        "description_lv1": "危険を冒した分だけちゃんと儲かっているかを見る指標です。",
        "description_lv2": "リスク（値動きの大きさ）に対してどれだけリターンを得られているか。高いほど効率的。",
        "description_lv3": "Sharpe Ratio = (ポートフォリオリターン - 無リスク金利) / ポートフォリオの標準偏差。1以上が望ましい。",
        "description_lv4": "日次リターンからの年率換算時の√252の使用。Sortino Ratioとの使い分け。",
        "image_metaphor": "危険を冒した分だけ儲かっているか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "β値",
        "reading": "べーたち",
        "display_name_lv1": "市場との連動度",
        "description_lv1": "市場全体が動いた時に、この銘柄がどれくらい影響を受けるかを示します。",
        "description_lv2": "β（ベータ）値は市場全体との連動性。1より大きいと市場より大きく動き、1未満だとマイルドな動き。",
        "description_lv3": "β = Cov(Ri, Rm) / Var(Rm)。TOPIX or 日経225との相関で算出。セクターベータとの比較も有効。",
        "description_lv4": "Barra Risk Model等のマルチファクターβとの比較。Adjusted Beta = 0.67*Raw + 0.33*1。",
        "image_metaphor": "市場が風邪をひいた時の影響度",
        "related_features": ["risk"],
    },
    {
        "term": "HHI",
        "reading": "エイチエイチアイ",
        "display_name_lv1": "偏り度合い",
        "description_lv1": "卵を一つのカゴに盛りすぎていないかを見る指標です。分散が大事！",
        "description_lv2": "集中度指数。ポートフォリオの銘柄偏りを数値化。値が高いほど特定銘柄に偏っています。",
        "description_lv3": "HHI = Σ(wi^2)。0〜10000のスケール。2500超は高集中。セクター別HHIの算出も有効。",
        "description_lv4": "Herfindahl-Hirschman Index。Effective N = 1/HHI。セクター/地域/時価総額別の分解分析。",
        "image_metaphor": "卵を一つのカゴに盛りすぎていないか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "VaR",
        "reading": "ブイエーアール",
        "display_name_lv1": "最悪ケースの損失額",
        "description_lv1": "運が悪い日の最大被害額です。「最悪これくらい損するかも」という目安。",
        "description_lv2": "バリュー・アット・リスク。95%の確率で、1日にこの金額以上は損しないという指標。",
        "description_lv3": "VaR(95%) = ポートフォリオ価値 × σ × 1.645。ヒストリカルVaR / パラメトリックVaRの区別。",
        "description_lv4": "CVaR（Expected Shortfall）との併用。Monte Carlo VaR。Cornish-Fisher展開による補正。",
        "image_metaphor": "運が悪い日の最大被害額",
        "related_features": ["risk"],
    },
    {
        "term": "ゴールデンクロス",
        "reading": "ごーるでんくろす",
        "display_name_lv1": "上昇トレンドのサイン",
        "description_lv1": "最近の勢いが長期の流れを追い越しました。上がり始めのサインかもしれません。",
        "description_lv2": "短期移動平均線が長期移動平均線を下から上に抜ける現象。買いシグナルとされます。",
        "description_lv3": "5MA/20MAまたは25MA/75MAの交差。出来高の確認やRSIとの併用で信頼度が向上。",
        "description_lv4": "GC/DC判定。MACD Signal Line Crossoverとの組み合わせ。ダマシ回避のフィルター設計。",
        "image_metaphor": "最近の勢いが長期の流れを追い越した",
        "related_features": ["signals", "chart"],
    },
    {
        "term": "含み損",
        "reading": "ふくみぞん",
        "display_name_lv1": "買った時より下がっている金額",
        "description_lv1": "今売ったらこれだけ損する、という金額です。売らなければ確定しません。",
        "description_lv2": "保有株の現在価格が取得価格を下回っている状態の差額。実現損失ではなく評価損。",
        "description_lv3": "含み損 = (現在株価 - 取得単価) × 保有数量。税務上の損益通算の検討ポイント。",
        "description_lv4": "未実現P&L。Tax-Loss Harvestingの対象検討。減損基準との比較分析。",
        "image_metaphor": "今売ったらこれだけ損する",
        "related_features": ["portfolio", "alerts"],
    },
    {
        "term": "配当利回り",
        "reading": "はいとうりまわり",
        "display_name_lv1": "年間のお小遣い率",
        "description_lv1": "持っているだけで毎年もらえるお金の割合です。銀行預金の利息のようなもの。",
        "description_lv2": "年間配当金を株価で割ったもの。高配当株は安定収入が期待できますが、株価下落リスクもあります。",
        "description_lv3": "配当利回り = 年間配当 / 株価 × 100。配当性向・DOE・増配傾向との総合判断が重要。",
        "description_lv4": "Dividend Yield。配当性向（Payout Ratio）との持続性分析。DPS成長率のDDM適用。",
        "image_metaphor": "持っているだけでもらえる分",
        "related_features": ["screening", "portfolio"],
    },
]

# ---------------------------------------------------------------------------
# Signal / Alert explanation templates
# ---------------------------------------------------------------------------

SIGNAL_EXPLANATIONS: dict[str, dict[int, str]] = {
    "golden_cross": {
        1: "この銘柄、最近上がり始めています。買う人が増えてきたサインです。",
        2: "5日移動平均が20日移動平均を上抜け（ゴールデンクロス）しました。短期の勢いが長期トレンドを上回り、上昇トレンドの始まりを示唆しています。",
        3: "5MA/20MAゴールデンクロス発生。上昇トレンドの開始を示唆。出来高と他のテクニカル指標も確認してください。",
        4: "GC発生。5MA > 20MA crossover。テクニカル詳細はチャート画面で確認可能。",
    },
    "volume_spike": {
        1: "いつもより多くの人がこの株を売買しています。何か動きがあるかもしれません。",
        2: "出来高が通常の2倍以上に急増しました。大きなニュースや機関投資家の動きがある可能性があります。",
        3: "出来高急増検出。20日平均出来高比で異常値。価格変動との相関を確認してください。",
        4: "Volume spike detected。機関投資家のブロックトレード可能性。VWAP分析推奨。",
    },
    "undervalued": {
        1: "この銘柄は本来の価値より安く売られているかもしれません。お買い得のチャンスかも。",
        2: "PERが業界平均を大きく下回っています。業績が安定しているなら割安な可能性があります。",
        3: "PER/PBRが業種平均比で乖離。ファンダメンタルズの裏付けを確認した上で割安判定。",
        4: "Valuation gap detected。マルチプル比較とDCF推定値を併用して分析推奨。",
    },
    "momentum": {
        1: "この銘柄は最近ずっと上がり続けています。勢いがあるサインです。",
        2: "株価が継続的に上昇しており、モメンタム（勢い）が強い状態です。ただし過熱にも注意。",
        3: "モメンタムスコア上位。直近のリターンが市場平均を大幅に上回る。RSIによる過熱チェック推奨。",
        4: "Strong momentum signal。Cross-sectional momentum factor上位。リバーサルリスクも考慮。",
    },
}

ALERT_EXPLANATIONS: dict[str, dict[int, str]] = {
    "stop_loss": {
        1: "この株が買った時よりだいぶ下がっています。これ以上損が広がらないよう注意しましょう。",
        2: "取得価格から一定以上下落しました。損切りラインに近づいています。早めの判断が大切です。",
        3: "損切りライン接近。現在の含み損率と損切り閾値を確認してください。",
        4: "Stop-loss threshold alert。トレーリングストップの調整を検討。",
    },
    "concentration": {
        1: "一つの株に集中しすぎています。分散するともっと安心です。",
        2: "特定銘柄の割合が高くなっています。1つの銘柄が大きく下がると全体に影響します。",
        3: "ポートフォリオ集中度が閾値超過。HHI値と個別銘柄ウェイトを確認してください。",
        4: "Concentration risk alert。HHI超過。リバランスまたはヘッジを検討。",
    },
    "health_low": {
        1: "ポートフォリオの健康状態が良くありません。新しい株を買うのは少し待ちましょう。",
        2: "健全度スコアが低下しています。リスクが高まっている状態です。",
        3: "健全度スコアが黄色/赤レベル。各サブスコアの内訳を確認してリスク要因を特定してください。",
        4: "Health score critical。リスクファクター分解と対策の優先度を判断。",
    },
    "high_volatility": {
        1: "この株はとても激しく上下します。大きく損をする可能性があるので注意してください。",
        2: "ボラティリティ（値動きの激しさ）が非常に高い銘柄です。利益も大きいですがリスクも大きいです。",
        3: "高ボラティリティ銘柄。HVが市場平均の2倍超。ポジションサイズの調整を推奨。",
        4: "High volatility alert。IV/HV分析とポジションサイジング再計算を推奨。",
    },
    "market_crash": {
        1: "市場全体が大きく下がっています。焦って売らずに落ち着いて様子を見ましょう。",
        2: "市場全体が急落しています。個別株も影響を受ける可能性が高いです。",
        3: "市場全体の急落検出。ベータ値に応じたポートフォリオ影響を試算してください。",
        4: "Market crash detected。システマティックリスク上昇。ヘッジポジションの検討。",
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_level(xp: int) -> tuple[int, str, int]:
    """Return (level, level_name, stage) for given XP."""
    result = LEVEL_TABLE[0]
    for entry in LEVEL_TABLE:
        if xp >= entry["xp"]:
            result = entry
        else:
            break
    return result["level"], result["name"], result["stage"]


def _xp_to_next_level(xp: int) -> int:
    """Return XP needed to reach the next level."""
    for entry in LEVEL_TABLE:
        if xp < entry["xp"]:
            return entry["xp"] - xp
    return 0


async def _ensure_user(user_id: int = 1) -> dict:
    """Get or create user profile. Returns dict."""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT id, stage, level, xp, safe_mode, login_streak, "
        "last_login_date, total_login_days, stage_upgraded_at, "
        "self_declared_stage, created_at "
        "FROM user_profile WHERE id = ?",
        (user_id,),
    )
    if row is not None:
        return dict(row)

    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO user_profile (id, stage, level, xp, safe_mode, login_streak, "
        "total_login_days, created_at) VALUES (?, 1, 1, 0, 0, 0, 0, ?)",
        (user_id, now),
    )
    await db.commit()
    return {
        "id": user_id, "stage": 1, "level": 1, "xp": 0, "safe_mode": False,
        "login_streak": 0, "last_login_date": None, "total_login_days": 0,
        "stage_upgraded_at": None, "self_declared_stage": None, "created_at": now,
    }


# ---------------------------------------------------------------------------
# User Profile endpoints
# ---------------------------------------------------------------------------


@router.get("/user/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: int = Query(1, description="ユーザーID")) -> dict:
    """ユーザーのステージ・レベル・XP情報を取得する。"""
    profile = await _ensure_user(user_id)
    profile["safe_mode"] = bool(profile["safe_mode"])
    return profile


@router.post("/user/xp", response_model=XPAddResponse)
async def add_xp(body: XPAddRequest, user_id: int = Query(1)) -> dict:
    """XPを加算する。"""
    action_conf = XP_ACTIONS.get(body.action_type)
    if action_conf is None:
        raise HTTPException(status_code=400, detail=f"Unknown action_type: {body.action_type}")

    db = await get_db()
    profile = await _ensure_user(user_id)

    # Check daily limit
    if action_conf["daily_limit"] is not None:
        today = date.today().isoformat()
        count_row = await db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM user_xp_log "
            "WHERE user_id = ? AND action_type = ? AND date(created_at) = ?",
            (user_id, body.action_type, today),
        )
        if count_row and count_row["cnt"] >= action_conf["daily_limit"]:
            return {
                "xp_earned": 0,
                "total_xp": profile["xp"],
                "level": profile["level"],
                "level_up": False,
            }

    xp_earned = action_conf["xp"]
    new_xp = profile["xp"] + xp_earned
    new_level, new_level_name, new_stage = _compute_level(new_xp)
    level_up = new_level > profile["level"]

    now = datetime.utcnow().isoformat()
    # Log XP
    await db.execute(
        "INSERT INTO user_xp_log (user_id, action_type, xp_earned, created_at) VALUES (?, ?, ?, ?)",
        (user_id, body.action_type, xp_earned, now),
    )
    # Update profile
    stage_clause = ""
    params: list = [new_xp, new_level]
    if new_stage > profile["stage"]:
        stage_clause = ", stage = ?, stage_upgraded_at = ?"
        params.extend([new_stage, now])
    params.append(user_id)
    await db.execute(
        f"UPDATE user_profile SET xp = ?, level = ?{stage_clause} WHERE id = ?",
        tuple(params),
    )

    # Log education event
    await db.execute(
        "INSERT INTO education_logs (user_id, event_type, target_id, context, created_at) "
        "VALUES (?, 'xp_earned', ?, ?, ?)",
        (user_id, body.action_type, body.context or None, now),
    )
    await db.commit()

    result: dict = {
        "xp_earned": xp_earned,
        "total_xp": new_xp,
        "level": new_level,
        "level_up": level_up,
    }
    if level_up:
        result["new_level_name"] = new_level_name
    return result


@router.get("/user/badges", response_model=list[BadgeResponse])
async def list_badges(user_id: int = Query(1)) -> list[dict]:
    """ユーザーのバッジ一覧を取得する。"""
    await _ensure_user(user_id)
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT badge_id, earned_at FROM user_badges WHERE user_id = ? ORDER BY earned_at DESC",
        (user_id,),
    )
    return [dict(r) for r in rows]


@router.get("/user/progress", response_model=UserProgressResponse)
async def get_user_progress(user_id: int = Query(1)) -> dict:
    """成長ダッシュボード用データを取得する。"""
    db = await get_db()
    profile = await _ensure_user(user_id)

    level, level_name, stage = _compute_level(profile["xp"])
    xp_next = _xp_to_next_level(profile["xp"])
    stage_name = STAGE_NAMES.get(stage, "ビギナー")

    badges_row = await db.execute_fetchone(
        "SELECT COUNT(*) as cnt FROM user_badges WHERE user_id = ?", (user_id,)
    )
    cards_row = await db.execute_fetchone(
        "SELECT COUNT(DISTINCT card_id) as cnt FROM user_card_history WHERE user_id = ?", (user_id,)
    )
    signals_row = await db.execute_fetchone(
        "SELECT COUNT(*) as cnt FROM education_logs WHERE user_id = ? AND event_type = 'why_viewed'",
        (user_id,),
    )
    sims_row = await db.execute_fetchone(
        "SELECT COUNT(*) as cnt FROM simulation_scenarios WHERE user_id = ?", (user_id,)
    )

    return {
        "stage": stage,
        "stage_name": stage_name,
        "level": level,
        "level_name": level_name,
        "xp": profile["xp"],
        "xp_to_next_level": xp_next,
        "total_login_days": profile["total_login_days"],
        "login_streak": profile["login_streak"],
        "badges_count": badges_row["cnt"] if badges_row else 0,
        "cards_viewed": cards_row["cnt"] if cards_row else 0,
        "signals_explained": signals_row["cnt"] if signals_row else 0,
        "simulations_run": sims_row["cnt"] if sims_row else 0,
    }


@router.put("/user/safe-mode", response_model=SafeModeResponse)
async def toggle_safe_mode(body: SafeModeRequest, user_id: int = Query(1)) -> dict:
    """セーフモードを切り替える。"""
    db = await get_db()
    await _ensure_user(user_id)
    await db.execute(
        "UPDATE user_profile SET safe_mode = ? WHERE id = ?",
        (1 if body.enabled else 0, user_id),
    )
    await db.commit()
    return {"safe_mode": body.enabled}


@router.get("/user/guardrails", response_model=GuardrailsResponse)
async def get_guardrails(user_id: int = Query(1)) -> dict:
    """現在のガードレール設定を取得する。"""
    profile = await _ensure_user(user_id)
    stage = profile["stage"]
    safe = bool(profile["safe_mode"])

    # Guardrails per spec section 3
    configs = {
        1: {
            "stop_loss_editable": False,
            "stop_loss_range": [-10.0, -10.0],
            "concentration_limit": 30.0,
            "concentration_action": "block",
            "low_health_action": "block",
            "high_volatility_action": "confirm_required",
            "settings_editable": "none",
        },
        2: {
            "stop_loss_editable": True,
            "stop_loss_range": [-20.0, -5.0],
            "concentration_limit": 30.0,
            "concentration_action": "confirm",
            "low_health_action": "confirm",
            "high_volatility_action": "warn_with_explanation",
            "settings_editable": "partial",
        },
        3: {
            "stop_loss_editable": True,
            "stop_loss_range": [-30.0, -3.0],
            "concentration_limit": 40.0,
            "concentration_action": "warn",
            "low_health_action": "warn",
            "high_volatility_action": "info",
            "settings_editable": "most",
        },
        4: {
            "stop_loss_editable": True,
            "stop_loss_range": [-100.0, 0.0],
            "concentration_limit": 50.0,
            "concentration_action": "warn",
            "low_health_action": "info",
            "high_volatility_action": "none",
            "settings_editable": "all",
        },
    }
    effective_stage = 1 if safe else stage
    cfg = configs.get(effective_stage, configs[1])
    return {"stage": stage, "safe_mode": safe, **cfg}


# ---------------------------------------------------------------------------
# Glossary endpoints
# ---------------------------------------------------------------------------


@router.get("/glossary", response_model=list[GlossaryTermResponse])
async def list_glossary(
    search: str = Query("", description="検索キーワード"),
) -> list[dict]:
    """用語一覧を取得する。"""
    terms = GLOSSARY
    if search:
        q = search.lower()
        terms = [
            t for t in terms
            if q in t["term"].lower()
            or q in t["reading"].lower()
            or q in t["display_name_lv1"].lower()
        ]
    return terms


@router.get("/glossary/{term}", response_model=GlossaryTermResponse)
async def get_glossary_term(term: str) -> dict:
    """個別用語解説を取得する。"""
    for t in GLOSSARY:
        if t["term"] == term:
            return t
    raise HTTPException(status_code=404, detail=f"Term not found: {term}")


# ---------------------------------------------------------------------------
# Learning Cards endpoints
# ---------------------------------------------------------------------------


@router.get("/learning/cards", response_model=list[LearningCardResponse])
async def list_learning_cards(
    user_id: int = Query(1),
    category: Optional[str] = Query(None, description="カテゴリフィルタ"),
) -> list[dict]:
    """学習カード一覧を取得する（ステージに応じたコンテンツ付き）。"""
    db = await get_db()
    profile = await _ensure_user(user_id)
    stage = profile["stage"]
    content_col = f"content_lv{stage}"

    where = ""
    params: list = []
    if category:
        where = "WHERE lc.category = ?"
        params.append(category)

    rows = await db.execute_fetchall(
        f"SELECT lc.id, lc.card_key, lc.title, lc.{content_col} as content, "
        f"lc.category, lc.related_signal_type, "
        f"CASE WHEN uch.card_id IS NOT NULL THEN 1 ELSE 0 END as viewed "
        f"FROM learning_cards lc "
        f"LEFT JOIN (SELECT DISTINCT card_id FROM user_card_history WHERE user_id = ?) uch "
        f"ON lc.id = uch.card_id "
        f"{where} ORDER BY lc.id",
        (user_id, *params),
    )
    return [dict(r) | {"viewed": bool(r["viewed"])} for r in rows]


@router.post("/learning/cards/{card_id}/viewed", response_model=CardViewedResponse)
async def mark_card_viewed(card_id: int, user_id: int = Query(1)) -> dict:
    """カード閲覧を記録する（XPも加算）。"""
    db = await get_db()
    await _ensure_user(user_id)

    # Check card exists
    card = await db.execute_fetchone("SELECT id FROM learning_cards WHERE id = ?", (card_id,))
    if card is None:
        raise HTTPException(status_code=404, detail="Learning card not found")

    # Check if already viewed
    existing = await db.execute_fetchone(
        "SELECT id FROM user_card_history WHERE user_id = ? AND card_id = ?",
        (user_id, card_id),
    )

    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO user_card_history (user_id, card_id, viewed_at) VALUES (?, ?, ?)",
        (user_id, card_id, now),
    )

    xp_earned = 0
    if existing is None:
        # First view: award XP
        xp_earned = XP_ACTIONS["card_viewed"]["xp"]
        profile = await _ensure_user(user_id)
        new_xp = profile["xp"] + xp_earned
        new_level, _, new_stage = _compute_level(new_xp)
        await db.execute(
            "UPDATE user_profile SET xp = ?, level = ? WHERE id = ?",
            (new_xp, new_level, user_id),
        )
        await db.execute(
            "INSERT INTO user_xp_log (user_id, action_type, xp_earned, created_at) VALUES (?, 'card_viewed', ?, ?)",
            (user_id, xp_earned, now),
        )

    await db.execute(
        "INSERT INTO education_logs (user_id, event_type, target_id, created_at) "
        "VALUES (?, 'card_viewed', ?, ?)",
        (user_id, str(card_id), now),
    )
    await db.commit()
    return {"card_id": card_id, "xp_earned": xp_earned}


# ---------------------------------------------------------------------------
# Signal / Alert explanation endpoints
# ---------------------------------------------------------------------------


@router.get("/signals/{signal_id}/explanation", response_model=SignalExplanationResponse)
async def get_signal_explanation(
    signal_id: int,
    user_id: int = Query(1),
) -> dict:
    """シグナルのステージ別説明を取得する。"""
    db = await get_db()
    profile = await _ensure_user(user_id)
    stage = profile["stage"]

    row = await db.execute_fetchone(
        "SELECT id, ticker, signal_type FROM signals WHERE id = ?",
        (signal_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    signal_type = row["signal_type"]
    templates = SIGNAL_EXPLANATIONS.get(signal_type, {})
    explanation = templates.get(stage, templates.get(1, "この銘柄に注目のシグナルが出ています。"))

    # Log the view
    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO education_logs (user_id, event_type, target_id, context, created_at) "
        "VALUES (?, 'why_viewed', ?, 'signal', ?)",
        (user_id, str(signal_id), now),
    )
    await db.commit()

    return {
        "signal_id": row["id"],
        "signal_type": signal_type,
        "ticker": row["ticker"],
        "explanation": explanation,
        "stage": stage,
    }


@router.get("/alerts/{alert_id}/explanation", response_model=AlertExplanationResponse)
async def get_alert_explanation(
    alert_id: int,
    user_id: int = Query(1),
) -> dict:
    """アラートの「なぜ危険？」説明を取得する。"""
    db = await get_db()
    profile = await _ensure_user(user_id)
    stage = profile["stage"]

    row = await db.execute_fetchone(
        "SELECT id, alert_type, ticker FROM alerts WHERE id = ?",
        (alert_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_type = row["alert_type"]
    templates = ALERT_EXPLANATIONS.get(alert_type, {})
    explanation = templates.get(stage, templates.get(1, "注意が必要なアラートです。"))

    now = datetime.utcnow().isoformat()
    await db.execute(
        "INSERT INTO education_logs (user_id, event_type, target_id, context, created_at) "
        "VALUES (?, 'why_viewed', ?, 'alert', ?)",
        (user_id, str(alert_id), now),
    )
    await db.commit()

    return {
        "alert_id": row["id"],
        "alert_type": alert_type,
        "ticker": row["ticker"],
        "explanation": explanation,
        "stage": stage,
    }
