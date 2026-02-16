"""Simulation endpoints: paper-trade, what-if scenarios."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from src.api.database import get_db
from src.api.models import (
    PaperPortfolioResponse,
    PaperTradeRequest,
    PaperTradeResponse,
    SimulationResultResponse,
    WhatIfRequest,
)

router = APIRouter()

INITIAL_VIRTUAL_BALANCE = 1_000_000.0  # 仮想資金100万円


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_virtual_balance(user_id: int) -> float:
    """Return the user's latest virtual balance, or initial balance if none."""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT virtual_balance FROM simulation_trades "
        "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    if row is not None:
        return float(row["virtual_balance"])
    return INITIAL_VIRTUAL_BALANCE


# ---------------------------------------------------------------------------
# Paper Trade
# ---------------------------------------------------------------------------


@router.post("/simulation/paper-trade", response_model=PaperTradeResponse, status_code=201)
async def execute_paper_trade(body: PaperTradeRequest, user_id: int = Query(1)) -> dict:
    """ペーパートレードを実行する。"""
    db = await get_db()
    balance = await _get_virtual_balance(user_id)
    trade_value = body.price * body.quantity

    if body.action == "buy":
        if trade_value > balance:
            raise HTTPException(
                status_code=400,
                detail=f"残高不足です。必要: {trade_value:,.0f}円, 残高: {balance:,.0f}円",
            )
        new_balance = balance - trade_value
    else:
        # sell: check if user holds enough
        held = await db.execute_fetchone(
            "SELECT COALESCE(SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END), 0) as qty "
            "FROM simulation_trades WHERE user_id = ? AND ticker = ?",
            (user_id, body.ticker),
        )
        held_qty = held["qty"] if held else 0
        if held_qty < body.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"保有数量不足です。保有: {held_qty}株, 売却: {body.quantity}株",
            )
        new_balance = balance + trade_value

    now = datetime.utcnow().isoformat()
    cursor = await db.execute(
        "INSERT INTO simulation_trades (user_id, ticker, action, price, quantity, virtual_balance, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, body.ticker, body.action, body.price, body.quantity, new_balance, now),
    )
    await db.commit()

    return {
        "id": cursor.lastrowid,
        "ticker": body.ticker,
        "action": body.action,
        "price": body.price,
        "quantity": body.quantity,
        "virtual_balance": new_balance,
        "created_at": now,
    }


@router.get("/simulation/paper-portfolio", response_model=PaperPortfolioResponse)
async def get_paper_portfolio(user_id: int = Query(1)) -> dict:
    """ペーパーポートフォリオを取得する。"""
    db = await get_db()
    balance = await _get_virtual_balance(user_id)

    rows = await db.execute_fetchall(
        "SELECT ticker, "
        "SUM(CASE WHEN action='buy' THEN quantity ELSE -quantity END) as qty, "
        "SUM(CASE WHEN action='buy' THEN price * quantity ELSE 0 END) as total_cost, "
        "SUM(CASE WHEN action='buy' THEN quantity ELSE 0 END) as buy_qty "
        "FROM simulation_trades WHERE user_id = ? GROUP BY ticker HAVING qty > 0",
        (user_id,),
    )
    holdings = []
    holdings_value = 0.0
    for r in rows:
        qty = int(r["qty"])
        avg_price = r["total_cost"] / r["buy_qty"] if r["buy_qty"] > 0 else 0
        est_value = avg_price * qty
        holdings_value += est_value
        holdings.append({
            "ticker": r["ticker"],
            "quantity": qty,
            "avg_price": round(avg_price, 2),
            "current_value": round(est_value, 2),
        })

    return {
        "virtual_balance": balance,
        "holdings": holdings,
        "total_value": round(balance + holdings_value, 2),
    }


# ---------------------------------------------------------------------------
# What-If Simulation
# ---------------------------------------------------------------------------


