"""アラート生成モジュール.

セクション4の警告ルール (W-01 〜 W-10) に基づき、
ポートフォリオの状態に応じたアラートを生成する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

import pandas as pd

from src.data.fetcher import fetch_price_history, fetch_stock_info
from src.strategy.health import HealthScore, calculate_health_score
from src.strategy.risk import RiskMetrics, calculate_hhi


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class Alert:
    """生成されたアラートを格納するデータクラス."""

    alert_type: str       # "W-01" 〜 "W-10"
    level: int            # 1 (情報) 〜 4 (危険)
    ticker: str | None    # 銘柄コード。ポートフォリオ全体の場合は None
    message: str
    action_suggestion: str
    portfolio_id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    detail: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 閾値定数
# ---------------------------------------------------------------------------

# W-01: 日次急落
_DAILY_DROP_THRESHOLD = -0.05  # -5%

# W-02, W-03: 取得価格比
_LOSS_LEVEL2 = -0.10  # -10%
_LOSS_LEVEL4 = -0.15  # -15%

# W-04, W-05: 健全度スコア
_HEALTH_DANGER = 40
_HEALTH_CAUTION = 70

# W-06: 単一銘柄の比率
_SINGLE_STOCK_LIMIT = 0.30  # 30%

# W-07: 単一セクターの比率
_SINGLE_SECTOR_LIMIT = 0.50  # 50%

# W-08: 市場インデックス急落
_INDEX_DROP_THRESHOLD = -0.03  # -3%
_MARKET_INDICES = ["^N225", "^GSPC"]

# W-09: 保有銘柄の過半数下落
_MAJORITY_DROP_RATIO = 0.50  # 50%

# W-10: 含み損放置日数
_LOSS_STALE_DAYS = 30


# ---------------------------------------------------------------------------
# 個別アラート生成
# ---------------------------------------------------------------------------

def _check_w01_daily_drop(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-01: 個別銘柄が 1 日で -5% 以上下落.

    Level 2: 「{銘柄}が本日{X}%下落しました」
    """
    alerts: list[Alert] = []
    for holding in holdings:
        ticker = holding["ticker"]
        df = fetch_price_history(ticker, period="5d")
        if df.empty or len(df) < 2:
            continue

        today_close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        if prev_close == 0:
            continue

        daily_return = (today_close - prev_close) / prev_close
        if daily_return <= _DAILY_DROP_THRESHOLD:
            pct = round(daily_return * 100, 1)
            alerts.append(Alert(
                alert_type="W-01",
                level=2,
                ticker=ticker,
                message=f"{ticker}が本日{pct}%下落しました",
                action_suggestion="急落の原因を確認し、損切りラインを見直してください",
                detail={"daily_return": round(daily_return, 4)},
            ))
    return alerts


