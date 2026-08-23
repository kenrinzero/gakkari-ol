"""Shared pytest fixtures.

The ``db`` fixture points the data layer at a throwaway SQLite file via the
GAKKARI_DB env seam (see gakkari.db.db_path), so DB tests never touch the
user's real data/gakkari.db.
"""
from __future__ import annotations

import pytest

from gakkari.db import init_db


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("GAKKARI_DB", str(tmp_path / "gakkari.db"))
    init_db()
