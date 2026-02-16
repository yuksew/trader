"""APScheduler integration for daily/weekly batch jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> None:
    """スケジューラを起動し、日次/週次ジョブを登録する。"""
    scheduler = get_scheduler()

    # 日次チェック: 平日 18:00 JST (= 09:00 UTC)
    scheduler.add_job(
        run_daily_check,
        CronTrigger(day_of_week="mon-fri", hour=9, minute=0),
        id="daily_check",
        replace_existing=True,
    )

    # 週次レポート: 毎週土曜 10:00 JST (= 01:00 UTC)
    scheduler.add_job(
        run_weekly_report,
        CronTrigger(day_of_week="sat", hour=1, minute=0),
        id="weekly_report",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with daily_check and weekly_report jobs")


def stop_scheduler() -> None:
    """スケジューラを停止する。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None


async def run_daily_check() -> str:
    """日次チェックバッチを実行する。

    1. 株価データ取得・キャッシュ更新
    2. スクリーニング実行
    3. シグナル検知
    4. リスク指標算出
    5. アラート生成
    """
    logger.info("Daily check started at %s", datetime.utcnow().isoformat())

    from src.api.database import get_db

    db = await get_db()

    # ポートフォリオ一覧を取得
    portfolios = await db.execute_fetchall("SELECT id FROM portfolios")

    for pf in portfolios:
        portfolio_id = pf["id"]
        try:
            await _run_portfolio_daily(portfolio_id)
        except Exception:
            logger.exception("Daily check failed for portfolio %s", portfolio_id)

    # スクリーニング実行 (全体)
    try:
        await _run_screening()
    except Exception:
        logger.exception("Screening failed")

    # シグナル検知
    try:
        await _run_signal_detection()
    except Exception:
        logger.exception("Signal detection failed")

    logger.info("Daily check completed")
    return "Daily check completed"


async def _run_portfolio_daily(portfolio_id: int) -> None:
    """個別ポートフォリオの日次処理。"""
    from src.api.database import get_db

    db = await get_db()
    holdings = await db.execute_fetchall(
        "SELECT ticker FROM holdings WHERE portfolio_id = ?",
        (portfolio_id,),
    )
    tickers = [h["ticker"] for h in holdings]
    if not tickers:
        return

    # 株価取得・キャッシュ更新
    try:
        from src.data.fetcher import StockFetcher

        fetcher = StockFetcher()
        for ticker in tickers:
            await asyncio.to_thread(fetcher.fetch_recent, ticker)
    except ImportError:
        logger.warning("StockFetcher not available yet; skipping price fetch")

    # リスク指標算出
    try:
        from src.strategy.risk import calculate_risk_metrics
        from src.strategy.health import calculate_health_score

        holdings_data = [
            {"ticker": h["ticker"], "shares": h["shares"] or 0, "buy_price": h["buy_price"] or 0}
            for h in (await db.execute_fetchall(
                "SELECT ticker, shares, buy_price FROM holdings WHERE portfolio_id = ?",
                (portfolio_id,),
            ))
        ]
        if holdings_data:
            risk_result = await asyncio.to_thread(calculate_risk_metrics, holdings_data)
            health_result = await asyncio.to_thread(calculate_health_score, holdings_data)
            today = datetime.utcnow().date().isoformat()
            await db.execute(
                "INSERT OR REPLACE INTO risk_metrics "
                "(portfolio_id, date, health_score, max_drawdown, portfolio_volatility, "
                "sharpe_ratio, hhi, var_95) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    portfolio_id,
                    today,
                    health_result.total,
                    risk_result.max_drawdown,
                    risk_result.portfolio_volatility,
                    risk_result.sharpe_ratio,
                    risk_result.hhi,
                    risk_result.var_95,
                ),
            )
            await db.commit()
    except ImportError:
        logger.warning("Risk/Health modules not available yet; skipping risk calc")
    except Exception:
        logger.exception("Risk calculation failed for portfolio %s", portfolio_id)

    # アラート生成
    try:
        from src.strategy.alerts import generate_alerts

        holdings_data = [
            dict(h) for h in (await db.execute_fetchall(
                "SELECT ticker, shares, buy_price, buy_date FROM holdings WHERE portfolio_id = ?",
                (portfolio_id,),
            ))
        ]
        if holdings_data:
            alerts = await asyncio.to_thread(generate_alerts, holdings_data)
            now = datetime.utcnow().isoformat()
            for a in (alerts or []):
                await db.execute(
                    "INSERT INTO alerts "
                    "(portfolio_id, ticker, alert_type, level, message, action_suggestion, "
                    "is_read, is_resolved, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)",
                    (
                        portfolio_id,
                        a.ticker,
                        a.alert_type,
                        a.level,
                        a.message,
                        a.action_suggestion,
                        now,
                    ),
                )
            await db.commit()
    except ImportError:
        logger.warning("Alert module not available yet; skipping alert generation")
    except Exception:
        logger.exception("Alert generation failed for portfolio %s", portfolio_id)


