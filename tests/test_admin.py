import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

# Add repo root to import path and ensure bot token is set for aiogram
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "123456789:TESTTOKENEXAMPLEEXAMPLEEXAMPLEEX")

from admin import cmd_users, cmd_userlist  # noqa: E402


@pytest.mark.asyncio
async def test_cmd_users_formats_stats():
    message = SimpleNamespace(from_user=SimpleNamespace(id=124508057), answer=AsyncMock())
    with patch("admin.get_users_stats", new=AsyncMock(return_value=(10, 7, 2, 4, 1))):
        await cmd_users(message)
    expected = (
        "\u0412\u0441\u0435\u0433\u043e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439: 10\n"
        "\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0445: 7\n"
        "\u0421 \u043f\u0440\u043e\u0431\u043d\u044b\u043c \u0434\u043e\u0441\u0442\u0443\u043f\u043e\u043c: 2\n"
        "\u0421 \u043f\u043b\u0430\u0442\u043d\u043e\u0439 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u043e\u0439: 4\n"
        "\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0432\u0448\u0438\u0445 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443: 1"
    )
    message.answer.assert_awaited_with(expected)


@pytest.mark.asyncio
async def test_cmd_userlist_formats_user_block():
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057),
        text="/userlist",
        answer=AsyncMock(),
    )
    row = (7, "alice", 0, 1, 1700000000, 1700003600)
    created = time.strftime("%Y-%m-%d", time.localtime(row[4]))
    expires = time.strftime("%Y-%m-%d", time.localtime(row[5]))
    expected = (
        f"\U0001f464 @alice | ID: 7\n"
        f"\U0001f511 \u0421\u0442\u0430\u0442\u0443\u0441: \u043f\u043b\u0430\u0442\u043d\u044b\u0439\n"
        f"\U0001f4c5 \u0410\u043a\u0442\u0438\u0432\u0430\u0446\u0438\u044f: {created}\n"
        f"\u23f3 \u0418\u0441\u0442\u0435\u043a\u0430\u0435\u0442: {expires}"
    )
    with patch("admin.get_all_users", new=AsyncMock(return_value=[row])), patch("admin.time.time", return_value=0):
        await cmd_userlist(message)
    message.answer.assert_awaited_with(expected)


@pytest.mark.asyncio
async def test_cmd_userlist_empty():
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=124508057),
        text="/userlist",
        answer=AsyncMock(),
    )
    with patch("admin.get_all_users", new=AsyncMock(return_value=[])):
        await cmd_userlist(message)
    message.answer.assert_awaited_with("\u041d\u0435\u0442 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439.")
