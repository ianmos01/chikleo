import os
import sys

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault(
    "BOT_TOKEN", "123456789:TESTTOKENEXAMPLEEXAMPLEEXAMPLEEX"
)

from bot import send_temporary  # noqa: E402


@pytest.mark.asyncio
async def test_send_temporary_deletes_message():
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=10))

    tasks = []
    orig_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = orig_create_task(coro)
        tasks.append(task)
        return task

    with patch("bot.asyncio.create_task", side_effect=fake_create_task), patch(
        "bot.asyncio.sleep", new=AsyncMock()
    ) as sleep_mock:
        await send_temporary(bot, 123, "hi", delay=5)
        await asyncio.gather(*tasks)
        bot.send_message.assert_awaited_with(123, "hi")
        assert any(c.args[0] == 5 for c in sleep_mock.await_args_list)
        bot.delete_message.assert_awaited_with(123, 10)
