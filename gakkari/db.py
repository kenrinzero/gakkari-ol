from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from gakkari.models import RenewalLog, Settings, Subscription

DB_PATH = Path(__file__).parent.parent / "data" / "gakkari.db"


def _adapt_decimal(d: Decimal) -> str:
    return str(d)


def _convert_decimal(s: bytes) -> Decimal:
    return Decimal(s.decode())


def _adapt_date(d: date) -> str:
    return d.isoformat()


def _convert_date(s: bytes) -> date:
    return date.fromisoformat(s.decode())


sqlite3.register_adapter(Decimal, _adapt_decimal)
sqlite3.register_converter("DECIMAL", _convert_decimal)
sqlite3.register_adapter(date, _adapt_date)
sqlite3.register_converter("DATE", _convert_date)

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    amount           DECIMAL NOT NULL,
    currency         TEXT    NOT NULL DEFAULT 'USD',
    billing_period   TEXT    NOT NULL DEFAULT 'monthly',
    next_renewal_date DATE   NOT NULL,
    category         TEXT    NOT NULL DEFAULT '',
    notes            TEXT    NOT NULL DEFAULT '',
    tax_mode         TEXT    NOT NULL DEFAULT 'none',
    tax_rate         DECIMAL NOT NULL DEFAULT '0',
    status           TEXT    NOT NULL DEFAULT 'active',
    trial_ends       DATE
);

CREATE TABLE IF NOT EXISTS settings (
    id                     INTEGER PRIMARY KEY CHECK (id = 1),
    base_currency          TEXT    NOT NULL DEFAULT 'USD',
    price_display_mode     TEXT    NOT NULL DEFAULT 'gross',
    due_soon_days          INTEGER NOT NULL DEFAULT 7,
    mascot_enabled         INTEGER NOT NULL DEFAULT 1,
    notices_enabled        INTEGER NOT NULL DEFAULT 1,
    language               TEXT    NOT NULL DEFAULT 'en',
    convert_column_enabled INTEGER NOT NULL DEFAULT 0,
    convert_currency       TEXT    NOT NULL DEFAULT '',
    totals_view_mode       TEXT    NOT NULL DEFAULT 'estimate',
    sort_mode              TEXT    NOT NULL DEFAULT 'date'
);

CREATE TABLE IF NOT EXISTS exchange_rate_cache (
    base_currency  TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate           DECIMAL NOT NULL,
    fetched_at     DATE NOT NULL,
    PRIMARY KEY (base_currency, quote_currency)
);

CREATE TABLE IF NOT EXISTS renewal_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    renewed_on      DATE NOT NULL,
    amount          DECIMAL NOT NULL,
    currency        TEXT NOT NULL,
    billing_period  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_renewal_log_date ON renewal_log(renewed_on);
CREATE INDEX IF NOT EXISTS idx_renewal_log_sub ON renewal_log(subscription_id);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
        _migrations: tuple[str, ...] = (
            "ALTER TABLE settings ADD COLUMN language TEXT NOT NULL DEFAULT 'en'",
            "ALTER TABLE settings ADD COLUMN convert_column_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE settings ADD COLUMN convert_currency TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE settings ADD COLUMN totals_view_mode TEXT NOT NULL DEFAULT 'estimate'",
            "ALTER TABLE settings ADD COLUMN sort_mode TEXT NOT NULL DEFAULT 'date'",
            "ALTER TABLE subscriptions ADD COLUMN trial_ends DATE",
        )
        for stmt in _migrations:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass


# ── Subscriptions ────────────────────────────────────────────────────────────

def _row_to_sub(row: sqlite3.Row) -> Subscription:
    return Subscription(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        currency=row["currency"],
        billing_period=row["billing_period"],
        next_renewal_date=row["next_renewal_date"],
        category=row["category"],
        notes=row["notes"],
        tax_mode=row["tax_mode"],
        tax_rate=row["tax_rate"],
        status=row["status"],
        trial_ends=row["trial_ends"],
    )


def list_subscriptions(
    conn: sqlite3.Connection,
    statuses: tuple[str, ...] = ("active", "paused"),
) -> list[Subscription]:
    placeholders = ", ".join("?" for _ in statuses)
    rows = conn.execute(
        f"SELECT * FROM subscriptions WHERE status IN ({placeholders}) ORDER BY next_renewal_date",
        statuses,
    ).fetchall()
    return [_row_to_sub(r) for r in rows]


