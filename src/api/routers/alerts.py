"""Alert endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import AlertResponse

router = APIRouter()


@router.get("/portfolios/{portfolio_id}/alerts", response_model=list[AlertResponse])
async def list_alerts(
    portfolio_id: int,
    unresolved_only: bool = Query(True, description="未解消のみ"),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """ポートフォリオに紐づくアラート一覧を取得する。"""
    db = await get_db()
    where = "WHERE portfolio_id = ?"
    params: list = [portfolio_id]
    if unresolved_only:
        where += " AND is_resolved = 0"

    rows = await db.execute_fetchall(
        f"SELECT id, portfolio_id, ticker, alert_type, level, message, "
        f"action_suggestion, is_read, is_resolved, created_at, resolved_at "
        f"FROM alerts {where} ORDER BY level DESC, created_at DESC LIMIT ?",
        (*params, limit),
    )
    return [dict(r) for r in rows]


@router.put("/alerts/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(alert_id: int) -> dict:
    """アラートを既読にする。"""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT id, portfolio_id, ticker, alert_type, level, message, "
        "action_suggestion, is_read, is_resolved, created_at, resolved_at "
        "FROM alerts WHERE id = ?",
        (alert_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
    await db.commit()

    result = dict(row)
    result["is_read"] = True
    return result


@router.put("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(alert_id: int) -> dict:
    """アラートを解決済みにする。"""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT id, portfolio_id, ticker, alert_type, level, message, "
        "action_suggestion, is_read, is_resolved, created_at, resolved_at "
        "FROM alerts WHERE id = ?",
        (alert_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "UPDATE alerts SET is_resolved = 1, resolved_at = ? WHERE id = ?",
        (now, alert_id),
    )
    await db.commit()

    result = dict(row)
    result["is_resolved"] = True
    result["resolved_at"] = now
    return result


@router.put(
    "/portfolios/{portfolio_id}/alerts/resolve-all",
    response_model=list[AlertResponse],
)
async def resolve_all_alerts(portfolio_id: int) -> list[dict]:
    """ポートフォリオの未解決アラートを一括で解決済みにする。"""
    db = await get_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    await db.execute(
        "UPDATE alerts SET is_resolved = 1, resolved_at = ? "
        "WHERE portfolio_id = ? AND is_resolved = 0",
        (now, portfolio_id),
    )
    await db.commit()

    rows = await db.execute_fetchall(
        "SELECT id, portfolio_id, ticker, alert_type, level, message, "
        "action_suggestion, is_read, is_resolved, created_at, resolved_at "
        "FROM alerts WHERE portfolio_id = ? AND resolved_at = ? "
        "ORDER BY level DESC, created_at DESC",
        (portfolio_id, now),
    )
    return [dict(r) for r in rows]