@router.post("/simulation/what-if", response_model=SimulationResultResponse, status_code=201)
async def run_what_if(body: WhatIfRequest, user_id: int = Query(1)) -> dict:
    """What-Ifシミュレーションを実行する。"""
    db = await get_db()
    now = datetime.utcnow().isoformat()

    # Produce result based on scenario type
    summary, result_data = _run_scenario(body.scenario_type, body.parameters)

    cursor = await db.execute(
        "INSERT INTO simulation_scenarios (user_id, scenario_type, parameters, result_summary, result_data, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            body.scenario_type,
            json.dumps(body.parameters, ensure_ascii=False),
            summary,
            json.dumps(result_data, ensure_ascii=False),
            now,
        ),
    )
    await db.commit()

    return {
        "id": cursor.lastrowid,
        "scenario_type": body.scenario_type,
        "parameters": body.parameters,
        "result_summary": summary,
        "result_data": result_data,
        "created_at": now,
    }


@router.get("/simulation/{sim_id}/result", response_model=SimulationResultResponse)
async def get_simulation_result(sim_id: int) -> dict:
    """シミュレーション結果を取得する。"""
    db = await get_db()
    row = await db.execute_fetchone(
        "SELECT id, scenario_type, parameters, result_summary, result_data, created_at "
        "FROM simulation_scenarios WHERE id = ?",
        (sim_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {
        "id": row["id"],
        "scenario_type": row["scenario_type"],
        "parameters": json.loads(row["parameters"]) if row["parameters"] else {},
        "result_summary": row["result_summary"] or "",
        "result_data": json.loads(row["result_data"]) if row["result_data"] else {},
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Scenario runners (simplified – strategy layer will provide real calculations)
# ---------------------------------------------------------------------------


def _run_scenario(scenario_type: str, params: dict) -> tuple[str, dict]:
    """Run a What-If scenario and return (summary, result_data).

    These are placeholder calculations. The strategy layer (simulation.py)
    will eventually provide more sophisticated modeling.
    """
    if scenario_type == "stop_loss":
        ticker = params.get("ticker", "N/A")
        buy_price = params.get("buy_price", 1000)
        current_price = params.get("current_price", 900)
        loss_pct = (current_price - buy_price) / buy_price * 100
        no_stop_price = params.get("worst_case_price", buy_price * 0.5)
        no_stop_loss = (no_stop_price - buy_price) / buy_price * 100
        return (
            f"損切りしなかった場合、{ticker}の損失は最大{no_stop_loss:.1f}%に拡大する可能性があります。"
            f"損切り実行で損失を{loss_pct:.1f}%に抑えられます。",
            {
                "ticker": ticker,
                "with_stop_loss": round(loss_pct, 2),
                "without_stop_loss": round(no_stop_loss, 2),
                "saved_amount_pct": round(no_stop_loss - loss_pct, 2),
            },
        )

    if scenario_type == "concentration":
        top_weight = params.get("top_weight", 50)
        ideal_weight = params.get("ideal_weight", 20)
        drop_pct = params.get("drop_pct", 30)
        concentrated_loss = top_weight * drop_pct / 100
        diversified_loss = ideal_weight * drop_pct / 100
        return (
            f"集中投資のまま{drop_pct}%下落した場合、ポートフォリオは{concentrated_loss:.1f}%の損失。"
            f"分散していれば{diversified_loss:.1f}%で済みます。",
            {
                "concentrated_impact": round(concentrated_loss, 2),
                "diversified_impact": round(diversified_loss, 2),
                "difference": round(concentrated_loss - diversified_loss, 2),
            },
        )

    if scenario_type == "stress_test":
        scenario_name = params.get("scenario_name", "リーマンショック級")
        market_drop = params.get("market_drop", -40)
        beta = params.get("portfolio_beta", 1.0)
        estimated_drop = market_drop * beta
        return (
            f"{scenario_name}（市場{market_drop}%）の場合、ポートフォリオは約{estimated_drop:.1f}%下落する試算です。",
            {
                "scenario": scenario_name,
                "market_drop_pct": market_drop,
                "portfolio_beta": beta,
                "estimated_portfolio_drop": round(estimated_drop, 2),
            },
        )

    if scenario_type == "diversification":
        current_hhi = params.get("current_hhi", 3000)
        ideal_hhi = params.get("ideal_hhi", 1500)
        improvement = (current_hhi - ideal_hhi) / current_hhi * 100
        return (
            f"分散を改善すると集中度が{improvement:.0f}%低下し、リスクが軽減されます。",
            {
                "current_hhi": current_hhi,
                "ideal_hhi": ideal_hhi,
                "improvement_pct": round(improvement, 2),
            },
        )

    return ("シナリオの計算結果です。", {"message": "result placeholder"})