def insert_subscription(conn: sqlite3.Connection, sub: Subscription) -> int:
    cur = conn.execute(
        """INSERT INTO subscriptions
           (name, amount, currency, billing_period, next_renewal_date,
            category, notes, tax_mode, tax_rate, status, trial_ends)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status, sub.trial_ends),
    )
    return cur.lastrowid


def update_subscription(conn: sqlite3.Connection, sub: Subscription) -> None:
    conn.execute(
        """UPDATE subscriptions SET
           name=?, amount=?, currency=?, billing_period=?, next_renewal_date=?,
           category=?, notes=?, tax_mode=?, tax_rate=?, status=?, trial_ends=?
           WHERE id=?""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status, sub.trial_ends, sub.id),
    )


def delete_subscription(conn: sqlite3.Connection, sub_id: int) -> None:
    conn.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))


# ── Settings ─────────────────────────────────────────────────────────────────

def load_settings(conn: sqlite3.Connection) -> Settings:
    row = conn.execute("SELECT * FROM settings WHERE id=1").fetchone()
    return Settings(
        id=row["id"],
        base_currency=row["base_currency"],
        price_display_mode=row["price_display_mode"],
        due_soon_days=row["due_soon_days"],
        mascot_enabled=bool(row["mascot_enabled"]),
        notices_enabled=bool(row["notices_enabled"]),
        language=row["language"],
        convert_column_enabled=bool(row["convert_column_enabled"]),
        convert_currency=row["convert_currency"],
        totals_view_mode=row["totals_view_mode"],
        sort_mode=row["sort_mode"],
    )


def save_settings(conn: sqlite3.Connection, s: Settings) -> None:
    conn.execute(
        """UPDATE settings SET
           base_currency=?, price_display_mode=?, due_soon_days=?,
           mascot_enabled=?, notices_enabled=?, language=?,
           convert_column_enabled=?, convert_currency=?,
           totals_view_mode=?, sort_mode=?
           WHERE id=1""",
        (s.base_currency, s.price_display_mode, s.due_soon_days,
         int(s.mascot_enabled), int(s.notices_enabled), s.language,
         int(s.convert_column_enabled), s.convert_currency,
         s.totals_view_mode, s.sort_mode),
    )


# ── Exchange rate cache ──────────────────────────────────────────────────────

def get_cached_rate(
    conn: sqlite3.Connection, base: str, quote: str, today: date
) -> Decimal | None:
    row = conn.execute(
        "SELECT rate, fetched_at FROM exchange_rate_cache "
        "WHERE base_currency=? AND quote_currency=?",
        (base, quote),
    ).fetchone()
    if row is None or row["fetched_at"] != today:
        return None
    return row["rate"]


def upsert_rate(
    conn: sqlite3.Connection, base: str, quote: str, rate: Decimal, today: date
) -> None:
    conn.execute(
        "INSERT INTO exchange_rate_cache (base_currency, quote_currency, rate, fetched_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(base_currency, quote_currency) DO UPDATE SET "
        "  rate=excluded.rate, fetched_at=excluded.fetched_at",
        (base, quote, rate, today),
    )


# ── Renewal log ──────────────────────────────────────────────────────────────

def insert_renewal(
    conn: sqlite3.Connection,
    subscription_id: int,
    renewed_on: date,
    amount: Decimal,
    currency: str,
    billing_period: str,
) -> int:
    cur = conn.execute(
        """INSERT INTO renewal_log
           (subscription_id, renewed_on, amount, currency, billing_period)
           VALUES (?, ?, ?, ?, ?)""",
        (subscription_id, renewed_on, amount, currency, billing_period),
    )
    return cur.lastrowid


def list_renewals(
    conn: sqlite3.Connection,
    subscription_id: int | None = None,
    limit: int | None = None,
) -> list[RenewalLog]:
    """Recent-first list. Joins subscription name so the history view can
    label entries even if the sub was later renamed or soft-deleted."""
    sql = """
        SELECT r.id, r.subscription_id, r.renewed_on, r.amount, r.currency,
               r.billing_period, COALESCE(s.name, '') AS sub_name
        FROM renewal_log r
        LEFT JOIN subscriptions s ON s.id = r.subscription_id
    """
    params: tuple = ()
    if subscription_id is not None:
        sql += " WHERE r.subscription_id = ?"
        params = (subscription_id,)
    sql += " ORDER BY r.renewed_on DESC, r.id DESC"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    rows = conn.execute(sql, params).fetchall()
    return [
        RenewalLog(
            id=r["id"],
            subscription_id=r["subscription_id"],
            renewed_on=r["renewed_on"],
            amount=r["amount"],
            currency=r["currency"],
            billing_period=r["billing_period"],
            sub_name=r["sub_name"],
        )
        for r in rows
    ]
