"""What-If シミュレーション.

以下の4種類のシミュレーションを提供する:
  SIM-1: 損切りしなかった場合のシミュレーション
  SIM-2: 集中投資を続けた場合のシミュレーション
  SIM-3: ストレステスト（リーマン/コロナ/ITバブル）
  SIM-4: 分散効果のシミュレーション
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

    scenario_type: str  # "stop_loss" | "concentration" | "stress_test" | "diversification"
    title: str
    summary: str
    result_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# ストレステスト用 歴史的暴落シナリオ
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CrashScenario:
    """歴史的暴落シナリオの定義."""

    name: str
    description: str
    market_drop_pct: float  # 市場全体の下落率 (例: -0.50 = -50%)
    duration_days: int  # 暴落期間 (日数)
    recovery_days: int  # 回復までの日数
    high_beta_multiplier: float  # 高βセクターへの影響倍率
    low_beta_multiplier: float  # 低βセクターへの影響倍率


CRASH_SCENARIOS: dict[str, CrashScenario] = {
    "lehman": CrashScenario(
        name="リーマンショック級",
        description="2008年のリーマンショック級の金融危機を想定",
        market_drop_pct=-0.50,
        duration_days=380,
        recovery_days=900,
        high_beta_multiplier=1.5,
        low_beta_multiplier=0.7,
    ),
    "covid": CrashScenario(
        name="コロナショック級",
        description="2020年のコロナショック級の急落を想定",
        market_drop_pct=-0.35,
        duration_days=33,
        recovery_days=150,
        high_beta_multiplier=1.3,
        low_beta_multiplier=0.8,
    ),
    "dot_com": CrashScenario(
        name="ITバブル崩壊級",
        description="2000年のITバブル崩壊級の長期下落を想定",
        market_drop_pct=-0.45,
        duration_days=640,
        recovery_days=1800,
        high_beta_multiplier=2.0,
        low_beta_multiplier=0.5,
    ),
}


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

    損切りラインで売却した場合の確定損失と、保有を続けた場合の
    その後の値動きを比較する。

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

    # 損切りが発動するポイントを特定
    stop_loss_triggered_idx: int | None = None
    for i, price in enumerate(prices):
        if price <= stop_loss_price:
            stop_loss_triggered_idx = i
            break

    if stop_loss_triggered_idx is None:
        # 損切りラインに達しなかった
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
    max_after = float(np.max(remaining_prices))
    worst_case_pnl = (min_after - buy_price) * shares
    worst_case_pnl_pct = (min_after - buy_price) / buy_price * 100

    # 回復したかどうか
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

    現在のポートフォリオ配分と、特定銘柄に100%集中した場合の
    リスク・リターンを比較する。

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

    # 各銘柄の日次リターンを取得
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

    # 現在のポートフォリオリターン
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

    # 集中投資のリターン
    concentrated_returns = aligned[concentrated_ticker]

    # リスク指標を比較
    port_vol = calculate_volatility(portfolio_returns) * 100
    conc_vol = calculate_volatility(concentrated_returns) * 100

    port_cumulative = (1 + portfolio_returns).cumprod()
    conc_cumulative = (1 + concentrated_returns).cumprod()

    port_mdd = calculate_max_drawdown(port_cumulative) * 100
    conc_mdd = calculate_max_drawdown(conc_cumulative) * 100

    port_total_return = (float(port_cumulative.iloc[-1]) - 1) * 100
    conc_total_return = (float(conc_cumulative.iloc[-1]) - 1) * 100

    port_hhi = calculate_hhi(norm_weights)
    conc_hhi = 1.0  # 100% 集中

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


# ---------------------------------------------------------------------------
# SIM-3: ストレステスト
# ---------------------------------------------------------------------------

def simulate_stress_test(
    holdings: list[dict[str, Any]],
    scenario_key: str = "lehman",
    betas: dict[str, float] | None = None,
) -> SimulationResult:
    """歴史的暴落シナリオでのポートフォリオ影響をシミュレーションする.

    各銘柄のβ値を用いて暴落時の推定損失額を算出する。

    Args:
        holdings: 保有銘柄リスト。
            {"ticker", "shares", "buy_price"} を含む dict のリスト
        scenario_key: シナリオキー ("lehman", "covid", "dot_com")
        betas: 銘柄ごとのβ値。None の場合はデフォルト1.0を使用

    Returns:
        SimulationResult
    """
    scenario = CRASH_SCENARIOS.get(scenario_key)
    if scenario is None:
        return SimulationResult(
            scenario_type="stress_test",
            title="SIM-3: ストレステスト",
            summary=f"不明なシナリオ: {scenario_key}",
        )

    if not holdings:
        return SimulationResult(
            scenario_type="stress_test",
            title=f"SIM-3: {scenario.name}ストレステスト",
            summary="ポートフォリオデータがありません。",
        )

    if betas is None:
        betas = {}

    # 各銘柄の推定損失を算出
    ticker_impacts: list[dict[str, Any]] = []
    total_value = 0.0
    total_loss = 0.0

    for holding in holdings:
        ticker = holding["ticker"]
        shares = float(holding.get("shares", 0))

        df = fetch_price_history(ticker, period="5d")
        if df.empty:
            continue

        current_price = float(df["close"].iloc[-1])
        position_value = current_price * shares
        total_value += position_value

        beta = betas.get(ticker, 1.0)

        # β値に応じた影響度を算出
        if beta >= 1.2:
            multiplier = scenario.high_beta_multiplier
        elif beta <= 0.8:
            multiplier = scenario.low_beta_multiplier
        else:
            multiplier = 1.0

        estimated_drop = scenario.market_drop_pct * beta * multiplier
        estimated_loss = position_value * estimated_drop

        total_loss += estimated_loss

        ticker_impacts.append({
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "position_value": round(position_value),
            "beta": round(beta, 2),
            "estimated_drop_pct": round(estimated_drop * 100, 1),
            "estimated_loss": round(estimated_loss),
        })

    if total_value == 0:
        return SimulationResult(
            scenario_type="stress_test",
            title=f"SIM-3: {scenario.name}ストレステスト",
            summary="評価額を算出できません。",
        )

    total_loss_pct = total_loss / total_value * 100

    # 銘柄をインパクト順にソート
    ticker_impacts.sort(key=lambda x: x["estimated_loss"])

    summary = (
        f"【{scenario.name}】が発生した場合の推定影響:\n"
        f"  ポートフォリオ評価額: {total_value:,.0f}円\n"
        f"  推定損失額: {total_loss:+,.0f}円（{total_loss_pct:+.1f}%）\n"
        f"  暴落期間: 約{scenario.duration_days}日\n"
        f"  回復までの目安: 約{scenario.recovery_days}日"
    )

    return SimulationResult(
        scenario_type="stress_test",
        title=f"SIM-3: {scenario.name}ストレステスト",
        summary=summary,
        result_data={
            "scenario": scenario_key,
            "scenario_name": scenario.name,
            "market_drop_pct": round(scenario.market_drop_pct * 100, 1),
            "duration_days": scenario.duration_days,
            "recovery_days": scenario.recovery_days,
            "portfolio_value": round(total_value),
            "estimated_total_loss": round(total_loss),
            "estimated_total_loss_pct": round(total_loss_pct, 2),
            "ticker_impacts": ticker_impacts,
        },
    )


# ---------------------------------------------------------------------------
# SIM-4: 分散効果シミュレーション
# ---------------------------------------------------------------------------

def simulate_diversification(
    holdings: list[dict[str, Any]],
    period: str = "1y",
) -> SimulationResult:
    """現在のポートフォリオと均等配分の分散効果を比較するシミュレーション.

    現在のウェイト配分 vs 均等配分でのリスク・リターン特性を比較し、
    分散による改善余地を示す。

    Args:
        holdings: 保有銘柄リスト。
            {"ticker", "shares", "buy_price"} を含む dict のリスト
        period: 株価取得期間

    Returns:
        SimulationResult
    """
    if not holdings or len(holdings) < 2:
        return SimulationResult(
            scenario_type="diversification",
            title="SIM-4: 分散効果シミュレーション",
            summary="分散効果を比較するには2銘柄以上が必要です。",
        )

    # 各銘柄のリターンとウェイトを取得
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
    if total_value == 0 or len(returns_dict) < 2:
        return SimulationResult(
            scenario_type="diversification",
            title="SIM-4: 分散効果シミュレーション",
            summary="データが不足しているためシミュレーションを実行できません。",
        )

    norm_weights = {t: v / total_value for t, v in weights.items()}
    equal_weight = 1.0 / len(returns_dict)

    aligned = pd.DataFrame(returns_dict).dropna()
    if aligned.empty:
        return SimulationResult(
            scenario_type="diversification",
            title="SIM-4: 分散効果シミュレーション",
            summary="日次リターンデータを構築できません。",
        )

    # 現在のポートフォリオ
    current_returns = pd.Series(0.0, index=aligned.index)
    for ticker, w in norm_weights.items():
        if ticker in aligned.columns:
            current_returns += aligned[ticker] * w

    # 均等配分ポートフォリオ
    equal_returns = pd.Series(0.0, index=aligned.index)
    for ticker in returns_dict:
        if ticker in aligned.columns:
            equal_returns += aligned[ticker] * equal_weight

    # リスク指標比較
    curr_vol = calculate_volatility(current_returns) * 100
    equal_vol = calculate_volatility(equal_returns) * 100

    curr_cumulative = (1 + current_returns).cumprod()
    equal_cumulative = (1 + equal_returns).cumprod()

    curr_mdd = calculate_max_drawdown(curr_cumulative) * 100
    equal_mdd = calculate_max_drawdown(equal_cumulative) * 100

    curr_total_return = (float(curr_cumulative.iloc[-1]) - 1) * 100
    equal_total_return = (float(equal_cumulative.iloc[-1]) - 1) * 100

    curr_hhi = calculate_hhi(norm_weights)
    equal_hhi = calculate_hhi({t: equal_weight for t in returns_dict})

    vol_improvement = curr_vol - equal_vol
    mdd_improvement = curr_mdd - equal_mdd

    summary = (
        f"現在のポートフォリオ vs 均等配分の比較:\n"
        f"  リターン: 現在{curr_total_return:+.1f}% vs 均等{equal_total_return:+.1f}%\n"
        f"  ボラティリティ: 現在{curr_vol:.1f}% vs 均等{equal_vol:.1f}%"
        f"（差: {vol_improvement:+.1f}pt）\n"
        f"  最大ドローダウン: 現在{curr_mdd:.1f}% vs 均等{equal_mdd:.1f}%"
        f"（差: {mdd_improvement:+.1f}pt）\n"
        f"  集中度(HHI): 現在{curr_hhi:.3f} vs 均等{equal_hhi:.3f}"
    )

    return SimulationResult(
        scenario_type="diversification",
        title="SIM-4: 分散効果シミュレーション",
        summary=summary,
        result_data={
            "num_holdings": len(returns_dict),
            "current": {
                "weights": {t: round(w * 100, 2) for t, w in norm_weights.items()},
                "total_return_pct": round(curr_total_return, 2),
                "volatility_pct": round(curr_vol, 2),
                "max_drawdown_pct": round(curr_mdd, 2),
                "hhi": round(curr_hhi, 4),
            },
            "equal_weight": {
                "weight_per_stock_pct": round(equal_weight * 100, 2),
                "total_return_pct": round(equal_total_return, 2),
                "volatility_pct": round(equal_vol, 2),
                "max_drawdown_pct": round(equal_mdd, 2),
                "hhi": round(equal_hhi, 4),
            },
            "improvement": {
                "volatility_diff_pt": round(vol_improvement, 2),
                "mdd_diff_pt": round(mdd_improvement, 2),
            },
        },
    )