def _check_w02_w03_loss_from_buy(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-02/W-03: 取得価格からの下落.

    W-02 (Level 3): -10% 「損切りラインに接近中」
    W-03 (Level 4): -15% 「損切り推奨ラインを突破」
    """
    alerts: list[Alert] = []
    for holding in holdings:
        ticker = holding["ticker"]
        buy_price = float(holding.get("buy_price", 0))
        if buy_price <= 0:
            continue

        df = fetch_price_history(ticker, period="5d")
        if df.empty:
            continue

        current_price = float(df["close"].iloc[-1])
        loss_pct = (current_price - buy_price) / buy_price

        if loss_pct <= _LOSS_LEVEL4:
            pct = round(loss_pct * 100, 1)
            alerts.append(Alert(
                alert_type="W-03",
                level=4,
                ticker=ticker,
                message=f"{ticker}が取得価格から{pct}%下落。損切り推奨ラインを突破",
                action_suggestion="損切りを検討してください。このまま保有を続けるリスクが高い状況です",
                detail={"loss_pct": round(loss_pct, 4), "buy_price": buy_price, "current_price": current_price},
            ))
        elif loss_pct <= _LOSS_LEVEL2:
            pct = round(loss_pct * 100, 1)
            alerts.append(Alert(
                alert_type="W-02",
                level=3,
                ticker=ticker,
                message=f"{ticker}が取得価格から{pct}%下落。損切りラインに接近中",
                action_suggestion="損切りラインを確認し、売却の準備を検討してください",
                detail={"loss_pct": round(loss_pct, 4), "buy_price": buy_price, "current_price": current_price},
            ))
    return alerts


def _check_w04_w05_health(
    health_score: HealthScore,
) -> list[Alert]:
    """W-04/W-05: 健全度スコアに基づく警告.

    W-04 (Level 4): スコア < 40 「危険水準」
    W-05 (Level 2): スコア < 70 「注意水準」
    """
    alerts: list[Alert] = []
    score = health_score.total

    if score < _HEALTH_DANGER:
        alerts.append(Alert(
            alert_type="W-04",
            level=4,
            ticker=None,
            message=f"ポートフォリオの健全度が危険水準です (スコア: {score})",
            action_suggestion="ポートフォリオのリバランスを検討してください。分散を改善する銘柄の追加を推奨します",
            detail={"health_score": score, "breakdown": health_score.breakdown},
        ))
    elif score < _HEALTH_CAUTION:
        alerts.append(Alert(
            alert_type="W-05",
            level=2,
            ticker=None,
            message=f"ポートフォリオの健全度が注意水準です (スコア: {score})",
            action_suggestion="健全度の改善ポイントを確認してください",
            detail={"health_score": score, "breakdown": health_score.breakdown},
        ))
    return alerts


def _check_w06_concentration(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-06: 単一銘柄がポートフォリオの 30% 超.

    Level 3: 「{銘柄}がポートフォリオの{X}%を占めています。集中リスクに注意」
    """
    alerts: list[Alert] = []
    weights = _calc_weights(holdings)
    total = sum(weights.values())
    if total == 0:
        return alerts

    for ticker, value in weights.items():
        ratio = value / total
        if ratio > _SINGLE_STOCK_LIMIT:
            pct = round(ratio * 100, 1)
            alerts.append(Alert(
                alert_type="W-06",
                level=3,
                ticker=ticker,
                message=f"{ticker}がポートフォリオの{pct}%を占めています。集中リスクに注意",
                action_suggestion=f"{ticker}の一部売却や他銘柄への分散を検討してください",
                detail={"ratio": round(ratio, 4)},
            ))
    return alerts


def _check_w07_sector_concentration(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-07: 単一セクターがポートフォリオの 50% 超.

    Level 3: 「{セクター}がポートフォリオの{X}%を占めています」
    """
    alerts: list[Alert] = []
    weights = _calc_weights(holdings)
    total = sum(weights.values())
    if total == 0:
        return alerts

    # セクターごとに集計
    sector_weights: dict[str, float] = {}
    for holding in holdings:
        ticker = holding["ticker"]
        info = fetch_stock_info(ticker)
        sector = info.get("sector", "Unknown") if info else "Unknown"
        value = weights.get(ticker, 0)
        sector_weights[sector] = sector_weights.get(sector, 0) + value

    for sector, value in sector_weights.items():
        ratio = value / total
        if ratio > _SINGLE_SECTOR_LIMIT:
            pct = round(ratio * 100, 1)
            alerts.append(Alert(
                alert_type="W-07",
                level=3,
                ticker=None,
                message=f"{sector}セクターがポートフォリオの{pct}%を占めています",
                action_suggestion=f"異なるセクターの銘柄を追加して分散を改善してください",
                detail={"sector": sector, "ratio": round(ratio, 4)},
            ))
    return alerts


def _check_w08_market_crash() -> list[Alert]:
    """W-08: 市場インデックスが 1 日で -3% 以上下落.

    Level 3: 「市場全体が大幅下落中。保有銘柄への影響を確認してください」
    """
    alerts: list[Alert] = []
    for index_ticker in _MARKET_INDICES:
        df = fetch_price_history(index_ticker, period="5d")
        if df.empty or len(df) < 2:
            continue

        today_close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        if prev_close == 0:
            continue

        daily_return = (today_close - prev_close) / prev_close
        if daily_return <= _INDEX_DROP_THRESHOLD:
            pct = round(daily_return * 100, 1)
            alerts.append(Alert(
                alert_type="W-08",
                level=3,
                ticker=None,
                message=f"市場全体が大幅下落中 ({index_ticker}: {pct}%)。保有銘柄への影響を確認してください",
                action_suggestion="ポートフォリオ全体を確認し、追加の損切りが必要か検討してください",
                detail={"index": index_ticker, "daily_return": round(daily_return, 4)},
            ))
    return alerts


def _check_w09_majority_drop(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-09: 保有銘柄の 50% 以上が同日下落.

    Level 3: 「保有銘柄の過半数が下落中」
    """
    if not holdings:
        return []

    drop_count = 0
    total = 0

    for holding in holdings:
        ticker = holding["ticker"]
        df = fetch_price_history(ticker, period="5d")
        if df.empty or len(df) < 2:
            continue

        total += 1
        today_close = float(df["close"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])
        if prev_close > 0 and today_close < prev_close:
            drop_count += 1

    if total == 0:
        return []

    drop_ratio = drop_count / total
    if drop_ratio >= _MAJORITY_DROP_RATIO:
        pct = round(drop_ratio * 100, 1)
        return [Alert(
            alert_type="W-09",
            level=3,
            ticker=None,
            message=f"保有銘柄の{pct}%が下落中。ポートフォリオ全体を確認してください",
            action_suggestion="市場全体の動向を確認し、ポジション縮小を検討してください",
            detail={"drop_ratio": round(drop_ratio, 4), "drop_count": drop_count, "total": total},
        )]
    return []


def _check_w10_stale_loss(
    holdings: list[dict[str, Any]],
) -> list[Alert]:
    """W-10: 含み損が 30 日以上継続.

    Level 2: 「{銘柄}の含み損が{X}日間継続中。損切り/ナンピンの検討を」
    """
    alerts: list[Alert] = []

    for holding in holdings:
        ticker = holding["ticker"]
        buy_price = float(holding.get("buy_price", 0))
        buy_date = holding.get("buy_date")

        if buy_price <= 0:
            continue

        df = fetch_price_history(ticker, period="3mo")
        if df.empty:
            continue

        current_price = float(df["close"].iloc[-1])
        if current_price >= buy_price:
            continue  # 含み益なのでスキップ

        # 含み損の継続日数を算出
        # 直近の株価データから、取得価格を下回った日数を逆算
        prices = df["close"]
        loss_days = 0
        for i in range(len(prices) - 1, -1, -1):
            if float(prices.iloc[i]) < buy_price:
                loss_days += 1
            else:
                break

        if loss_days >= _LOSS_STALE_DAYS:
            alerts.append(Alert(
                alert_type="W-10",
                level=2,
                ticker=ticker,
                message=f"{ticker}の含み損が{loss_days}日間継続中。損切り/ナンピンの検討を",
                action_suggestion="損切りして資金を成長銘柄に振り向けるか、ナンピンで平均取得価格を下げることを検討してください",
                detail={"loss_days": loss_days, "buy_price": buy_price, "current_price": current_price},
            ))
    return alerts


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _calc_weights(holdings: list[dict[str, Any]]) -> dict[str, float]:
    """保有銘柄の時価ウェイトを算出する.

    Returns:
        {ticker: 時価評価額} の辞書
    """
    weights: dict[str, float] = {}
    for holding in holdings:
        ticker = holding["ticker"]
        shares = float(holding.get("shares", 0))
        df = fetch_price_history(ticker, period="5d")
        if df.empty:
            continue
        current_price = float(df["close"].iloc[-1])
        weights[ticker] = current_price * shares
    return weights


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def generate_alerts(
    holdings: list[dict[str, Any]],
    *,
    portfolio_id: int | None = None,
    health_score: HealthScore | None = None,
) -> list[Alert]:
    """ポートフォリオに対するすべてのアラートを生成する.

    W-01 〜 W-10 の全ルールをチェックし、該当するアラートをまとめて返す。

    Args:
        holdings: 保有銘柄リスト。各要素は
            {"ticker", "shares", "buy_price", "buy_date"(optional)} を含む dict
        portfolio_id: ポートフォリオ ID (アラートに付与)
        health_score: 事前算出済みの HealthScore。None の場合は内部で算出する

    Returns:
        アラートのリスト (レベル降順)
    """
    alerts: list[Alert] = []

    # 健全度スコアを算出 (W-04, W-05 用)
    if health_score is None:
        health_score = calculate_health_score(holdings)

    # W-01: 日次急落
    alerts.extend(_check_w01_daily_drop(holdings))

    # W-02, W-03: 取得価格比の下落
    alerts.extend(_check_w02_w03_loss_from_buy(holdings))

    # W-04, W-05: 健全度スコア
    alerts.extend(_check_w04_w05_health(health_score))

    # W-06: 単一銘柄集中
    alerts.extend(_check_w06_concentration(holdings))

    # W-07: セクター集中
    alerts.extend(_check_w07_sector_concentration(holdings))

    # W-08: 市場インデックス急落
    alerts.extend(_check_w08_market_crash())

    # W-09: 過半数下落
    alerts.extend(_check_w09_majority_drop(holdings))

    # W-10: 含み損放置
    alerts.extend(_check_w10_stale_loss(holdings))

    # portfolio_id を付与
    for alert in alerts:
        alert.portfolio_id = portfolio_id

    # レベル降順 (高いほど重要) でソート
    alerts.sort(key=lambda a: a.level, reverse=True)

    return alerts
