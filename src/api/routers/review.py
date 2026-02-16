"""Review endpoints: weekly/monthly reviews, signal/alert outcome tracking."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import (
    AlertOutcomeResponse,
    MonthlyReviewResponse,
    SignalOutcomeResponse,
    WeeklyReviewResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Weekly Review
# ---------------------------------------------------------------------------


@router.get("/review/weekly", response_model=WeeklyReviewResponse)
async def get_weekly_review(
    user_id: int = Query(1),
    weeks_ago: int = Query(0, ge=0, le=52, description="何週間前のデータか (0=今週)"),
) -> dict:
    """週次振り返りデータを取得する。"""
    db = await get_db()

    today = date.today()
    # Monday of the target week
    start_of_this_week = today - timedelta(days=today.weekday())
    period_start = start_of_this_week - timedelta(weeks=weeks_ago)
    period_end = period_start + timedelta(days=6)

    start_str = period_start.isoformat()
    end_str = period_end.isoformat()

    # Signal accuracy
    signal_rows = await db.execute_fetchall(
        "SELECT is_success FROM signal_outcomes "
        "WHERE user_id = ? AND signal_id IN ("
        "  SELECT id FROM signals WHERE date(created_at) BETWEEN ? AND ?"
        ")",
        (user_id, start_str, end_str),
    )
    signals_total = len(signal_rows)
    signals_hit = sum(1 for r in signal_rows if r["is_success"])
    signal_accuracy = (signals_hit / signals_total * 100) if signals_total > 0 else None

    # Alerts acted on
    alert_rows = await db.execute_fetchall(
        "SELECT user_action FROM alert_outcomes "
        "WHERE user_id = ? AND alert_id IN ("
        "  SELECT id FROM alerts WHERE date(created_at) BETWEEN ? AND ?"
        ")",
        (user_id, start_str, end_str),
    )
    alerts_total = len(alert_rows)
    alerts_acted = sum(1 for r in alert_rows if r["user_action"] == "acted")

    # XP earned this week
    xp_row = await db.execute_fetchone(
        "SELECT COALESCE(SUM(xp_earned), 0) as total "
        "FROM user_xp_log WHERE user_id = ? AND date(created_at) BETWEEN ? AND ?",
        (user_id, start_str, end_str),
    )
    xp_earned = xp_row["total"] if xp_row else 0

    # Cards viewed this week
    cards_row = await db.execute_fetchone(
        "SELECT COUNT(DISTINCT card_id) as cnt "
        "FROM user_card_history WHERE user_id = ? AND date(viewed_at) BETWEEN ? AND ?",
        (user_id, start_str, end_str),
    )
    cards_viewed = cards_row["cnt"] if cards_row else 0

    # Build highlights
    highlights: list[str] = []
    if xp_earned > 0:
        highlights.append(f"今週 {xp_earned} XP を獲得しました")
    if cards_viewed > 0:
        highlights.append(f"学習カードを {cards_viewed} 枚閲覧しました")
    if signals_total > 0 and signal_accuracy is not None:
        highlights.append(f"シグナル的中率: {signal_accuracy:.0f}%")
    if alerts_acted > 0:
        highlights.append(f"アラートに {alerts_acted} 件対応しました")

    return {
        "period_start": start_str,
        "period_end": end_str,
        "signal_accuracy": round(signal_accuracy, 1) if signal_accuracy is not None else None,
        "signals_total": signals_total,
        "signals_hit": signals_hit,
        "alerts_total": alerts_total,
        "alerts_acted": alerts_acted,
        "xp_earned": xp_earned,
        "cards_viewed": cards_viewed,
        "highlights": highlights,
    }


# ---------------------------------------------------------------------------
# Monthly Review
# ---------------------------------------------------------------------------


@router.get("/review/monthly", response_model=MonthlyReviewResponse)
async def get_monthly_review(
    user_id: int = Query(1),
    months_ago: int = Query(0, ge=0, le=12, description="何ヶ月前のデータか (0=今月)"),
) -> dict:
    """月次振り返りデータを取得する。"""
    db = await get_db()

    today = date.today()
    # Target month
    target_month = today.month - months_ago
    target_year = today.year
    while target_month <= 0:
        target_month += 12
        target_year -= 1

    period_start = date(target_year, target_month, 1)
    # End of month
    if target_month == 12:
        period_end = date(target_year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(target_year, target_month + 1, 1) - timedelta(days=1)

    start_str = period_start.isoformat()
    end_str = period_end.isoformat()

    # Signal accuracy
    signal_rows = await db.execute_fetchall(
        "SELECT is_success FROM signal_outcomes "
        "WHERE user_id = ? AND signal_id IN ("
        "  SELECT id FROM signals WHERE date(created_at) BETWEEN ? AND ?"
        ")",
        (user_id, start_str, end_str),
    )
    signals_total = len(signal_rows)
    signals_hit = sum(1 for r in signal_rows if r["is_success"])
    signal_accuracy = (signals_hit / signals_total * 100) if signals_total > 0 else None

    # Alert response rate
    alert_rows = await db.execute_fetchall(
        "SELECT user_action FROM alert_outcomes "
        "WHERE user_id = ? AND alert_id IN ("
        "  SELECT id FROM alerts WHERE date(created_at) BETWEEN ? AND ?"
        ")",
        (user_id, start_str, end_str),
    )
    alerts_total = len(alert_rows)
    alerts_acted = sum(1 for r in alert_rows if r["user_action"] == "acted")
    alert_response_rate = (alerts_acted / alerts_total * 100) if alerts_total > 0 else None

    # XP earned
    xp_row = await db.execute_fetchone(
        "SELECT COALESCE(SUM(xp_earned), 0) as total "
        "FROM user_xp_log WHERE user_id = ? AND date(created_at) BETWEEN ? AND ?",
        (user_id, start_str, end_str),
    )
    xp_earned = xp_row["total"] if xp_row else 0

    # Badges earned this month
    badge_rows = await db.execute_fetchall(
        "SELECT badge_id FROM user_badges WHERE user_id = ? AND date(earned_at) BETWEEN ? AND ?",
        (user_id, start_str, end_str),
    )
    badges_earned = [r["badge_id"] for r in badge_rows]

    # Simulations run
    sims_row = await db.execute_fetchone(
        "SELECT COUNT(*) as cnt FROM simulation_scenarios "
        "WHERE user_id = ? AND date(created_at) BETWEEN ? AND ?",
        (user_id, start_str, end_str),
    )
    simulations_run = sims_row["cnt"] if sims_row else 0

    # "If followed" P&L estimate from alert outcomes
    if_pnl_row = await db.execute_fetchone(
        "SELECT SUM(portfolio_impact) as total FROM alert_outcomes "
        "WHERE user_id = ? AND user_action = 'ignored' AND portfolio_impact IS NOT NULL "
        "AND alert_id IN (SELECT id FROM alerts WHERE date(created_at) BETWEEN ? AND ?)",
        (user_id, start_str, end_str),
    )
    if_followed_pnl = if_pnl_row["total"] if if_pnl_row and if_pnl_row["total"] is not None else None

    # Build highlights
    highlights: list[str] = []
    if xp_earned > 0:
        highlights.append(f"今月 {xp_earned} XP を獲得しました")
    if badges_earned:
        highlights.append(f"バッジ {len(badges_earned)} 個を獲得: {', '.join(badges_earned)}")
    if signal_accuracy is not None:
        highlights.append(f"シグナル的中率: {signal_accuracy:.0f}%")
    if alert_response_rate is not None:
        highlights.append(f"アラート対応率: {alert_response_rate:.0f}%")
    if simulations_run > 0:
        highlights.append(f"シミュレーションを {simulations_run} 回実行しました")

    return {
        "period_start": start_str,
        "period_end": end_str,
        "signal_accuracy": round(signal_accuracy, 1) if signal_accuracy is not None else None,
        "alert_response_rate": round(alert_response_rate, 1) if alert_response_rate is not None else None,
        "xp_earned": xp_earned,
        "level_change": 0,
        "badges_earned": badges_earned,
        "simulations_run": simulations_run,
        "if_followed_pnl": round(if_followed_pnl, 2) if if_followed_pnl is not None else None,
        "highlights": highlights,
    }


# ---------------------------------------------------------------------------
# Signal Outcome
# ---------------------------------------------------------------------------


@router.get("/signals/{signal_id}/outcome", response_model=SignalOutcomeResponse)
async def get_signal_outcome(signal_id: int, user_id: int = Query(1)) -> dict:
    """シグナルの結果追跡データを取得する。"""
    db = await get_db()

    # Get signal info
    signal = await db.execute_fetchone(
        "SELECT id, ticker, signal_type FROM signals WHERE id = ?",
        (signal_id,),
    )
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Get outcome
    outcome = await db.execute_fetchone(
        "SELECT user_action, price_at_signal, price_after_7d, price_after_30d, is_success "
        "FROM signal_outcomes WHERE signal_id = ? AND user_id = ?",
        (signal_id, user_id),
    )

    if outcome is None:
        return {
            "signal_id": signal["id"],
            "ticker": signal["ticker"],
            "signal_type": signal["signal_type"],
            "user_action": "unknown",
            "price_at_signal": None,
            "price_after_7d": None,
            "price_after_30d": None,
            "is_success": None,
            "pnl_7d_pct": None,
            "pnl_30d_pct": None,
        }

    price_at = outcome["price_at_signal"]
    pnl_7d = None
    pnl_30d = None
    if price_at and price_at > 0:
        if outcome["price_after_7d"] is not None:
            pnl_7d = round((outcome["price_after_7d"] - price_at) / price_at * 100, 2)
        if outcome["price_after_30d"] is not None:
            pnl_30d = round((outcome["price_after_30d"] - price_at) / price_at * 100, 2)

    return {
        "signal_id": signal["id"],
        "ticker": signal["ticker"],
        "signal_type": signal["signal_type"],
        "user_action": outcome["user_action"],
        "price_at_signal": outcome["price_at_signal"],
        "price_after_7d": outcome["price_after_7d"],
        "price_after_30d": outcome["price_after_30d"],
        "is_success": bool(outcome["is_success"]) if outcome["is_success"] is not None else None,
        "pnl_7d_pct": pnl_7d,
        "pnl_30d_pct": pnl_30d,
    }


# ---------------------------------------------------------------------------
# Alert Outcome
# ---------------------------------------------------------------------------


@router.get("/alerts/{alert_id}/outcome", response_model=AlertOutcomeResponse)
async def get_alert_outcome(alert_id: int, user_id: int = Query(1)) -> dict:
    """アラートの結果追跡データを取得する。"""
    db = await get_db()

    alert = await db.execute_fetchone(
        "SELECT id, alert_type, ticker FROM alerts WHERE id = ?",
        (alert_id,),
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    outcome = await db.execute_fetchone(
        "SELECT user_action, action_detail, price_at_alert, price_after_7d, "
        "price_after_30d, portfolio_impact "
        "FROM alert_outcomes WHERE alert_id = ? AND user_id = ?",
        (alert_id, user_id),
    )

    if outcome is None:
        return {
            "alert_id": alert["id"],
            "alert_type": alert["alert_type"],
            "ticker": alert["ticker"],
            "user_action": "unknown",
            "action_detail": None,
            "price_at_alert": None,
            "price_after_7d": None,
            "price_after_30d": None,
            "portfolio_impact": None,
        }

    return {
        "alert_id": alert["id"],
        "alert_type": alert["alert_type"],
        "ticker": alert["ticker"],
        "user_action": outcome["user_action"],
        "action_detail": outcome["action_detail"],
        "price_at_alert": outcome["price_at_alert"],
        "price_after_7d": outcome["price_after_7d"],
        "price_after_30d": outcome["price_after_30d"],
        "portfolio_impact": outcome["portfolio_impact"],
    }
