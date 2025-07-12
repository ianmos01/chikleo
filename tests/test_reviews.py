import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import menu_reviews  # noqa: E402


@pytest.mark.asyncio
async def test_menu_reviews_with_url():
    os.environ["REVIEWS_CHANNEL_URL"] = "https://t.me/test_channel"
    with patch("bot.REVIEWS_CHANNEL_URL", "https://t.me/test_channel"), patch(
        "bot.send_temporary", new=AsyncMock()
    ):
        message = SimpleNamespace(answer=AsyncMock())
        await menu_reviews(message)
        args, kwargs = message.answer.call_args
        kb = kwargs["reply_markup"]
        assert kb.inline_keyboard[0][0].url == "https://t.me/test_channel"


@pytest.mark.asyncio
async def test_menu_reviews_without_url():
    if "REVIEWS_CHANNEL_URL" in os.environ:
        del os.environ["REVIEWS_CHANNEL_URL"]
    with patch("bot.REVIEWS_CHANNEL_URL", None), patch(
        "bot.send_temporary", new=AsyncMock()
    ) as send_mock:
        message = SimpleNamespace(chat=SimpleNamespace(id=1))
        await menu_reviews(message)
        send_mock.assert_awaited()

