"""Tests for asynchronous database functions."""

import os
import sys
import shutil

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


@pytest.mark.asyncio
async def test_record_referral_existing_user(tmp_path, monkeypatch):
    db_file = tmp_path / "ref.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("db.DB_PATH", str(db_file), raising=False)
    await init_db()
    await add_key(3, 7, "url", 999, False)
    assert not await record_referral(3, 1)


@pytest.mark.asyncio
async def test_init_db_creates_directory(tmp_path, monkeypatch):
    """Ensure init_db creates missing parent directories."""
    db_file = tmp_path / "subdir" / "db.sqlite"
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("db.DB_PATH", str(db_file), raising=False)
    # create then remove directory to simulate missing path
    db_file.parent.mkdir()
    shutil.rmtree(db_file.parent)
    assert not db_file.parent.exists()
    await init_db()
    assert db_file.exists()
    assert db_file.parent.exists()
