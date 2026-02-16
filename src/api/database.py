"""Database initialization and connection management."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "traders.db"

_SCHEMA_SQL = """
-- portfolios
CREATE TABLE IF NOT EXISTS portfolios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- holdings (portfolio positions)
CREATE TABLE IF NOT EXISTS holdings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id  INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker        TEXT    NOT NULL,
    name          TEXT    NOT NULL DEFAULT '',
    sector        TEXT    NOT NULL DEFAULT '',
    shares        REAL    NOT NULL DEFAULT 0,
    buy_price     REAL    NOT NULL DEFAULT 0,
    buy_date      DATE,
    stop_loss_pct REAL    NOT NULL DEFAULT -10.0,
    trailing_stop BOOLEAN NOT NULL DEFAULT 0,
    created_at    DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- watchlist
CREATE TABLE IF NOT EXISTS watchlist (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker    TEXT    NOT NULL,
    name      TEXT    NOT NULL DEFAULT '',
    reason    TEXT    NOT NULL DEFAULT '',
    added_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- screening_results (daily screening output)
CREATE TABLE IF NOT EXISTS screening_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            DATE    NOT NULL,
    ticker          TEXT    NOT NULL,
    name            TEXT    NOT NULL DEFAULT '',
    sector          TEXT    NOT NULL DEFAULT '',
    score           REAL    NOT NULL DEFAULT 0,
    per             REAL,
    pbr             REAL,
    dividend_yield  REAL,
    momentum_score  REAL,
    value_score     REAL
);

-- signals (offensive signals)
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT    NOT NULL,
    signal_type TEXT    NOT NULL,
    priority    TEXT    NOT NULL DEFAULT 'medium',
    message     TEXT    NOT NULL DEFAULT '',
    detail      TEXT,
    is_valid    BOOLEAN NOT NULL DEFAULT 1,
    expires_at  DATETIME,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- alerts (defensive alerts)
CREATE TABLE IF NOT EXISTS alerts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id      INTEGER REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker            TEXT,
    alert_type        TEXT    NOT NULL,
    level             INTEGER NOT NULL DEFAULT 1,
    message           TEXT    NOT NULL DEFAULT '',
    action_suggestion TEXT    NOT NULL DEFAULT '',
    is_read           BOOLEAN NOT NULL DEFAULT 0,
    is_resolved       BOOLEAN NOT NULL DEFAULT 0,
    created_at        DATETIME NOT NULL DEFAULT (datetime('now')),
    resolved_at       DATETIME
);

-- risk_metrics (daily risk snapshot)
CREATE TABLE IF NOT EXISTS risk_metrics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id          INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    date                  DATE    NOT NULL,
    health_score          REAL,
    max_drawdown          REAL,
    portfolio_volatility  REAL,
    sharpe_ratio          REAL,
    hhi                   REAL,
    var_95                REAL
);

-- stop_loss_rules
CREATE TABLE IF NOT EXISTS stop_loss_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker          TEXT    NOT NULL,
    buy_price       REAL    NOT NULL,
    stop_loss_pct   REAL    NOT NULL DEFAULT -10.0,
    trailing_stop   BOOLEAN NOT NULL DEFAULT 0,
    highest_price   REAL,
    is_active       BOOLEAN NOT NULL DEFAULT 1
);

-- price_cache (OHLCV cache)
CREATE TABLE IF NOT EXISTS price_cache (
    ticker  TEXT    NOT NULL,
    date    DATE    NOT NULL,
    open    REAL,
    high    REAL,
    low     REAL,
    close   REAL,
    volume  INTEGER,
    PRIMARY KEY (ticker, date)
);

-- learning_cards
CREATE TABLE IF NOT EXISTS learning_cards (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    card_key            TEXT    UNIQUE NOT NULL,
    title               TEXT    NOT NULL,
    content             TEXT    NOT NULL DEFAULT '',
    category            TEXT    NOT NULL DEFAULT 'term',
    related_signal_type TEXT
);

-- simulation_trades (paper trading)
CREATE TABLE IF NOT EXISTS simulation_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT    NOT NULL,
    action          TEXT    NOT NULL,
    price           REAL    NOT NULL,
    quantity        INTEGER NOT NULL,
    virtual_balance REAL    NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- simulation_scenarios (What-If)
CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_type   TEXT    NOT NULL,
    parameters      TEXT,
    result_summary  TEXT,
    result_data     TEXT,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON holdings(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_portfolio ON alerts(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts(is_read, is_resolved);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_portfolio_date ON risk_metrics(portfolio_id, date);
CREATE INDEX IF NOT EXISTS idx_screening_date ON screening_results(date);
CREATE INDEX IF NOT EXISTS idx_price_cache_ticker ON price_cache(ticker);
"""


def get_db_path() -> Path:
    return DEFAULT_DB_PATH


def init_db(db_path: str | Path | None = None) -> None:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("Database initialized at %s", path)
    finally:
        conn.close()


@contextmanager
def get_connection(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class _AsyncDB:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    async def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        import asyncio
        return await asyncio.to_thread(self._conn.execute, sql, params)

    async def execute_fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        import asyncio
        def _run() -> list[sqlite3.Row]:
            return self._conn.execute(sql, params).fetchall()
        return await asyncio.to_thread(_run)

    async def execute_fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        import asyncio
        def _run() -> sqlite3.Row | None:
            return self._conn.execute(sql, params).fetchone()
        return await asyncio.to_thread(_run)

    async def commit(self) -> None:
        import asyncio
        await asyncio.to_thread(self._conn.commit)


_async_db: _AsyncDB | None = None


async def init_db_async(db_path: str | Path | None = None) -> None:
    init_db(db_path)
    global _async_db
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    _async_db = _AsyncDB(conn)


async def get_db() -> _AsyncDB:
    global _async_db
    if _async_db is None:
        await init_db_async()
    return _async_db
