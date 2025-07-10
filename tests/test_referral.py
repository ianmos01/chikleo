import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import cmd_start, menu_invite  # noqa: E402


@pytest.mark.asyncio
async def test_cmd_start_records_referral():
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=5, first_name="Bob"),
        chat=SimpleNamespace(id=10),
        text="/start ref3",
        answer=AsyncMock(),
    )

    with patch("bot.record_referral", new=AsyncMock(return_value=True)) as rec, \
        patch("bot.logging.info") as log:
        await cmd_start(message)
        rec.assert_awaited_with(5, 3)
        log.assert_called_with("User %s joined via referral from %s", 5, 3)


@pytest.mark.asyncio
async def test_menu_invite_generates_link():
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=4, first_name="Ann"),
        chat=SimpleNamespace(id=15),
        answer=AsyncMock(),
    )

    with patch("bot.get_bot_username", new=AsyncMock(return_value="VPNos_bot")):
        await menu_invite(message)

    args, kwargs = message.answer.call_args
    assert "https://t.me/VPNos_bot?start=ref4" in args[0]
    kb = kwargs["reply_markup"]
    assert kb.inline_keyboard[0][0].switch_inline_query == "https://t.me/VPNos_bot?start=ref4"
    assert kb.inline_keyboard[1][0].callback_data == "main_menu"
