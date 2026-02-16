"""Risk metrics & health score endpoints."""

from __future__ import annotations

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import (
    ConcentrationResponse,
    HealthResponse,
    RiskMetricsResponse,
    StopLossCreate,
    StopLossResponse,
)

router = APIRouter()


@router.get("/portfolios/{portfolio_id}/health", response_model=HealthResponse)
async def get_health(portfolio_id: int) -> dict:
    """ポートフォリオ健全度スコアを取得する。"""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT health_score, max_drawdown, portfolio_volatility, hhi "
        "FROM risk_metrics WHERE portfolio_id = ? ORDER BY date DESC LIMIT 1",
        (portfolio_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Risk metrics not found. Run daily check first.")

    score = row["health_score"]
    if score >= 70:
        level = "green"
        message = "健全です。特にアクションは不要です。"
    elif score >= 40:
        level = "yellow"
        message = "注意が必要です。改善ポイントを確認してください。"
    else:
        level = "red"
        message = "危険な状態です。具体的なアクションを確認してください。"

    return {
        "health_score": score,
        "level": level,
        "message": message,
        "breakdown": {
            "max_drawdown": row["max_drawdown"],
            "volatility": row["portfolio_volatility"],
            "hhi": row["hhi"],
        },
    }


@router.get("/portfolios/{portfolio_id}/risk-metrics", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    portfolio_id: int,
    target_date: Optional[date_type] = Query(None, description="算出日 (省略時は最新)"),
) -> dict:
    """リスク指標を取得する。"""
    db = await get_db()
    if target_date:
        row = await db.execute_fetchone(
            "SELECT id, portfolio_id, date, health_score, max_drawdown, "
            "portfolio_volatility, sharpe_ratio, hhi, var_95 "
            "FROM risk_metrics WHERE portfolio_id = ? AND date = ?",
            (portfolio_id, str(target_date)),
        )
    else:
        row = await db.execute_fetchone(
            "SELECT id, portfolio_id, date, health_score, max_drawdown, "
            "portfolio_volatility, sharpe_ratio, hhi, var_95 "
            "FROM risk_metrics WHERE portfolio_id = ? ORDER BY date DESC LIMIT 1",
            (portfolio_id,),
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Risk metrics not found")
    return dict(row)


@router.get("/portfolios/{portfolio_id}/concentration", response_model=ConcentrationResponse)
async def get_concentration(portfolio_id: int) -> dict:
    """集中度分析を取得する。"""
    db = await get_db()
    holdings = await db.execute_fetchall(
        "SELECT ticker, name, sector, shares, buy_price FROM holdings WHERE portfolio_id = ?",
        (portfolio_id,),
    )
    if not holdings:
        return {"hhi": 0.0, "top_holdings": [], "sector_weights": {}, "warnings": []}

    total_value = sum(h["shares"] * h["buy_price"] for h in holdings)
    if total_value == 0:
        return {"hhi": 0.0, "top_holdings": [], "sector_weights": {}, "warnings": []}

    weights: dict[str, float] = {}
    sector_totals: dict[str, float] = {}
    top_holdings = []

    for h in holdings:
        val = h["shares"] * h["buy_price"]
        w = val / total_value
        weights[h["ticker"]] = w
        sector = h["sector"] or "Unknown"
        sector_totals[sector] = sector_totals.get(sector, 0.0) + w
        top_holdings.append({
            "ticker": h["ticker"],
            "name": h["name"],
            "weight": round(w * 100, 2),
        })

    top_holdings.sort(key=lambda x: x["weight"], reverse=True)
    hhi = sum(w ** 2 for w in weights.values())

    warnings: list[str] = []
    for h in top_holdings:
        if h["weight"] > 30:
            warnings.append(f"{h['ticker']}が{h['weight']:.1f}%を占めています（30%超過）")
    for sector, sw in sector_totals.items():
        if sw > 0.5:
            warnings.append(f"{sector}セクターが{sw*100:.1f}%を占めています（50%超過）")

    return {
        "hhi": round(hhi, 4),
        "top_holdings": top_holdings[:10],
        "sector_weights": {k: round(v * 100, 2) for k, v in sector_totals.items()},
        "warnings": warnings,
    }


@router.post(
    "/portfolios/{portfolio_id}/stop-loss",
    response_model=StopLossResponse,
    status_code=201,
)
async def create_stop_loss(portfolio_id: int, body: StopLossCreate) -> dict:
    """損切りルールを設定する。"""
    db = await get_db()
    pf = await db.execute_fetchone("SELECT id FROM portfolios WHERE id = ?", (portfolio_id,))
    if pf is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    cursor = await db.execute(
        "INSERT INTO stop_loss_rules "
        "(portfolio_id, ticker, buy_price, stop_loss_pct, trailing_stop, highest_price, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?, 1)",
        (
            portfolio_id,
            body.ticker,
            body.buy_price,
            body.stop_loss_pct,
            body.trailing_stop,
            body.buy_price,
        ),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "portfolio_id": portfolio_id,
        "ticker": body.ticker,
        "buy_price": body.buy_price,
        "stop_loss_pct": body.stop_loss_pct,
        "trailing_stop": body.trailing_stop,
        "highest_price": body.buy_price,
        "is_active": True,
    }
