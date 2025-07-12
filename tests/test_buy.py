import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import buy_one_month  # noqa: E402


@pytest.mark.asyncio
async def test_buy_one_month_sends_link():
    message = SimpleNamespace(answer=AsyncMock())
    await buy_one_month(message)
    args, kwargs = message.answer.call_args
    kb = kwargs["reply_markup"]
    assert kb.inline_keyboard[0][0].url == "https://t.me/tribute/app?startapp=piiP"
