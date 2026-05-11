from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import httpx

from gakkari.db import get_cached_rate, upsert_rate

_FRANKFURTER_URL = "https://api.frankfurter.app/latest"
_TIMEOUT = 5.0


def get_rate(conn: sqlite3.Connection, base: str, quote: str) -> Decimal:
    """Return the rate to convert 1 unit of `base` into `quote`.

    Resolution order: identity, today's cache hit, live fetch (which caches).
    On any network or parse failure, returns Decimal("1") so totals degrade
    to raw amounts rather than crashing.
    """
    if base == quote:
        return Decimal("1")
    today = date.today()
    cached = get_cached_rate(conn, base, quote, today)
    if cached is not None:
        return cached
    try:
        resp = httpx.get(
            _FRANKFURTER_URL,
            params={"from": base, "to": quote},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        rate = Decimal(str(payload["rates"][quote]))
    except Exception:
        # Cache the fallback too so we do not retry the same failing pair on
        # every UI refresh — one bad currency would otherwise burn a 5-second
        # HTTP timeout per render.
        rate = Decimal("1")
    upsert_rate(conn, base, quote, rate, today)
    return rate
