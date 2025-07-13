import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import aiosqlite

# Add repo root to import path and ensure bot token is set for aiogram
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("BOT_TOKEN", "123456789:TESTTOKENEXAMPLEEXAMPLEEXAMPLEEX")

import admin


@pytest.mark.asyncio
async def test_add_and_list_users(tmp_path, monkeypatch):
    db_file = tmp_path / "test.sqlite"

    def _get_conn():
        return aiosqlite.connect(db_file)

    monkeypatch.setattr(admin, "get_connection", _get_conn)

    # Prepare tables
    async with _get_conn() as conn:
        await conn.execute(
            "CREATE TABLE users (user_id INTEGER PRIMARY KEY, registered_at TEXT)"
        )
        await conn.execute(
            "CREATE TABLE keys (user_id INTEGER, vpn_id TEXT, expires_at TEXT)"
        )
        await conn.commit()

    add_msg = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057), text="/add_user 42", answer=AsyncMock()
    )
    await admin.cmd_add_user(add_msg)
    add_msg.answer.assert_awaited_with("Пользователь добавлен.")

    list_msg = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057), text="/users", answer=AsyncMock()
    )
    await admin.cmd_users(list_msg)
    list_msg.answer.assert_awaited()
    assert "42" in list_msg.answer.await_args[0][0]


@pytest.mark.asyncio
async def test_wipe_db_confirmation(tmp_path, monkeypatch):
    db_file = tmp_path / "wipe.sqlite"

    def _get_conn():
        return aiosqlite.connect(db_file)

    monkeypatch.setattr(admin, "get_connection", _get_conn)

    async with _get_conn() as conn:
        await conn.execute(
            "CREATE TABLE users (user_id INTEGER PRIMARY KEY, registered_at TEXT)"
        )
        await conn.execute("INSERT INTO users VALUES (1, 'now')")
        await conn.execute(
            "CREATE TABLE keys (user_id INTEGER, vpn_id TEXT, expires_at TEXT)"
        )
        await conn.execute(
            "INSERT INTO keys VALUES (1, '11', '2099')"
        )
        await conn.commit()

    msg = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057), text="/wipe_db", answer=AsyncMock()
    )
    await admin.cmd_wipe_db(msg)
    msg.answer.assert_awaited()
    assert "confirm" in msg.answer.await_args[0][0]

    msg2 = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057), text="/wipe_db confirm", answer=AsyncMock(),
    )
    manager = Mock()
    with patch("bot.outline_manager", return_value=manager):
        await admin.cmd_wipe_db(msg2)
    msg2.answer.assert_awaited_with("База данных очищена.")
    manager.delete.assert_called_with("11")


    async with _get_conn() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        count = (await cursor.fetchone())[0]
    assert count == 0
