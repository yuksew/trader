"""リスク指標算出モジュール.

ボラティリティ、最大ドローダウン (MDD)、シャープレシオ、相関係数、
ベータ値、集中度指数 (HHI)、バリューアットリスク (VaR) を算出する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.data.fetcher import fetch_price_history


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class RiskMetrics:
    """ポートフォリオのリスク指標を格納するデータクラス."""

    portfolio_volatility: float
    max_drawdown: float
    sharpe_ratio: float
    hhi: float
    var_95: float
    var_99: float
    avg_correlation: float
    betas: dict[str, float]
    individual_volatilities: dict[str, float]


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

# 無リスク金利 (年率, 日本国債10年利回りの近似)
_RISK_FREE_RATE = 0.005

# 年間営業日数
_TRADING_DAYS = 252

# 市場インデックスのティッカー
_MARKET_INDEX_JP = "^N225"
_MARKET_INDEX_US = "^GSPC"


# ---------------------------------------------------------------------------
# 個別指標算出
# ---------------------------------------------------------------------------

def calculate_volatility(
    returns: pd.Series,
    annualize: bool = True,
) -> float:
    """ボラティリティ (標準偏差) を算出する.

    Args:
        returns: 日次リターン系列
        annualize: True の場合は年率換算する

    Returns:
        ボラティリティ (年率化済みなら年率 %)
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    vol = float(returns.std())
    if annualize:
        vol *= np.sqrt(_TRADING_DAYS)
    return vol


