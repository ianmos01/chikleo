import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, Mock

import pytest

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import schedule_key_deletion, callback_trial


@pytest.mark.asyncio
async def test_schedule_key_deletion_removes_key():
    tasks = []
    orig_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = orig_create_task(coro)
        tasks.append(task)
        return task

    manager = Mock()
    with patch('bot.outline_manager', return_value=manager), \
         patch('bot.asyncio.create_task', side_effect=fake_create_task), \
         patch('bot.asyncio.sleep', new=AsyncMock()) as sleep_mock:
        await schedule_key_deletion(5, delay=5)
        await asyncio.gather(*tasks)
        assert any(c.args[0] == 5 for c in sleep_mock.await_args_list)
        manager.delete.assert_called_with(5)


@pytest.mark.asyncio
async def test_callback_trial_creates_key_and_schedules_deletion():
    key = {"id": 7, "accessUrl": "url"}

    message = AsyncMock()
    message.chat.id = 42

    callback = SimpleNamespace(from_user=SimpleNamespace(id=1), message=message, answer=AsyncMock())

    tasks = []
    orig_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = orig_create_task(coro)
        tasks.append(task)
        return task

    manager = Mock()
    with patch('bot.create_outline_key', AsyncMock(return_value=key)), \
         patch('bot.outline_manager', return_value=manager), \
         patch('bot.asyncio.create_task', side_effect=fake_create_task), \
         patch('bot.asyncio.sleep', new=AsyncMock()):
        await callback_trial(callback)
        await asyncio.gather(*tasks)
        message.answer.assert_awaited_with('Ваш пробный ключ на 24 часа:\nurl')
        manager.delete.assert_called_with(7)
        callback.answer.assert_awaited()
