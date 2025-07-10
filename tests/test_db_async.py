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
    record_referral,
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


@pytest.mark.asyncio
async def test_record_referral(tmp_path, monkeypatch):
    db_file = tmp_path / "ref.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("db.DB_PATH", str(db_file), raising=False)
    await init_db()
    assert await record_referral(2, 1)
    assert not await record_referral(2, 1)
    assert not await record_referral(1, 1)
