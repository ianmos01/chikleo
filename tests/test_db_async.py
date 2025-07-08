"""Tests for asynchronous database functions."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402

from db import (  # noqa: E402
    add_key,
    clear_key,
    get_active_key,
    has_used_trial,
    init_db,
)


@pytest.mark.asyncio
async def test_add_and_get_key(tmp_path, monkeypatch):
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("db.DB_PATH", str(db_file), raising=False)
    await init_db()
    await add_key(1, 2, "url", 123, False)
    row = await get_active_key(1)
    assert row == ("url", 123, 0)


@pytest.mark.asyncio
async def test_has_used_trial(tmp_path, monkeypatch):
    db_file = tmp_path / "trial.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("db.DB_PATH", str(db_file), raising=False)
    await init_db()
    assert not await has_used_trial(1)
    await add_key(1, 2, "url", 123, True)
    assert await has_used_trial(1)
    await clear_key(1, True)
    # even after clearing, trial usage remains recorded
    assert await has_used_trial(1)