async def _run_screening() -> None:
    """割安銘柄スクリーニングを実行する。"""
    try:
        from src.strategy.screener import screen_value_stocks

        # デフォルトの日経225主要銘柄でスクリーニング
        default_tickers = [
            "7203.T", "6758.T", "9984.T", "8306.T", "6861.T",
            "9433.T", "6501.T", "7267.T", "4503.T", "6902.T",
        ]
        screening_results = await asyncio.to_thread(screen_value_stocks, default_tickers)
        results = [
            {
                "ticker": r.ticker, "name": r.name, "sector": r.sector,
                "score": r.score, "per": r.per,
                "pbr": r.pbr, "dividend_yield": r.dividend_yield,
                "momentum_score": r.momentum_score, "value_score": r.value_score,
            }
            for r in (screening_results or [])
        ]
    except ImportError:
        logger.warning("Screener not available yet; skipping")
        return
    except Exception:
        logger.exception("Screening failed")
        return

    if not results:
        return

    from src.api.database import get_db

    db = await get_db()
    today = datetime.utcnow().date().isoformat()
    for r in results:
        await db.execute(
            "INSERT INTO screening_results "
            "(date, ticker, name, sector, score, per, pbr, dividend_yield, momentum_score, value_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                today,
                r["ticker"],
                r.get("name", ""),
                r.get("sector", ""),
                r.get("score", 0),
                r.get("per"),
                r.get("pbr"),
                r.get("dividend_yield"),
                r.get("momentum_score"),
                r.get("value_score"),
            ),
        )
    await db.commit()


async def _run_signal_detection() -> None:
    """シグナル検知を実行する。"""
    try:
        from src.strategy.signals import detect_signals

        # ウォッチリスト + 保有銘柄のシグナルを検知
        from src.api.database import get_db as _get_db
        _db = await _get_db()
        watchlist_rows = await _db.execute_fetchall("SELECT ticker FROM watchlist")
        holdings_rows = await _db.execute_fetchall("SELECT DISTINCT ticker FROM holdings")
        all_tickers = list({r["ticker"] for r in watchlist_rows} | {r["ticker"] for r in holdings_rows})
        if not all_tickers:
            return
        detected = await asyncio.to_thread(detect_signals, all_tickers)
        signals = [
            {
                "ticker": s.ticker, "signal_type": s.signal_type,
                "priority": s.priority, "message": s.message,
                "detail": str(s.detail) if s.detail else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in (detected or [])
        ]
    except ImportError:
        logger.warning("Signal module not available yet; skipping")
        return
    except Exception:
        logger.exception("Signal detection failed")
        return

    if not signals:
        return

    from src.api.database import get_db

    db = await get_db()
    now = datetime.utcnow().isoformat()
    for s in signals:
        await db.execute(
            "INSERT INTO signals "
            "(ticker, signal_type, priority, message, detail, is_valid, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (
                s["ticker"],
                s["signal_type"],
                s.get("priority", "medium"),
                s["message"],
                s.get("detail"),
                s.get("expires_at"),
                now,
            ),
        )
    await db.commit()


async def run_weekly_report() -> str:
    """週次レポートバッチを実行する。"""
    logger.info("Weekly report started at %s", datetime.utcnow().isoformat())

    # 期限切れシグナルを無効化
    from src.api.database import get_db

    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE signals SET is_valid = 0 WHERE is_valid = 1 AND expires_at < ?",
        (now,),
    )
    await db.commit()

    logger.info("Weekly report completed")
    return "Weekly report completed"
