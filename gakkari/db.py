from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from gakkari.models import Settings, Subscription

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
    status           TEXT    NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS settings (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    base_currency      TEXT    NOT NULL DEFAULT 'USD',
    price_display_mode TEXT    NOT NULL DEFAULT 'gross',
    due_soon_days      INTEGER NOT NULL DEFAULT 7,
    mascot_enabled     INTEGER NOT NULL DEFAULT 1,
    notices_enabled    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS exchange_rate_cache (
    base_currency  TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate           DECIMAL NOT NULL,
    fetched_at     DATE NOT NULL,
    PRIMARY KEY (base_currency, quote_currency)
);
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
        conn.execute(
            "INSERT OR IGNORE INTO settings (id) VALUES (1)"
        )


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
    )


def list_subscriptions(conn: sqlite3.Connection, include_inactive: bool = False) -> list[Subscription]:
    if include_inactive:
        rows = conn.execute("SELECT * FROM subscriptions ORDER BY next_renewal_date").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE status = 'active' ORDER BY next_renewal_date"
        ).fetchall()
    return [_row_to_sub(r) for r in rows]


def insert_subscription(conn: sqlite3.Connection, sub: Subscription) -> int:
    cur = conn.execute(
        """INSERT INTO subscriptions
           (name, amount, currency, billing_period, next_renewal_date,
            category, notes, tax_mode, tax_rate, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status),
    )
    return cur.lastrowid


def update_subscription(conn: sqlite3.Connection, sub: Subscription) -> None:
    conn.execute(
        """UPDATE subscriptions SET
           name=?, amount=?, currency=?, billing_period=?, next_renewal_date=?,
           category=?, notes=?, tax_mode=?, tax_rate=?, status=?
           WHERE id=?""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status, sub.id),
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
    )


def save_settings(conn: sqlite3.Connection, s: Settings) -> None:
    conn.execute(
        """UPDATE settings SET
           base_currency=?, price_display_mode=?, due_soon_days=?,
           mascot_enabled=?, notices_enabled=?
           WHERE id=1""",
        (s.base_currency, s.price_display_mode, s.due_soon_days,
         int(s.mascot_enabled), int(s.notices_enabled)),
    )
