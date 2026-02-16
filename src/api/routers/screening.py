"""Screening results endpoints."""

from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Query

from src.api.database import get_db
from src.api.models import ScreeningResultResponse

router = APIRouter()


@router.get("/screening/value", response_model=list[ScreeningResultResponse])
async def get_value_screening(
    target_date: Optional[date_type] = Query(None, description="スクリーニング日 (省略時は最新)"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """割安銘柄スクリーニング結果を取得する (バリュースコア順)。"""
    db = await get_db()
    if target_date is None:
        row = await db.execute_fetchone(
            "SELECT MAX(date) as max_date FROM screening_results"
        )
        target_date = row["max_date"] if row and row["max_date"] else date_type.today().isoformat()

    rows = await db.execute_fetchall(
        "SELECT id, date, ticker, name, sector, score, per, pbr, dividend_yield, "
        "momentum_score, value_score "
        "FROM screening_results WHERE date = ? ORDER BY value_score DESC LIMIT ?",
        (str(target_date), limit),
    )
    return [dict(r) for r in rows]


@router.get("/screening/momentum", response_model=list[ScreeningResultResponse])
async def get_momentum_screening(
    target_date: Optional[date_type] = Query(None, description="スクリーニング日 (省略時は最新)"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """モメンタムシグナル一覧を取得する (モメンタムスコア順)。"""
    db = await get_db()
    if target_date is None:
        row = await db.execute_fetchone(
            "SELECT MAX(date) as max_date FROM screening_results"
        )
        target_date = row["max_date"] if row and row["max_date"] else date_type.today().isoformat()

    rows = await db.execute_fetchall(
        "SELECT id, date, ticker, name, sector, score, per, pbr, dividend_yield, "
        "momentum_score, value_score "
        "FROM screening_results WHERE date = ? ORDER BY momentum_score DESC LIMIT ?",
        (str(target_date), limit),
    )
    return [dict(r) for r in rows]
