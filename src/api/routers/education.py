"""Education endpoints: glossary and learning cards."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import GlossaryTermResponse, LearningCardResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Glossary data (in-memory)
# ---------------------------------------------------------------------------

GLOSSARY: list[dict] = [
    {
        "term": "PER",
        "reading": "ピーイーアール",
        "display_name": "お買い得度",
        "description": "利益の何倍の値段がついているかを示します。低いほどお買い得かもしれません。株価を1株あたり利益(EPS)で割って計算します。",
        "image_metaphor": "利益の何倍の値段か",
        "related_features": ["screening", "signals"],
    },
    {
        "term": "PBR",
        "reading": "ピービーアール",
        "display_name": "資産に対する割安度",
        "description": "会社の持ち物（純資産）に対して株価が安いかどうかを見ます。1倍以下は帳簿上の資産より安く買える状態です。",
        "image_metaphor": "会社の持ち物に対して安いか",
        "related_features": ["screening"],
    },
    {
        "term": "RSI",
        "reading": "アールエスアイ",
        "display_name": "買われすぎ/売られすぎメーター",
        "description": "株がどれくらい買われすぎ・売られすぎかを0〜100で示します。70以上は買われすぎ、30以下は売られすぎのサインです。",
        "image_metaphor": "温度計のようなもの",
        "related_features": ["signals", "chart"],
    },
    {
        "term": "ボラティリティ",
        "reading": "ぼらてぃりてぃ",
        "display_name": "値動きの激しさ",
        "description": "株価がどれくらい激しく上下するかを示します。高いほどリスクが大きいが、リターンの機会も大きいです。",
        "image_metaphor": "ジェットコースター度",
        "related_features": ["risk", "alerts"],
    },
    {
        "term": "ドローダウン",
        "reading": "どろーだうん",
        "display_name": "ピークからの下がり幅",
        "description": "一番高い所からどれだけ落ちたかを示します。最大ドローダウンが大きいほど、過去に大きな損失を経験したことを意味します。",
        "image_metaphor": "一番高い所からどれだけ落ちたか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "シャープレシオ",
        "reading": "しゃーぷれしお",
        "display_name": "リスクに見合ったリターンか",
        "description": "危険を冒した分だけちゃんと儲かっているかを見る指標です。高いほど効率的な投資ができています。1以上が望ましいです。",
        "image_metaphor": "危険を冒した分だけ儲かっているか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "β値",
        "reading": "べーたち",
        "display_name": "市場との連動度",
        "description": "市場全体が動いた時に、この銘柄がどれくらい影響を受けるかを示します。1より大きいと市場より大きく動きます。",
        "image_metaphor": "市場が風邪をひいた時の影響度",
        "related_features": ["risk"],
    },
    {
        "term": "HHI",
        "reading": "エイチエイチアイ",
        "display_name": "偏り度合い",
        "description": "卵を一つのカゴに盛りすぎていないかを見る指標です。値が高いほど特定銘柄に偏っています。分散が大事！",
        "image_metaphor": "卵を一つのカゴに盛りすぎていないか",
        "related_features": ["risk", "portfolio"],
    },
    {
        "term": "VaR",
        "reading": "ブイエーアール",
        "display_name": "最悪ケースの損失額",
        "description": "運が悪い日の最大被害額です。95%の確率で、1日にこの金額以上は損しないという目安です。",
        "image_metaphor": "運が悪い日の最大被害額",
        "related_features": ["risk"],
    },
    {
        "term": "ゴールデンクロス",
        "reading": "ごーるでんくろす",
        "display_name": "上昇トレンドのサイン",
        "description": "最近の勢い（短期移動平均）が長期の流れ（長期移動平均）を追い越しました。上がり始めのサインかもしれません。",
        "image_metaphor": "最近の勢いが長期の流れを追い越した",
        "related_features": ["signals", "chart"],
    },
    {
        "term": "含み損",
        "reading": "ふくみぞん",
        "display_name": "買った時より下がっている金額",
        "description": "今売ったらこれだけ損する、という金額です。売らなければ確定しません。",
        "image_metaphor": "今売ったらこれだけ損する",
        "related_features": ["portfolio", "alerts"],
    },
    {
        "term": "配当利回り",
        "reading": "はいとうりまわり",
        "display_name": "年間のお小遣い率",
        "description": "持っているだけで毎年もらえるお金の割合です。銀行預金の利息のようなもの。高配当は安定収入が期待できます。",
        "image_metaphor": "持っているだけでもらえる分",
        "related_features": ["screening", "portfolio"],
    },
]


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
            or q in t["display_name"].lower()
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
    category: Optional[str] = Query(None, description="カテゴリフィルタ"),
) -> list[dict]:
    """学習カード一覧を取得する。"""
    db = await get_db()

    where = ""
    params: list = []
    if category:
        where = "WHERE category = ?"
        params.append(category)

    rows = await db.execute_fetchall(
        f"SELECT id, card_key, title, content, category, related_signal_type "
        f"FROM learning_cards {where} ORDER BY id",
        tuple(params),
    )
    return [dict(r) for r in rows]
