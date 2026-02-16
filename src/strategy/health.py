"""健全度スコア算出モジュール.

セクション5のロジックに基づき、以下の5要素の加重合計で算出する:
  分散度(30%) + ボラティリティ(25%) + ドローダウン(20%) + 相関(15%) + 含み損(10%)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from src.data.fetcher import fetch_price_history
from src.strategy.risk import (
    RiskMetrics,
    calculate_risk_metrics,
)


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class HealthScore:
    """健全度スコアとその内訳を格納するデータクラス."""

    total: float
    level: str  # "green" | "yellow" | "red"
    message: str
    breakdown: dict[str, float]
    detail: dict[str, Any]


# ---------------------------------------------------------------------------
# 定数 (セクション5の基準値)
# ---------------------------------------------------------------------------

# 分散度 (HHI ベース)
_HHI_GOOD = 0.1    # HHI < 0.1 で 100 点
_HHI_BAD = 0.5     # HHI > 0.5 で 0 点

# ボラティリティ (年率)
_VOL_GOOD = 0.15   # 年率 σ < 15% で 100 点
_VOL_BAD = 0.40    # 年率 σ > 40% で 0 点

# ドローダウン (MDD)
_MDD_GOOD = 0.05   # MDD < 5% で 100 点
_MDD_BAD = 0.30    # MDD > 30% で 0 点

# 相関 (平均相関係数)
_CORR_GOOD = 0.3   # 平均相関 < 0.3 で 100 点
_CORR_BAD = 0.8    # 平均相関 > 0.8 で 0 点

# 含み損 (含み損銘柄比率)
_LOSS_GOOD = 0.0   # 含み損銘柄 0% で 100 点
_LOSS_BAD = 0.5    # 含み損銘柄 > 50% で 0 点

# 配点ウェイト
_WEIGHT_DIVERSITY = 0.30
_WEIGHT_VOLATILITY = 0.25
_WEIGHT_DRAWDOWN = 0.20
_WEIGHT_CORRELATION = 0.15
_WEIGHT_UNREALIZED_LOSS = 0.10

# 信号機
_LEVEL_GREEN = 70
_LEVEL_YELLOW = 40


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _score_inverse(value: float, good: float, bad: float) -> float:
    """値が低いほど高スコアになる逆正規化 (0-100).

    *good* 以下で 100、*bad* 以上で 0。
    """
    if bad == good:
        return 50.0
    score = (bad - value) / (bad - good) * 100.0
    return float(np.clip(score, 0.0, 100.0))


def _determine_level(score: float) -> tuple[str, str]:
    """スコアから信号機レベルとメッセージを決定する.

    Returns:
        (level, message) のタプル
    """
    if score >= _LEVEL_GREEN:
        return "green", "健全です。特にアクションは不要です。"
    elif score >= _LEVEL_YELLOW:
        return "yellow", "注意が必要です。改善ポイントを確認してください。"
    else:
        return "red", "危険な状態です。具体的なアクションを検討してください。"


# ---------------------------------------------------------------------------
# 含み損比率算出
# ---------------------------------------------------------------------------

def _calc_unrealized_loss_ratio(
    holdings: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """含み損銘柄の比率を算出する.

    Args:
        holdings: 保有銘柄リスト。各要素は {"ticker", "shares", "buy_price"} を含む dict

    Returns:
        (含み損銘柄比率, 詳細dict) のタプル
    """
    if not holdings:
        return 0.0, {}

    loss_count = 0
    detail: dict[str, float] = {}

    for holding in holdings:
        ticker = holding["ticker"]
        buy_price = float(holding.get("buy_price", 0))
        if buy_price <= 0:
            continue

        df = fetch_price_history(ticker, period="5d")
        if df.empty:
            continue

        current_price = float(df["close"].iloc[-1])
        pnl_pct = (current_price - buy_price) / buy_price

        if pnl_pct < 0:
            loss_count += 1
        detail[ticker] = round(pnl_pct, 4)

    total = len(holdings)
    ratio = loss_count / total if total > 0 else 0.0
    return ratio, {"pnl_by_ticker": detail, "loss_count": loss_count, "total": total}


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def calculate_health_score(
    holdings: list[dict[str, Any]],
    *,
    risk_metrics: RiskMetrics | None = None,
    period: str = "1y",
) -> HealthScore:
    """ポートフォリオの健全度スコア (0-100) を算出する.

    健全度 = 分散度(30%) + ボラティリティ(25%) + ドローダウン(20%)
           + 相関(15%) + 含み損(10%)

    Args:
        holdings: 保有銘柄リスト。各要素は {"ticker", "shares", "buy_price"} を含む dict
        risk_metrics: 事前算出済みの RiskMetrics。None の場合は内部で算出する
        period: 株価取得期間 (risk_metrics を内部算出する場合に使用)

    Returns:
        HealthScore データクラス
    """
    if not holdings:
        return HealthScore(
            total=0.0,
            level="red",
            message="ポートフォリオに保有銘柄がありません。",
            breakdown={},
            detail={},
        )

    # リスク指標を算出
    if risk_metrics is None:
        risk_metrics = calculate_risk_metrics(holdings, period=period)

    # 各要素のスコア算出
    diversity_score = _score_inverse(risk_metrics.hhi, _HHI_GOOD, _HHI_BAD)
    volatility_score = _score_inverse(
        risk_metrics.portfolio_volatility, _VOL_GOOD, _VOL_BAD
    )
    drawdown_score = _score_inverse(risk_metrics.max_drawdown, _MDD_GOOD, _MDD_BAD)
    correlation_score = _score_inverse(
        risk_metrics.avg_correlation, _CORR_GOOD, _CORR_BAD
    )

    loss_ratio, loss_detail = _calc_unrealized_loss_ratio(holdings)
    loss_score = _score_inverse(loss_ratio, _LOSS_GOOD, _LOSS_BAD)

    # 加重合計
    total = (
        diversity_score * _WEIGHT_DIVERSITY
        + volatility_score * _WEIGHT_VOLATILITY
        + drawdown_score * _WEIGHT_DRAWDOWN
        + correlation_score * _WEIGHT_CORRELATION
        + loss_score * _WEIGHT_UNREALIZED_LOSS
    )
    total = round(float(np.clip(total, 0.0, 100.0)), 2)

    level, message = _determine_level(total)

    return HealthScore(
        total=total,
        level=level,
        message=message,
        breakdown={
            "diversity": round(diversity_score, 2),
            "volatility": round(volatility_score, 2),
            "drawdown": round(drawdown_score, 2),
            "correlation": round(correlation_score, 2),
            "unrealized_loss": round(loss_score, 2),
        },
        detail={
            "weights": {
                "diversity": _WEIGHT_DIVERSITY,
                "volatility": _WEIGHT_VOLATILITY,
                "drawdown": _WEIGHT_DRAWDOWN,
                "correlation": _WEIGHT_CORRELATION,
                "unrealized_loss": _WEIGHT_UNREALIZED_LOSS,
            },
            "risk_metrics": {
                "hhi": risk_metrics.hhi,
                "portfolio_volatility": risk_metrics.portfolio_volatility,
                "max_drawdown": risk_metrics.max_drawdown,
                "avg_correlation": risk_metrics.avg_correlation,
                "sharpe_ratio": risk_metrics.sharpe_ratio,
            },
            "unrealized_loss": loss_detail,
        },
    )
