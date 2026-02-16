"""Portfolio CRUD & watchlist endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.api.database import get_db
from src.api.models import (
    HoldingAdd,
    HoldingResponse,
    PortfolioCreate,
    PortfolioDetailResponse,
    PortfolioResponse,
    WatchlistAdd,
    WatchlistResponse,
)

router = APIRouter()


# ---------- Portfolios ----------


@router.get("/portfolios", response_model=list[PortfolioResponse])
async def list_portfolios() -> list[dict]:
    """ポートフォリオ一覧を取得する。"""
    db = await get_db()
    rows = await db.execute_fetchall("SELECT id, name, created_at FROM portfolios ORDER BY id")
    return [dict(r) for r in rows]


@router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(body: PortfolioCreate) -> dict:
    """ポートフォリオを新規作成する。"""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO portfolios (name, created_at) VALUES (?, ?)",
        (body.name, now),
    )
    await db.commit()
    return {"id": cursor.lastrowid, "name": body.name, "created_at": now}


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioDetailResponse)
async def get_portfolio(portfolio_id: int) -> dict:
    """ポートフォリオ詳細（保有銘柄含む）を取得する。"""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT id, name, created_at FROM portfolios WHERE id = ?",
        (portfolio_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings = await db.execute_fetchall(
        "SELECT id, portfolio_id, ticker, name, sector, shares, buy_price, buy_date, created_at "
        "FROM holdings WHERE portfolio_id = ? ORDER BY id",
        (portfolio_id,),
    )
    result = dict(row)
    result["holdings"] = [dict(h) for h in holdings]
    return result


@router.post(
    "/portfolios/{portfolio_id}/holdings",
    response_model=HoldingResponse,
    status_code=201,
)
async def add_holding(portfolio_id: int, body: HoldingAdd) -> dict:
    """保有銘柄を追加する。"""
    db = await get_db()
    # ポートフォリオ存在チェック
    pf = await db.execute_fetchone(
        "SELECT id FROM portfolios WHERE id = ?", (portfolio_id,)
    )
    if pf is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO holdings (portfolio_id, ticker, name, sector, shares, buy_price, buy_date, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            portfolio_id,
            body.ticker,
            body.name,
            body.sector,
            body.shares,
            body.buy_price,
            body.buy_date.isoformat(),
            now,
        ),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "portfolio_id": portfolio_id,
        "ticker": body.ticker,
        "name": body.name,
        "sector": body.sector,
        "shares": body.shares,
        "buy_price": body.buy_price,
        "buy_date": body.buy_date,
        "created_at": now,
    }


@router.delete("/portfolios/{portfolio_id}/holdings/{ticker}", status_code=204)
async def delete_holding(portfolio_id: int, ticker: str) -> None:
    """保有銘柄を削除する。"""
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM holdings WHERE portfolio_id = ? AND ticker = ?",
        (portfolio_id, ticker),
    )
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Holding not found")


# ---------- Watchlist ----------


@router.get("/watchlist", response_model=list[WatchlistResponse])
async def list_watchlist() -> list[dict]:
    """ウォッチリスト一覧を取得する。"""
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, ticker, name, reason, added_at FROM watchlist ORDER BY added_at DESC"
    )
    return [dict(r) for r in rows]


@router.post("/watchlist", response_model=WatchlistResponse, status_code=201)
async def add_to_watchlist(body: WatchlistAdd) -> dict:
    """ウォッチリストに銘柄を追加する。"""
    db = await get_db()
    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO watchlist (ticker, name, reason, added_at) VALUES (?, ?, ?, ?)",
        (body.ticker, body.name, body.reason, now),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "ticker": body.ticker,
        "name": body.name,
        "reason": body.reason,
        "added_at": now,
    }


@router.delete("/watchlist/{ticker}", status_code=204)
async def remove_from_watchlist(ticker: str) -> None:
    """ウォッチリストから銘柄を削除する。"""
    db = await get_db()
    cursor = await db.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
