"""Review endpoints: weekly/monthly reviews."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from src.api.database import get_db
from src.api.models import MonthlyReviewResponse, WeeklyReviewResponse

router = APIRouter()


@router.get("/review/weekly", response_model=WeeklyReviewResponse)
async def get_weekly_review(
    weeks_ago: int = Query(0, ge=0, le=52, description="何週間前のデータか (0=今週)"),
) -> dict:
    """週次振り返りデータを取得する。"""
    db = await get_db()

    today = date.today()
    start_of_this_week = today - timedelta(days=today.weekday())
    period_start = start_of_this_week - timedelta(weeks=weeks_ago)
    period_end = period_start + timedelta(days=6)

    start_str = period_start.isoformat()
    end_str = period_end.isoformat()

    # シグナル数
    signal_rows = await db.execute_fetchall(
        "SELECT id FROM signals WHERE date(created_at) BETWEEN ? AND ?",
        (start_str, end_str),
    )
    signals_total = len(signal_rows)

    # アラート数 & 既読数
    alert_rows = await db.execute_fetchall(
        "SELECT is_read FROM alerts WHERE date(created_at) BETWEEN ? AND ?",
        (start_str, end_str),
    )
    alerts_total = len(alert_rows)
    alerts_acted = sum(1 for r in alert_rows if r["is_read"])

    highlights: list[str] = []
    if signals_total > 0:
        highlights.append(f"今週 {signals_total} 件のシグナルを検知しました")
    if alerts_total > 0:
        highlights.append(f"アラート {alerts_total} 件（うち確認済 {alerts_acted} 件）")

    return {
        "period_start": start_str,
        "period_end": end_str,
        "signals_total": signals_total,
        "alerts_total": alerts_total,
        "alerts_acted": alerts_acted,
        "highlights": highlights,
    }


@router.get("/review/monthly", response_model=MonthlyReviewResponse)
async def get_monthly_review(
    months_ago: int = Query(0, ge=0, le=12, description="何ヶ月前のデータか (0=今月)"),
) -> dict:
    """月次振り返りデータを取得する。"""
    db = await get_db()

    today = date.today()
    target_month = today.month - months_ago
    target_year = today.year
    while target_month <= 0:
        target_month += 12
        target_year -= 1

    period_start = date(target_year, target_month, 1)
    if target_month == 12:
        period_end = date(target_year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(target_year, target_month + 1, 1) - timedelta(days=1)

    start_str = period_start.isoformat()
    end_str = period_end.isoformat()

    signal_rows = await db.execute_fetchall(
        "SELECT id FROM signals WHERE date(created_at) BETWEEN ? AND ?",
        (start_str, end_str),
    )
    signals_total = len(signal_rows)

    alert_rows = await db.execute_fetchall(
        "SELECT is_read FROM alerts WHERE date(created_at) BETWEEN ? AND ?",
        (start_str, end_str),
    )
    alerts_total = len(alert_rows)
    alerts_acted = sum(1 for r in alert_rows if r["is_read"])

    highlights: list[str] = []
    if signals_total > 0:
        highlights.append(f"今月 {signals_total} 件のシグナルを検知しました")
    if alerts_total > 0:
        highlights.append(f"アラート {alerts_total} 件（うち確認済 {alerts_acted} 件）")

    return {
        "period_start": start_str,
        "period_end": end_str,
        "signals_total": signals_total,
        "alerts_total": alerts_total,
        "alerts_acted": alerts_acted,
        "highlights": highlights,
    }
