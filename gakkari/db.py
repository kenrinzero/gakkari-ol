from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path

from gakkari.models import RenewalLog, Settings, Subscription

DB_PATH = Path(__file__).parent.parent / "data" / "gakkari.db"
BACKUP_KEEP = 7  # rotating daily snapshots to retain


def _db_path() -> Path:
    """Resolved DB path. The GAKKARI_DB env var overrides the default, letting
    tests and tooling point at an alternate DB; read at call-time so there are
    no import-order traps."""
    env = os.environ.get("GAKKARI_DB")
    return Path(env) if env else DB_PATH


def _backup_dir() -> Path:
    return _db_path().parent / "backups"


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
    trial_ends       DATE,
    payment_method   TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    id                     INTEGER PRIMARY KEY CHECK (id = 1),
    base_currency          TEXT    NOT NULL DEFAULT 'USD',
    price_display_mode     TEXT    NOT NULL DEFAULT 'gross',
    due_soon_days          INTEGER NOT NULL DEFAULT 7,
    monthly_income         DECIMAL NOT NULL DEFAULT '0',
    monthly_income_currency TEXT   NOT NULL DEFAULT '',
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
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
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


def backup_db(today: date | None = None) -> Path | None:
    """Once-per-day rotating snapshot of the DB, kept locally under data/backups/.

    The DB is the user's only copy (no cloud by design), so a bad import, a
    crash mid-write, or a disk hiccup could otherwise wipe years of history.
    Uses SQLite's online backup API (not a raw file copy) so the snapshot is
    consistent even under WAL. Skips if today's snapshot already exists, then
    prunes to the most recent ``BACKUP_KEEP``. Best-effort: the backup must
    never itself put the app or data at risk, so any failure is swallowed and
    startup continues. Returns the snapshot path if one was written, else None.
    """
    today = today or date.today()
    db_path = _db_path()
    if not db_path.exists():
        return None  # nothing to back up yet (first run)
    try:
        backup_dir = _backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / f"gakkari-{today.isoformat()}.db"
        if dest.exists():
            return None  # already snapshotted today
        src = sqlite3.connect(db_path)
        try:
            dst = sqlite3.connect(dest)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        # Filenames sort chronologically (ISO date), so drop all but the newest.
        for old in sorted(backup_dir.glob("gakkari-*.db"))[:-BACKUP_KEEP]:
            try:
                old.unlink()
            except OSError:
                pass
        return dest
    except Exception:
        return None


def init_db() -> None:
    backup_db()
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
        _migrations: tuple[str, ...] = (
            "ALTER TABLE settings ADD COLUMN language TEXT NOT NULL DEFAULT 'en'",
            "ALTER TABLE settings ADD COLUMN convert_column_enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE settings ADD COLUMN convert_currency TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE settings ADD COLUMN monthly_income DECIMAL NOT NULL DEFAULT '0'",
            "ALTER TABLE settings ADD COLUMN monthly_income_currency TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE settings ADD COLUMN totals_view_mode TEXT NOT NULL DEFAULT 'estimate'",
            "ALTER TABLE settings ADD COLUMN sort_mode TEXT NOT NULL DEFAULT 'date'",
            "ALTER TABLE subscriptions ADD COLUMN trial_ends DATE",
            "ALTER TABLE subscriptions ADD COLUMN payment_method TEXT NOT NULL DEFAULT ''",
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
        payment_method=row["payment_method"],
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
            category, notes, tax_mode, tax_rate, status, trial_ends,
            payment_method)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status, sub.trial_ends,
         sub.payment_method),
    )
    return cur.lastrowid


def update_subscription(conn: sqlite3.Connection, sub: Subscription) -> None:
    conn.execute(
        """UPDATE subscriptions SET
           name=?, amount=?, currency=?, billing_period=?, next_renewal_date=?,
           category=?, notes=?, tax_mode=?, tax_rate=?, status=?, trial_ends=?,
           payment_method=?
           WHERE id=?""",
        (sub.name, sub.amount, sub.currency, sub.billing_period,
         sub.next_renewal_date, sub.category, sub.notes,
         sub.tax_mode, sub.tax_rate, sub.status, sub.trial_ends,
         sub.payment_method, sub.id),
    )


# ── Settings ─────────────────────────────────────────────────────────────────

def load_settings(conn: sqlite3.Connection) -> Settings:
    row = conn.execute("SELECT * FROM settings WHERE id=1").fetchone()
    return Settings(
        id=row["id"],
        base_currency=row["base_currency"],
        price_display_mode=row["price_display_mode"],
        due_soon_days=row["due_soon_days"],
        monthly_income=row["monthly_income"],
        monthly_income_currency=row["monthly_income_currency"],
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
           monthly_income=?, monthly_income_currency=?,
           notices_enabled=?, language=?,
           convert_column_enabled=?, convert_currency=?,
           totals_view_mode=?, sort_mode=?
           WHERE id=1""",
        (s.base_currency, s.price_display_mode, s.due_soon_days,
         s.monthly_income, s.monthly_income_currency,
         int(s.notices_enabled),
         s.language, int(s.convert_column_enabled), s.convert_currency,
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


def get_last_rate(
    conn: sqlite3.Connection, base: str, quote: str
) -> tuple[Decimal, date] | None:
    """Most recent cached rate for the pair regardless of age, as
    (rate, fetched_at), or None if it was never cached. Lets a failed live
    fetch fall back to a real (if old) rate instead of collapsing to 1:1."""
    row = conn.execute(
        "SELECT rate, fetched_at FROM exchange_rate_cache "
        "WHERE base_currency=? AND quote_currency=?",
        (base, quote),
    ).fetchone()
    if row is None:
        return None
    return row["rate"], row["fetched_at"]


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


def delete_renewal(conn: sqlite3.Connection, log_id: int) -> None:
    """Remove a single renewal_log row by id. Used only by the same-session
    undo of the last `k` acknowledgement — the ledger is otherwise append-only."""
    conn.execute("DELETE FROM renewal_log WHERE id=?", (log_id,))


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
