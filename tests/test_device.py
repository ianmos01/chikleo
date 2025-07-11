import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import callback_device, DEVICE_LINKS  # noqa: E402


@pytest.mark.asyncio
async def test_callback_device_sends_instructions():
    message = AsyncMock()
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        data="device_android",
        message=message,
        answer=AsyncMock(),
    )
    with patch("bot.get_key_info", new=AsyncMock(return_value=(7, "url", 0, False))):
        await callback_device(callback)
    message.answer.assert_awaited()
    args, _ = message.answer.await_args
    assert DEVICE_LINKS["android"] in args[0]
    assert "url" in args[0]
    callback.answer.assert_awaited()
