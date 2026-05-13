from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import httpx

from gakkari.db import get_cached_rate, upsert_rate

_FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"
_TIMEOUT = 5.0


def get_rate(conn: sqlite3.Connection, base: str, quote: str) -> Decimal:
    """Return the rate to convert 1 unit of `base` into `quote`.

    Resolution order: identity, today's cache hit, live fetch (which caches).
    On any network or parse failure, returns Decimal("1") so totals degrade
    to raw amounts rather than crashing. The fallback is intentionally not
    cached, so a transient outage self-heals on the next recompute instead
    of pinning the pair to rate 1 until midnight.
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
            follow_redirects=True,
        )
        resp.raise_for_status()
        payload = resp.json()
        rate = Decimal(str(payload["rates"][quote]))
        upsert_rate(conn, base, quote, rate, today)
    except Exception:
        rate = Decimal("1")
    return rate