def calculate_max_drawdown(prices: pd.Series) -> float:
    """最大ドローダウン (MDD) を算出する.

    ピークからの最大下落率を算出する。

    Args:
        prices: 株価時系列 (終値)

    Returns:
        最大ドローダウン (正の値, 例: 0.15 は 15% の下落)
    """
    if prices.empty or len(prices) < 2:
        return 0.0

    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax
    mdd = float(drawdown.min())
    return abs(mdd)


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = _RISK_FREE_RATE,
) -> float:
    """シャープレシオを算出する.

    (年率リターン - 無リスク金利) / 年率ボラティリティ

    Args:
        returns: 日次リターン系列
        risk_free_rate: 年率無リスク金利 (デフォルト 0.5%)

    Returns:
        シャープレシオ
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    annual_return = float(returns.mean()) * _TRADING_DAYS
    annual_vol = calculate_volatility(returns, annualize=True)

    if annual_vol == 0.0:
        return 0.0

    return (annual_return - risk_free_rate) / annual_vol


def calculate_correlation_matrix(
    returns_dict: dict[str, pd.Series],
) -> pd.DataFrame:
    """銘柄間の相関係数行列を算出する.

    Args:
        returns_dict: {ticker: 日次リターン系列} の辞書

    Returns:
        相関係数行列 DataFrame
    """
    if len(returns_dict) < 2:
        return pd.DataFrame()

    df = pd.DataFrame(returns_dict)
    return df.corr()


def calculate_avg_correlation(corr_matrix: pd.DataFrame) -> float:
    """相関行列から対角成分を除いた平均相関係数を算出する.

    Args:
        corr_matrix: 相関係数行列

    Returns:
        平均相関係数
    """
    if corr_matrix.empty or len(corr_matrix) < 2:
        return 0.0

    n = len(corr_matrix)
    # 対角成分 (=1.0) を除いて平均を取る
    mask = ~np.eye(n, dtype=bool)
    values = corr_matrix.values[mask]
    return float(np.mean(values))


def calculate_beta(
    stock_returns: pd.Series,
    market_returns: pd.Series,
) -> float:
    """個別銘柄のベータ値を算出する.

    β = Cov(Ri, Rm) / Var(Rm)

    Args:
        stock_returns: 個別銘柄の日次リターン
        market_returns: 市場インデックスの日次リターン

    Returns:
        ベータ値
    """
    if stock_returns.empty or market_returns.empty:
        return 1.0

    # 共通の日付で整列
    aligned = pd.DataFrame({
        "stock": stock_returns,
        "market": market_returns,
    }).dropna()

    if len(aligned) < 10:
        return 1.0

    cov = float(aligned["stock"].cov(aligned["market"]))
    var_market = float(aligned["market"].var())

    if var_market == 0.0:
        return 1.0

    return cov / var_market


def calculate_hhi(weights: dict[str, float]) -> float:
    """ハーフィンダール・ハーシュマン指数 (HHI) を算出する.

    各銘柄のウェイトの 2 乗和。完全均等分散で 1/N、1 銘柄集中で 1.0。

    Args:
        weights: {ticker: ポートフォリオ内の比率} (合計 1.0)

    Returns:
        HHI (0.0 〜 1.0)
    """
    if not weights:
        return 0.0

    total = sum(weights.values())
    if total == 0:
        return 0.0

    return sum((w / total) ** 2 for w in weights.values())


def calculate_var(
    returns: pd.Series,
    confidence: float = 0.95,
    portfolio_value: float = 1.0,
) -> float:
    """ヒストリカル法で VaR (バリューアットリスク) を算出する.

    Args:
        returns: ポートフォリオ全体の日次リターン系列
        confidence: 信頼水準 (デフォルト 95%)
        portfolio_value: ポートフォリオ評価額 (デフォルト 1.0 = 比率で返却)

    Returns:
        VaR (正の値で表現、例: 0.03 は最大 3% の日次損失を想定)
    """
    if returns.empty or len(returns) < 10:
        return 0.0

    percentile = (1.0 - confidence) * 100.0
    var_value = float(np.percentile(returns.dropna(), percentile))
    return abs(var_value) * portfolio_value


# ---------------------------------------------------------------------------
# ポートフォリオリターン算出
# ---------------------------------------------------------------------------

def _calc_portfolio_returns(
    holdings: list[dict[str, Any]],
    period: str = "1y",
) -> tuple[pd.Series, dict[str, pd.Series]]:
    """ポートフォリオ全体と個別銘柄の日次リターンを算出する.

    Args:
        holdings: 保有銘柄リスト。各要素は {"ticker", "shares", "buy_price"} を含む dict
        period: 株価取得期間

    Returns:
        (portfolio_returns, individual_returns) のタプル
    """
    individual_returns: dict[str, pd.Series] = {}
    weights: dict[str, float] = {}

    # 各銘柄の評価額を算出してウェイトを求める
    for holding in holdings:
        ticker = holding["ticker"]
        df = fetch_price_history(ticker, period=period)
        if df.empty or len(df) < 2:
            continue

        returns = df["close"].pct_change().dropna()
        individual_returns[ticker] = returns

        current_price = float(df["close"].iloc[-1])
        shares = float(holding.get("shares", 0))
        weights[ticker] = current_price * shares

    total_value = sum(weights.values())
    if total_value == 0:
        return pd.Series(dtype=float), individual_returns

    # ウェイトを正規化
    normalized_weights = {t: v / total_value for t, v in weights.items()}

    # 加重平均のポートフォリオリターン
    aligned = pd.DataFrame(individual_returns).dropna()
    if aligned.empty:
        return pd.Series(dtype=float), individual_returns

    portfolio_returns = pd.Series(0.0, index=aligned.index)
    for ticker, w in normalized_weights.items():
        if ticker in aligned.columns:
            portfolio_returns += aligned[ticker] * w

    return portfolio_returns, individual_returns


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def calculate_risk_metrics(
    holdings: list[dict[str, Any]],
    *,
    period: str = "1y",
    market_ticker: str | None = None,
) -> RiskMetrics:
    """ポートフォリオのリスク指標を一括算出する.

    Args:
        holdings: 保有銘柄リスト。各要素は {"ticker", "shares", "buy_price"} を含む dict
        period: 株価取得期間 (デフォルト "1y")
        market_ticker: 市場インデックスのティッカー。
            None の場合、ティッカーの末尾が ".T" なら日経 225、それ以外は S&P500

    Returns:
        RiskMetrics データクラス
    """
    portfolio_returns, individual_returns = _calc_portfolio_returns(holdings, period)

    # ウェイト算出
    weights: dict[str, float] = {}
    for holding in holdings:
        ticker = holding["ticker"]
        df = fetch_price_history(ticker, period=period)
        if df.empty:
            continue
        current_price = float(df["close"].iloc[-1])
        shares = float(holding.get("shares", 0))
        weights[ticker] = current_price * shares

    total_value = sum(weights.values())
    if total_value > 0:
        norm_weights = {t: v / total_value for t, v in weights.items()}
    else:
        norm_weights = {}

    # ボラティリティ
    portfolio_vol = calculate_volatility(portfolio_returns)

    # MDD
    if not portfolio_returns.empty:
        cumulative = (1 + portfolio_returns).cumprod()
        mdd = calculate_max_drawdown(cumulative)
    else:
        mdd = 0.0

    # シャープレシオ
    sharpe = calculate_sharpe_ratio(portfolio_returns)

    # HHI
    hhi = calculate_hhi(norm_weights)

    # VaR
    var_95 = calculate_var(portfolio_returns, confidence=0.95)
    var_99 = calculate_var(portfolio_returns, confidence=0.99)

    # 相関行列
    corr_matrix = calculate_correlation_matrix(individual_returns)
    avg_corr = calculate_avg_correlation(corr_matrix)

    # β値 (市場インデックスとの比較)
    if market_ticker is None:
        # 最初の銘柄で判定
        first_ticker = holdings[0]["ticker"] if holdings else ""
        market_ticker = (
            _MARKET_INDEX_JP if first_ticker.endswith(".T") else _MARKET_INDEX_US
        )

    market_df = fetch_price_history(market_ticker, period=period)
    if not market_df.empty and len(market_df) >= 2:
        market_returns = market_df["close"].pct_change().dropna()
    else:
        market_returns = pd.Series(dtype=float)

    betas: dict[str, float] = {}
    for ticker, ret in individual_returns.items():
        betas[ticker] = round(calculate_beta(ret, market_returns), 3)

    # 個別ボラティリティ
    individual_vols: dict[str, float] = {}
    for ticker, ret in individual_returns.items():
        individual_vols[ticker] = round(calculate_volatility(ret), 4)

    return RiskMetrics(
        portfolio_volatility=round(portfolio_vol, 4),
        max_drawdown=round(mdd, 4),
        sharpe_ratio=round(sharpe, 4),
        hhi=round(hhi, 4),
        var_95=round(var_95, 4),
        var_99=round(var_99, 4),
        avg_correlation=round(avg_corr, 4),
        betas=betas,
        individual_volatilities=individual_vols,
    )
