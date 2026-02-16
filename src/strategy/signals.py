"""モメンタムシグナル検知.

ゴールデンクロス、出来高急増、RSI 反転の3種類のシグナルを検知する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from src.data.fetcher import fetch_price_history
from src.data.indicators import calculate_ma, calculate_rsi, calculate_macd


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    """検知されたシグナルを格納するデータクラス."""

    ticker: str
    signal_type: str  # "golden_cross" | "volume_spike" | "rsi_reversal"
    priority: str     # "high" | "medium" | "low"
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# シグナル有効期限 (デフォルト 7 日)
# ---------------------------------------------------------------------------

_DEFAULT_EXPIRY_DAYS = 7


# ---------------------------------------------------------------------------
# 個別シグナル検知
# ---------------------------------------------------------------------------

def detect_golden_cross(
    ticker: str,
    df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20,
) -> Signal | None:
    """ゴールデンクロスを検知する.

    短期移動平均 (デフォルト 5 日) が長期移動平均 (デフォルト 20 日) を
    下から上に抜けた場合にシグナルを発行する。

    Args:
        ticker: 銘柄コード
        df: 株価 DataFrame (date, open, high, low, close, volume)
        short_window: 短期 MA 期間
        long_window: 長期 MA 期間

    Returns:
        Signal またはシグナル未検知時は None
    """
    if df.empty or len(df) < long_window + 2:
        return None

    ma_short = calculate_ma(df, window=short_window)
    ma_long = calculate_ma(df, window=long_window)

    if ma_short.empty or ma_long.empty or len(ma_short) < 2 or len(ma_long) < 2:
        return None

    # 直近 2 日分で判定: 前日は short <= long かつ 当日は short > long
    prev_short = float(ma_short.iloc[-2])
    prev_long = float(ma_long.iloc[-2])
    curr_short = float(ma_short.iloc[-1])
    curr_long = float(ma_long.iloc[-1])

    if prev_short <= prev_long and curr_short > curr_long:
        now = datetime.now()
        return Signal(
            ticker=ticker,
            signal_type="golden_cross",
            priority="high",
            message=f"{ticker}: ゴールデンクロス発生 (MA{short_window} > MA{long_window})",
            detail={
                "short_window": short_window,
                "long_window": long_window,
                "ma_short": round(curr_short, 2),
                "ma_long": round(curr_long, 2),
            },
            expires_at=now + timedelta(days=_DEFAULT_EXPIRY_DAYS),
            created_at=now,
        )

    return None


def detect_volume_spike(
    ticker: str,
    df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20,
    spike_ratio: float = 2.0,
) -> Signal | None:
    """出来高急増を検知する.

    直近 *short_window* 日の平均出来高が *long_window* 日の平均出来高の
    *spike_ratio* 倍以上の場合にシグナルを発行する。

    Args:
        ticker: 銘柄コード
        df: 株価 DataFrame
        short_window: 短期出来高平均期間
        long_window: 長期出来高平均期間
        spike_ratio: 出来高倍率の閾値 (デフォルト 2.0 倍)

    Returns:
        Signal またはシグナル未検知時は None
    """
    if df.empty or len(df) < long_window:
        return None

    vol = df["volume"].astype(float)
    avg_short = float(vol.iloc[-short_window:].mean())
    avg_long = float(vol.iloc[-long_window:].mean())

    if avg_long <= 0:
        return None

    ratio = avg_short / avg_long
    if ratio >= spike_ratio:
        now = datetime.now()
        return Signal(
            ticker=ticker,
            signal_type="volume_spike",
            priority="high",
            message=f"{ticker}: 出来高急増 ({ratio:.1f}倍)",
            detail={
                "avg_volume_short": round(avg_short),
                "avg_volume_long": round(avg_long),
                "ratio": round(ratio, 2),
            },
            expires_at=now + timedelta(days=_DEFAULT_EXPIRY_DAYS),
            created_at=now,
        )

    return None


def detect_rsi_reversal(
    ticker: str,
    df: pd.DataFrame,
    period: int = 14,
    oversold: float = 30.0,
    lookback: int = 5,
) -> Signal | None:
    """RSI 反転 (売られ過ぎからの回復) を検知する.

    直近 *lookback* 日以内に RSI が *oversold* 以下に達した後、
    最新の RSI がそれを上回っている場合にシグナルを発行する。

    Args:
        ticker: 銘柄コード
        df: 株価 DataFrame
        period: RSI 算出期間
        oversold: 売られ過ぎの閾値 (デフォルト 30)
        lookback: 直近何日以内に売られ過ぎがあったかを確認する日数

    Returns:
        Signal またはシグナル未検知時は None
    """
    if df.empty or len(df) < period + lookback:
        return None

    rsi_series = calculate_rsi(df, period=period)
    if rsi_series.empty or len(rsi_series) < lookback + 1:
        return None

    recent_rsi = rsi_series.iloc[-(lookback + 1):]
    current_rsi = float(recent_rsi.iloc[-1])
    past_rsi = recent_rsi.iloc[:-1]

    # 直近期間内に RSI が oversold 以下に達し、現在は oversold を上回っている
    was_oversold = bool((past_rsi <= oversold).any())
    min_rsi = float(past_rsi.min())

    if was_oversold and current_rsi > oversold:
        now = datetime.now()
        return Signal(
            ticker=ticker,
            signal_type="rsi_reversal",
            priority="medium",
            message=f"{ticker}: RSI 反転 ({min_rsi:.1f} → {current_rsi:.1f})",
            detail={
                "current_rsi": round(current_rsi, 2),
                "min_rsi_in_period": round(min_rsi, 2),
                "period": period,
                "oversold_threshold": oversold,
            },
            expires_at=now + timedelta(days=_DEFAULT_EXPIRY_DAYS),
            created_at=now,
        )

    return None


# ---------------------------------------------------------------------------
# 公開 API
# ---------------------------------------------------------------------------

def detect_signals(
    tickers: list[str],
    *,
    period: str = "6mo",
) -> list[Signal]:
    """複数銘柄に対してすべてのシグナル検知を実行する.

    ゴールデンクロス、出来高急増、RSI 反転の3種類を検査する。

    Args:
        tickers: 対象の銘柄コードリスト
        period: 株価取得期間 (デフォルト "6mo")

    Returns:
        検知されたシグナルのリスト (優先度順)
    """
    signals: list[Signal] = []

    for ticker in tickers:
        df = fetch_price_history(ticker, period=period)
        if df.empty:
            continue

        # 各シグナル検知を実行
        gc = detect_golden_cross(ticker, df)
        if gc is not None:
            signals.append(gc)

        vs = detect_volume_spike(ticker, df)
        if vs is not None:
            signals.append(vs)

        rr = detect_rsi_reversal(ticker, df)
        if rr is not None:
            signals.append(rr)

    # 優先度順にソート (high > medium > low)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    signals.sort(key=lambda s: priority_order.get(s.priority, 99))

    return signals
