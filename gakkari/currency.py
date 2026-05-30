from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import httpx

from gakkari.db import get_cached_rate, get_last_rate, upsert_rate

_FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
_TIMEOUT = 5.0


def get_rate_status(
    conn: sqlite3.Connection, base: str, quote: str, today: date | None = None
) -> tuple[Decimal, str]:
    """Return (rate, status) to convert 1 unit of `base` into `quote`.

    status is one of:
      "fresh"   — identity, a same-day cache hit, or a successful live fetch
      "stale"   — the live fetch failed, so the last cached rate (from an
                  earlier day) is reused; it is NOT re-stamped, so the pair
                  self-heals on the next successful fetch
      "missing" — the fetch failed and the pair was never cached; rate is 1:1
                  as a last resort so totals don't crash

    Distinguishing "stale" from "missing" lets the UI flag truly-unknown rates
    apart from old-but-real ones, and means a genuine 1.0 fetched today reads
    as "fresh" rather than a fake fallback.
    """
    if base == quote:
        return Decimal("1"), "fresh"
    today = today or date.today()
    cached = get_cached_rate(conn, base, quote, today)
    if cached is not None:
        return cached, "fresh"
    try:
        resp = httpx.get(
            _FRANKFURTER_URL,
            params={"from": base, "to": quote},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        rate = Decimal(str(resp.json()["rates"][quote]))
        upsert_rate(conn, base, quote, rate, today)
        return rate, "fresh"
    except Exception:
        last = get_last_rate(conn, base, quote)
        if last is not None:
            return last[0], "stale"
        return Decimal("1"), "missing"


def get_rate(
    conn: sqlite3.Connection, base: str, quote: str, today: date | None = None
) -> Decimal:
    """Rate to convert 1 unit of `base` into `quote` — just the Decimal, for
    callers that don't need the freshness status. See `get_rate_status`."""
    return get_rate_status(conn, base, quote, today)[0]
