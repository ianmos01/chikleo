"""Tests for trial key workflow and scheduled deletion."""

import asyncio
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import callback_trial, schedule_key_deletion  # noqa: E402


@pytest.mark.asyncio
async def test_schedule_key_deletion_removes_key(task_spy):
    tasks, fake_create_task = task_spy

    manager = Mock()
    with patch("bot.outline_manager", return_value=manager), patch(
        "bot.asyncio.create_task", side_effect=fake_create_task
    ), patch("bot.asyncio.sleep", new=AsyncMock()) as sleep_mock:
        await schedule_key_deletion(5, delay=5)
        await asyncio.gather(*tasks)
        assert any(c.args[0] == 5 for c in sleep_mock.await_args_list)
        manager.delete.assert_called_with(5)


@pytest.mark.asyncio
async def test_callback_trial_creates_key_and_schedules_deletion():
    key = {"id": 7, "accessUrl": "url"}

    message = AsyncMock()
    message.chat.id = 42

    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1), message=message, answer=AsyncMock()
    )

    manager = Mock()
    create_key_mock = AsyncMock(return_value=key)
    with patch("bot.create_outline_key", create_key_mock), patch(
        "bot.outline_manager", return_value=manager
    ), patch("bot.add_key", new=AsyncMock()) as add_key_mock, patch(
        "bot.has_used_trial", new=AsyncMock(return_value=False)
    ), patch(
        "bot.schedule_key_deletion", AsyncMock()
    ) as sched_mock:
        await callback_trial(callback)
        create_key_mock.assert_awaited_with(label="vpn_1")
        add_key_mock.assert_awaited()
        sched_mock.assert_awaited_with(
            key["id"], delay=24 * 60 * 60, user_id=1, is_trial=True
        )
        message.answer.assert_awaited_with("Ваш пробный ключ на 24 часа:\nurl")
        callback.answer.assert_awaited()
