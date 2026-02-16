"""Database initialization and connection management.

Creates all tables defined in the integrated specification (Section 3).
"""

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

-- user_profile (education stage / level / XP)
CREATE TABLE IF NOT EXISTS user_profile (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    stage               INTEGER NOT NULL DEFAULT 1,
    level               INTEGER NOT NULL DEFAULT 1,
    xp                  INTEGER NOT NULL DEFAULT 0,
    safe_mode           BOOLEAN NOT NULL DEFAULT 0,
    login_streak        INTEGER NOT NULL DEFAULT 0,
    last_login_date     DATE,
    total_login_days    INTEGER NOT NULL DEFAULT 0,
    stage_upgraded_at   DATETIME,
    self_declared_stage INTEGER,
    created_at          DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- user_xp_log
CREATE TABLE IF NOT EXISTS user_xp_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES user_profile(id),
    action_type TEXT    NOT NULL,
    xp_earned   INTEGER NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- user_badges
CREATE TABLE IF NOT EXISTS user_badges (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES user_profile(id),
    badge_id  TEXT    NOT NULL,
    earned_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- learning_cards
CREATE TABLE IF NOT EXISTS learning_cards (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    card_key            TEXT    UNIQUE NOT NULL,
    title               TEXT    NOT NULL,
    content_lv1         TEXT    NOT NULL DEFAULT '',
    content_lv2         TEXT    NOT NULL DEFAULT '',
    content_lv3         TEXT    NOT NULL DEFAULT '',
    content_lv4         TEXT    NOT NULL DEFAULT '',
    category            TEXT    NOT NULL DEFAULT 'term',
    related_signal_type TEXT
);

-- user_card_history
CREATE TABLE IF NOT EXISTS user_card_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES user_profile(id),
    card_id   INTEGER NOT NULL REFERENCES learning_cards(id),
    viewed_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- simulation_trades (paper trading)
CREATE TABLE IF NOT EXISTS simulation_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES user_profile(id),
    ticker          TEXT    NOT NULL,
    action          TEXT    NOT NULL,
    price           REAL    NOT NULL,
    quantity        INTEGER NOT NULL,
    virtual_balance REAL    NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- signal_outcomes
CREATE TABLE IF NOT EXISTS signal_outcomes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id        INTEGER NOT NULL REFERENCES signals(id),
    user_id          INTEGER NOT NULL REFERENCES user_profile(id),
    user_action      TEXT    NOT NULL DEFAULT 'ignored',
    price_at_signal  REAL,
    price_after_7d   REAL,
    price_after_30d  REAL,
    is_success       BOOLEAN
);

-- alert_outcomes
CREATE TABLE IF NOT EXISTS alert_outcomes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id         INTEGER NOT NULL REFERENCES alerts(id),
    user_id          INTEGER NOT NULL REFERENCES user_profile(id),
    user_action      TEXT    NOT NULL DEFAULT 'ignored',
    action_detail    TEXT,
    price_at_alert   REAL,
    price_after_7d   REAL,
    price_after_30d  REAL,
    portfolio_impact REAL
);

-- education_logs
CREATE TABLE IF NOT EXISTS education_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES user_profile(id),
    event_type TEXT    NOT NULL,
    target_id  TEXT,
    context    TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- simulation_scenarios (What-If)
CREATE TABLE IF NOT EXISTS simulation_scenarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES user_profile(id),
    scenario_type   TEXT    NOT NULL,
    parameters      TEXT,
    result_summary  TEXT,
    result_data     TEXT,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON holdings(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_alerts_portfolio ON alerts(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unread ON alerts(is_read, is_resolved);
CREATE INDEX IF NOT EXISTS idx_risk_metrics_portfolio_date ON risk_metrics(portfolio_id, date);
CREATE INDEX IF NOT EXISTS idx_screening_date ON screening_results(date);
CREATE INDEX IF NOT EXISTS idx_price_cache_ticker ON price_cache(ticker);

-- Education indexes
CREATE INDEX IF NOT EXISTS idx_user_xp_log_user ON user_xp_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_user ON user_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_user_card_history_user ON user_card_history(user_id);
CREATE INDEX IF NOT EXISTS idx_simulation_trades_user ON simulation_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_user ON signal_outcomes(user_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal ON signal_outcomes(signal_id);
CREATE INDEX IF NOT EXISTS idx_alert_outcomes_user ON alert_outcomes(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_outcomes_alert ON alert_outcomes(alert_id);
CREATE INDEX IF NOT EXISTS idx_education_logs_user ON education_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_simulation_scenarios_user ON simulation_scenarios(user_id);
"""


def get_db_path() -> Path:
    """Return the resolved database file path."""
    return DEFAULT_DB_PATH


def init_db(db_path: str | Path | None = None) -> None:
    """Create all tables if they don't exist.

    Safe to call multiple times (uses CREATE TABLE IF NOT EXISTS).
    """
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
    """Context manager that yields a SQLite connection.

    Usage::

        with get_connection() as conn:
            conn.execute("SELECT ...")
    """
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


# ---------------------------------------------------------------------------
# Async helpers (used by FastAPI async endpoints)
# ---------------------------------------------------------------------------

class _AsyncDB:
    """Thin async wrapper around synchronous sqlite3 for FastAPI usage."""

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
    """Async init_db: creates tables and keeps a persistent connection."""
    init_db(db_path)
    global _async_db
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    _async_db = _AsyncDB(conn)


async def get_db() -> _AsyncDB:
    """Return the async DB wrapper. Call init_db_async first."""
    global _async_db
    if _async_db is None:
        await init_db_async()
    return _async_db
