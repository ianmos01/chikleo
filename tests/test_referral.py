import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import (
    cmd_start,
    menu_invite,
    grant_referral_bonus,
    REFERRAL_BONUS_DAYS,
)



@pytest.mark.asyncio
async def test_cmd_start_records_referral():
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=5, first_name="Bob"),
        chat=SimpleNamespace(id=10),
        text="/start ref3",
        answer=AsyncMock(),
    )

    with patch("bot.record_referral", new=AsyncMock(return_value=True)) as rec, \
        patch("bot.logging.info") as log, patch("bot.grant_referral_bonus", new=AsyncMock()) as bonus:
        await cmd_start(message)
        rec.assert_awaited_with(5, 3)
        log.assert_called_with("User %s joined via referral from %s", 5, 3)
        bonus.assert_awaited_with(3)


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


@pytest.mark.asyncio
async def test_grant_referral_bonus_creates_key():
    now = 123
    key = {"id": 8, "accessUrl": "url"}
    with patch("bot.create_outline_key", new=AsyncMock(return_value=key)) as create_mock, patch(
        "bot.add_key", new=AsyncMock()
    ) as add_key_mock, patch(
        "bot.schedule_key_deletion"
    ) as sched_mock, patch(
        "bot.bot.send_message", new=AsyncMock()) as send_mock, patch(
        "bot.time.time", return_value=now):
        await grant_referral_bonus(4)
        assert create_mock.await_args.kwargs["label"].startswith("ref_bonus_4_")
        add_key_mock.assert_awaited_with(4, 8, "url", now + REFERRAL_BONUS_DAYS * 24 * 60 * 60, False)
        sched_mock.assert_called_with(8, delay=REFERRAL_BONUS_DAYS * 24 * 60 * 60, user_id=4, is_trial=False)
        send_mock.assert_awaited()


@pytest.mark.asyncio
async def test_grant_referral_bonus_message_text():
    key = {"id": 9, "accessUrl": "link"}
    with patch("bot.create_outline_key", new=AsyncMock(return_value=key)), patch(
        "bot.add_key", new=AsyncMock()), patch(
        "bot.schedule_key_deletion"), patch(
        "bot.time.time", return_value=456), patch(
        "bot.bot.send_message", new=AsyncMock()) as send_mock:
        await grant_referral_bonus(5)
        msg = send_mock.await_args.args[1]
        assert "\u0434\u043e\u0441\u0442\u0443\u043f \u0430\u043a\u0442\u0438\u0432\u0438\u0440\u043e\u0432\u0430\u043d" in msg.lower()
        assert "link" in msg
