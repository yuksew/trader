"""割安銘柄スクリーニング + スコアリング.

セクション6のスコアリングロジックに基づき、バリュー(40%) + モメンタム(30%) +
成長性(20%) + 安全性(10%) の統合スコアで銘柄をランク付けする。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.data.fetcher import fetch_stock_info, fetch_price_history
from src.data.indicators import calculate_rsi, calculate_macd, calculate_ma


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class ScreeningResult:
    """スクリーニング結果を格納するデータクラス."""

    ticker: str
    name: str
    sector: str
    score: float
    per: float | None
    pbr: float | None
    dividend_yield: float | None
    momentum_score: float
    value_score: float
    growth_score: float
    safety_score: float
    detail: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# スコアリング定数
# ---------------------------------------------------------------------------

# バリュースコアの基準値
_PER_UPPER = 25.0  # PER がこれ以上なら 0 点
_PER_LOWER = 5.0   # PER がこれ以下なら満点
_PBR_UPPER = 3.0
_PBR_LOWER = 0.5
_DIV_YIELD_LOWER = 0.0   # 配当利回り 0% で 0 点
_DIV_YIELD_UPPER = 5.0   # 5% 以上で満点

# モメンタムスコアの基準値
_RSI_OVERSOLD = 30.0
_RSI_NEUTRAL = 50.0

# 成長性スコアの基準値
_GROWTH_UPPER = 30.0  # 30% 以上で満点
_GROWTH_LOWER = 0.0

# 安全性スコアの基準値
_EQUITY_RATIO_LOWER = 20.0
_EQUITY_RATIO_UPPER = 60.0
_PAYOUT_RATIO_UPPER = 80.0  # 配当性向 80% 超は減点


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _normalize(value: float, low: float, high: float) -> float:
    """*value* を [0, 100] に線形正規化する.

    *low* 以下は 0、*high* 以上は 100 にクリップする。
    """
    if high == low:
        return 50.0
    score = (value - low) / (high - low) * 100.0
    return float(np.clip(score, 0.0, 100.0))


def _normalize_inverse(value: float, low: float, high: float) -> float:
    """低いほど高スコアになる逆正規化.

    *low* 以下で 100、*high* 以上で 0。
    """
    return 100.0 - _normalize(value, low, high)


# ---------------------------------------------------------------------------
# 個別スコア算出
# ---------------------------------------------------------------------------

def _calc_value_score(info: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """バリュースコア (0-100) を算出する.

    PER (業種平均比)、PBR、配当利回りの3指標から算出。
    """
    per = info.get("trailingPE") or info.get("forwardPE")
    pbr = info.get("priceToBook")
    div_yield = info.get("dividendYield")  # 0.03 = 3%

    scores: list[float] = []
    detail: dict[str, Any] = {}

    if per is not None and per > 0:
        s = _normalize_inverse(per, _PER_LOWER, _PER_UPPER)
        scores.append(s)
        detail["per"] = per
        detail["per_score"] = round(s, 1)

    if pbr is not None and pbr > 0:
        s = _normalize_inverse(pbr, _PBR_LOWER, _PBR_UPPER)
        scores.append(s)
        detail["pbr"] = pbr
        detail["pbr_score"] = round(s, 1)

    if div_yield is not None:
        pct = div_yield * 100.0  # % 表記に変換
        s = _normalize(pct, _DIV_YIELD_LOWER, _DIV_YIELD_UPPER)
        scores.append(s)
        detail["dividend_yield"] = round(pct, 2)
        detail["dividend_yield_score"] = round(s, 1)

    value = float(np.mean(scores)) if scores else 0.0
    return value, detail


def _calc_momentum_score(df: pd.DataFrame) -> tuple[float, dict[str, Any]]:
    """モメンタムスコア (0-100) を算出する.

    RSI、MACD、移動平均乖離率の3指標から算出。
    """
    scores: list[float] = []
    detail: dict[str, Any] = {}

    if df.empty or len(df) < 20:
        return 0.0, detail

    # RSI
    rsi_series = calculate_rsi(df, period=14)
    if not rsi_series.empty:
        rsi_val = float(rsi_series.iloc[-1])
        # RSI 30 以下: 反転期待で高スコア、50 付近: 中立、70 超: 過熱で減点
        if rsi_val <= _RSI_OVERSOLD:
            rsi_score = 100.0
        elif rsi_val <= _RSI_NEUTRAL:
            rsi_score = _normalize_inverse(rsi_val, _RSI_OVERSOLD, _RSI_NEUTRAL)
            rsi_score = 50.0 + rsi_score * 0.5  # 50-100 にマッピング
        else:
            rsi_score = _normalize_inverse(rsi_val, _RSI_NEUTRAL, 100.0)
            rsi_score = rsi_score * 0.5  # 0-50 にマッピング
        scores.append(rsi_score)
        detail["rsi"] = round(rsi_val, 2)
        detail["rsi_score"] = round(rsi_score, 1)

    # MACD
    macd_result = calculate_macd(df)
    if macd_result is not None and not macd_result.empty:
        macd_line = macd_result.get("macd")
        signal_line = macd_result.get("signal")
        if macd_line is not None and signal_line is not None:
            macd_val = float(macd_line.iloc[-1])
            signal_val = float(signal_line.iloc[-1])
            macd_diff = macd_val - signal_val
            # MACD がシグナルを上回っていれば高スコア
            macd_score = _normalize(macd_diff, -2.0, 2.0)
            scores.append(macd_score)
            detail["macd_diff"] = round(macd_diff, 4)
            detail["macd_score"] = round(macd_score, 1)

    # 移動平均乖離率 (20 日)
    ma20 = calculate_ma(df, window=20)
    if not ma20.empty and len(ma20) > 0:
        current_price = float(df["close"].iloc[-1])
        ma20_val = float(ma20.iloc[-1])
        if ma20_val > 0:
            deviation = (current_price - ma20_val) / ma20_val * 100.0
            # -10% 以下で高スコア (反発期待)、+10% 以上で低スコア (過熱)
            dev_score = _normalize_inverse(deviation, -10.0, 10.0)
            scores.append(dev_score)
            detail["ma_deviation_pct"] = round(deviation, 2)
            detail["ma_deviation_score"] = round(dev_score, 1)

    momentum = float(np.mean(scores)) if scores else 0.0
    return momentum, detail


def _calc_growth_score(info: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """成長性スコア (0-100) を算出する.

    売上成長率、EPS 成長率から算出。
    """
    scores: list[float] = []
    detail: dict[str, Any] = {}

    revenue_growth = info.get("revenueGrowth")  # 0.15 = 15%
    if revenue_growth is not None:
        pct = revenue_growth * 100.0
        s = _normalize(pct, _GROWTH_LOWER, _GROWTH_UPPER)
        scores.append(s)
        detail["revenue_growth_pct"] = round(pct, 2)
        detail["revenue_growth_score"] = round(s, 1)

    earnings_growth = info.get("earningsGrowth")  # 0.20 = 20%
    if earnings_growth is not None:
        pct = earnings_growth * 100.0
        s = _normalize(pct, _GROWTH_LOWER, _GROWTH_UPPER)
        scores.append(s)
        detail["earnings_growth_pct"] = round(pct, 2)
        detail["earnings_growth_score"] = round(s, 1)

    growth = float(np.mean(scores)) if scores else 0.0
    return growth, detail


def _calc_safety_score(info: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """安全性スコア (0-100) を算出する.

    自己資本比率、配当性向から算出。
    """
    scores: list[float] = []
    detail: dict[str, Any] = {}

    # 自己資本比率 (debtToEquity の逆数から推定)
    debt_to_equity = info.get("debtToEquity")  # 例: 50.0 = 50%
    if debt_to_equity is not None and debt_to_equity >= 0:
        # debtToEquity → 自己資本比率の概算: 1 / (1 + D/E)
        equity_ratio = 1.0 / (1.0 + debt_to_equity / 100.0) * 100.0
        s = _normalize(equity_ratio, _EQUITY_RATIO_LOWER, _EQUITY_RATIO_UPPER)
        scores.append(s)
        detail["equity_ratio_pct"] = round(equity_ratio, 2)
        detail["equity_ratio_score"] = round(s, 1)

    payout_ratio = info.get("payoutRatio")  # 0.40 = 40%
    if payout_ratio is not None:
        pct = payout_ratio * 100.0
        # 配当性向は低すぎても高すぎてもよくない。20-60% が理想的。
        if pct <= 60.0:
            s = _normalize(pct, 0.0, 60.0)
        else:
            s = _normalize_inverse(pct, 60.0, _PAYOUT_RATIO_UPPER)
        scores.append(s)
        detail["payout_ratio_pct"] = round(pct, 2)
        detail["payout_ratio_score"] = round(s, 1)

    safety = float(np.mean(scores)) if scores else 50.0
    return safety, detail


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def score_stock(ticker: str) -> ScreeningResult | None:
    """単一銘柄の統合スコアを算出する.

    統合スコア = バリュー(40%) + モメンタム(30%) + 成長性(20%) + 安全性(10%)

    Args:
        ticker: 銘柄コード (例: "7203.T")

    Returns:
        ScreeningResult、またはデータ取得失敗時は None
    """
    info = fetch_stock_info(ticker)
    if info is None:
        return None

    df = fetch_price_history(ticker, period="6mo")

    value_score, value_detail = _calc_value_score(info)
    momentum_score, momentum_detail = _calc_momentum_score(df)
    growth_score, growth_detail = _calc_growth_score(info)
    safety_score, safety_detail = _calc_safety_score(info)

    total_score = (
        value_score * 0.40
        + momentum_score * 0.30
        + growth_score * 0.20
        + safety_score * 0.10
    )

    return ScreeningResult(
        ticker=ticker,
        name=info.get("shortName", ticker),
        sector=info.get("sector", "Unknown"),
        score=round(total_score, 2),
        per=info.get("trailingPE") or info.get("forwardPE"),
        pbr=info.get("priceToBook"),
        dividend_yield=(
            round(info["dividendYield"] * 100.0, 2)
            if info.get("dividendYield") is not None
            else None
        ),
        momentum_score=round(momentum_score, 2),
        value_score=round(value_score, 2),
        growth_score=round(growth_score, 2),
        safety_score=round(safety_score, 2),
        detail={
            "value": value_detail,
            "momentum": momentum_detail,
            "growth": growth_detail,
            "safety": safety_detail,
        },
    )


def screen_value_stocks(
    tickers: list[str],
    *,
    top_n: int = 20,
    min_per: float = 0.0,
    max_per: float | None = None,
    min_dividend_yield: float | None = None,
) -> list[ScreeningResult]:
    """複数銘柄をスクリーニングし、スコア上位を返す.

    Args:
        tickers: スクリーニング対象の銘柄コードリスト
        top_n: 返却する上位銘柄数 (デフォルト 20)
        min_per: 最小 PER (赤字企業除外用、デフォルト 0)
        max_per: 最大 PER (割安フィルター用)
        min_dividend_yield: 最低配当利回り (%, 例: 3.0)

    Returns:
        スコア降順にソートされた ScreeningResult のリスト
    """
    results: list[ScreeningResult] = []

    for ticker in tickers:
        result = score_stock(ticker)
        if result is None:
            continue

        # フィルタリング
        if result.per is not None:
            if result.per <= min_per:
                continue
            if max_per is not None and result.per > max_per:
                continue

        if min_dividend_yield is not None and result.dividend_yield is not None:
            if result.dividend_yield < min_dividend_yield:
                continue

        results.append(result)

    # スコア降順でソートし上位 N 件を返却
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
