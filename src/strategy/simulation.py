"""What-If シミュレーション.

以下の2種類のシミュレーションを提供する:
  SIM-1: 損切りしなかった場合のシミュレーション
  SIM-2: 集中投資を続けた場合のシミュレーション
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.data.fetcher import fetch_price_history
from src.strategy.risk import (
    calculate_hhi,
    calculate_max_drawdown,
    calculate_volatility,
)


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """シミュレーション結果を格納するデータクラス."""

    scenario_type: str  # "stop_loss" | "concentration"
    title: str
    summary: str
    result_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# SIM-1: 損切りしなかった場合
# ---------------------------------------------------------------------------

def simulate_no_stop_loss(
    ticker: str,
    buy_price: float,
    shares: int,
    stop_loss_pct: float = -0.10,
    period: str = "1y",
) -> SimulationResult:
    """損切りしなかった場合と損切りした場合を比較するシミュレーション.

    Args:
        ticker: 銘柄コード
        buy_price: 取得価格
        shares: 保有株数
        stop_loss_pct: 損切りライン (例: -0.10 = -10%)
        period: 株価取得期間

    Returns:
        SimulationResult
    """
    df = fetch_price_history(ticker, period=period)
    if df.empty or len(df) < 2:
        return SimulationResult(
            scenario_type="stop_loss",
            title=f"SIM-1: {ticker} 損切りシミュレーション",
            summary="株価データが不足しているためシミュレーションを実行できません。",
        )

    prices = df["close"].values.astype(float)
    stop_loss_price = buy_price * (1 + stop_loss_pct)

    stop_loss_triggered_idx: int | None = None
    for i, price in enumerate(prices):
        if price <= stop_loss_price:
            stop_loss_triggered_idx = i
            break

    if stop_loss_triggered_idx is None:
        final_price = float(prices[-1])
        hold_pnl = (final_price - buy_price) * shares
        hold_pnl_pct = (final_price - buy_price) / buy_price * 100

        return SimulationResult(
            scenario_type="stop_loss",
            title=f"SIM-1: {ticker} 損切りシミュレーション",
            summary=(
                f"この期間では損切りライン（{stop_loss_pct*100:+.0f}%）に達しませんでした。"
                f"保有を続けた場合の損益: {hold_pnl:+,.0f}円（{hold_pnl_pct:+.1f}%）"
            ),
            result_data={
                "stop_loss_triggered": False,
                "final_price": final_price,
                "hold_pnl": round(hold_pnl),
                "hold_pnl_pct": round(hold_pnl_pct, 2),
            },
        )

    # 損切りした場合
    stop_loss_actual_price = float(prices[stop_loss_triggered_idx])
    stop_loss_pnl = (stop_loss_actual_price - buy_price) * shares
    stop_loss_pnl_pct = (stop_loss_actual_price - buy_price) / buy_price * 100

    # 保有を続けた場合
    final_price = float(prices[-1])
    hold_pnl = (final_price - buy_price) * shares
    hold_pnl_pct = (final_price - buy_price) / buy_price * 100

    # 損切り後の最安値・最高値
    remaining_prices = prices[stop_loss_triggered_idx:]
    min_after = float(np.min(remaining_prices))
    worst_case_pnl = (min_after - buy_price) * shares
    worst_case_pnl_pct = (min_after - buy_price) / buy_price * 100

    recovered = final_price >= buy_price

    if hold_pnl > stop_loss_pnl:
        summary = (
            f"損切りしなかった方が結果的には良かった場合です。"
            f"損切り時: {stop_loss_pnl:+,.0f}円（{stop_loss_pnl_pct:+.1f}%）"
            f" → 保有継続: {hold_pnl:+,.0f}円（{hold_pnl_pct:+.1f}%）。"
            f"ただし途中で最大{worst_case_pnl:+,.0f}円（{worst_case_pnl_pct:+.1f}%）まで下がるリスクがありました。"
        )
    else:
        summary = (
            f"損切りが正解でした。"
            f"損切り時: {stop_loss_pnl:+,.0f}円（{stop_loss_pnl_pct:+.1f}%）"
            f" → 保有継続: {hold_pnl:+,.0f}円（{hold_pnl_pct:+.1f}%）。"
            f"損切りにより{stop_loss_pnl - hold_pnl:,.0f}円の損失を回避できました。"
        )

    return SimulationResult(
        scenario_type="stop_loss",
        title=f"SIM-1: {ticker} 損切りシミュレーション",
        summary=summary,
        result_data={
            "stop_loss_triggered": True,
            "stop_loss_day": stop_loss_triggered_idx,
            "stop_loss_price": round(stop_loss_actual_price, 2),
            "stop_loss_pnl": round(stop_loss_pnl),
            "stop_loss_pnl_pct": round(stop_loss_pnl_pct, 2),
            "hold_final_price": round(final_price, 2),
            "hold_pnl": round(hold_pnl),
            "hold_pnl_pct": round(hold_pnl_pct, 2),
            "worst_case_pnl": round(worst_case_pnl),
            "worst_case_pnl_pct": round(worst_case_pnl_pct, 2),
            "recovered": recovered,
            "stop_loss_was_better": stop_loss_pnl >= hold_pnl,
        },
    )


# ---------------------------------------------------------------------------
# SIM-2: 集中投資を続けた場合
# ---------------------------------------------------------------------------

def simulate_concentration_risk(
    holdings: list[dict[str, Any]],
    concentrated_ticker: str,
    period: str = "1y",
) -> SimulationResult:
    """集中投資を続けた場合のリスクをシミュレーションする.

    Args:
        holdings: 保有銘柄リスト。
            {"ticker", "shares", "buy_price"} を含む dict のリスト
        concentrated_ticker: 集中対象の銘柄コード
        period: 株価取得期間

    Returns:
        SimulationResult
    """
    if not holdings:
        return SimulationResult(
            scenario_type="concentration",
            title="SIM-2: 集中投資シミュレーション",
            summary="ポートフォリオデータがありません。",
        )

    returns_dict: dict[str, pd.Series] = {}
    weights: dict[str, float] = {}

    for holding in holdings:
        ticker = holding["ticker"]
        df = fetch_price_history(ticker, period=period)
        if df.empty or len(df) < 2:
            continue
        returns_dict[ticker] = df["close"].pct_change().dropna()
        current_price = float(df["close"].iloc[-1])
        weights[ticker] = current_price * float(holding.get("shares", 0))

    total_value = sum(weights.values())
    if total_value == 0 or concentrated_ticker not in returns_dict:
        return SimulationResult(
            scenario_type="concentration",
            title=f"SIM-2: {concentrated_ticker} 集中投資シミュレーション",
            summary="データが不足しているためシミュレーションを実行できません。",
        )

    norm_weights = {t: v / total_value for t, v in weights.items()}

    aligned = pd.DataFrame(returns_dict).dropna()
    if aligned.empty:
        return SimulationResult(
            scenario_type="concentration",
            title=f"SIM-2: {concentrated_ticker} 集中投資シミュレーション",
            summary="日次リターンデータを構築できません。",
        )

    portfolio_returns = pd.Series(0.0, index=aligned.index)
    for ticker, w in norm_weights.items():
        if ticker in aligned.columns:
            portfolio_returns += aligned[ticker] * w

    concentrated_returns = aligned[concentrated_ticker]

    port_vol = calculate_volatility(portfolio_returns) * 100
    conc_vol = calculate_volatility(concentrated_returns) * 100

    port_cumulative = (1 + portfolio_returns).cumprod()
    conc_cumulative = (1 + concentrated_returns).cumprod()

    port_mdd = calculate_max_drawdown(port_cumulative) * 100
    conc_mdd = calculate_max_drawdown(conc_cumulative) * 100

    port_total_return = (float(port_cumulative.iloc[-1]) - 1) * 100
    conc_total_return = (float(conc_cumulative.iloc[-1]) - 1) * 100

    port_hhi = calculate_hhi(norm_weights)
    conc_hhi = 1.0

    concentration_ratio = norm_weights.get(concentrated_ticker, 0) * 100

    summary = (
        f"{concentrated_ticker}に100%集中した場合 vs 現在の分散ポートフォリオ:\n"
        f"  リターン: 集中{conc_total_return:+.1f}% vs 分散{port_total_return:+.1f}%\n"
        f"  ボラティリティ: 集中{conc_vol:.1f}% vs 分散{port_vol:.1f}%\n"
        f"  最大ドローダウン: 集中{conc_mdd:.1f}% vs 分散{port_mdd:.1f}%\n"
        f"現在の{concentrated_ticker}の比率: {concentration_ratio:.1f}%"
    )

    return SimulationResult(
        scenario_type="concentration",
        title=f"SIM-2: {concentrated_ticker} 集中投資シミュレーション",
        summary=summary,
        result_data={
            "concentrated_ticker": concentrated_ticker,
            "current_weight_pct": round(concentration_ratio, 2),
            "portfolio": {
                "total_return_pct": round(port_total_return, 2),
                "volatility_pct": round(port_vol, 2),
                "max_drawdown_pct": round(port_mdd, 2),
                "hhi": round(port_hhi, 4),
            },
            "concentrated": {
                "total_return_pct": round(conc_total_return, 2),
                "volatility_pct": round(conc_vol, 2),
                "max_drawdown_pct": round(conc_mdd, 2),
                "hhi": round(conc_hhi, 4),
            },
        },
    )
