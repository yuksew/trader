"""Signal endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from src.api.database import get_db
from src.api.models import JobTriggerResponse, NotificationResponse, SignalResponse
from src.api.scheduler import run_daily_check

router = APIRouter()


@router.get("/signals", response_model=list[SignalResponse])
async def list_signals(
    valid_only: bool = Query(True, description="有効なシグナルのみ"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """直近シグナル一覧を取得する。"""
    db = await get_db()
    where = "WHERE is_valid = 1" if valid_only else ""
    rows = await db.execute_fetchall(
        f"SELECT id, ticker, signal_type, priority, message, detail, "
        f"is_valid, expires_at, created_at "
        f"FROM signals {where} ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    limit: int = Query(20, ge=1, le=50),
) -> list[dict]:
    """通知一覧 (攻め+守り統合) を取得する。

    signalsとalertsを日時降順で統合して返す。
    """
    db = await get_db()
    # signals
    signal_rows = await db.execute_fetchall(
        "SELECT id, 'signal' as source, ticker, priority, message, created_at "
        "FROM signals WHERE is_valid = 1 "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    # alerts (未読・未解消)
    alert_rows = await db.execute_fetchall(
        "SELECT id, 'alert' as source, ticker, "
        "CASE WHEN level >= 3 THEN 'high' WHEN level = 2 THEN 'medium' ELSE 'low' END as priority, "
        "message, created_at "
        "FROM alerts WHERE is_resolved = 0 "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    merged = [dict(r) for r in signal_rows] + [dict(r) for r in alert_rows]
    merged.sort(key=lambda x: x["created_at"], reverse=True)
    return merged[:limit]


@router.post("/jobs/daily-check", response_model=JobTriggerResponse)
async def trigger_daily_check() -> dict:
    """日次チェックを手動実行する。"""
    result = await run_daily_check()
    return {"status": "ok", "message": result}
