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
    button_url = kb.inline_keyboard[0][0].url
    assert button_url.startswith("https://t.me/share/url")
    assert "url=https%3A%2F%2Ft.me%2FVPNos_bot%3Fstart%3Dref4" in button_url
    assert kb.inline_keyboard[1][0].callback_data == "main_menu"


@pytest.mark.asyncio
async def test_grant_referral_bonus_creates_key():
    with patch("bot.get_key_info", new=AsyncMock(return_value=None)), patch(
        "bot.create_outline_key", new=AsyncMock(return_value={"id": 8, "accessUrl": "url"})
    ) as create_mock, patch(
        "bot.add_key", new=AsyncMock()
    ) as add_key_mock, patch(
        "bot.schedule_key_deletion"
    ) as sched_mock, patch(
        "bot.bot.send_message", new=AsyncMock()) as send_mock:
        await grant_referral_bonus(4)
        create_mock.assert_awaited_with(label="vpn_4")
        add_key_mock.assert_awaited()
        sched_mock.assert_called_with(8, delay=REFERRAL_BONUS_DAYS * 24 * 60 * 60, user_id=4, is_trial=False)
        send_mock.assert_awaited()


@pytest.mark.asyncio
async def test_grant_referral_bonus_extends_key():
    now = 100
    record = (11, "url", 200, 0)
    with patch("bot.get_key_info", new=AsyncMock(return_value=record)), patch(
        "bot.update_expiration", new=AsyncMock()
    ) as upd_mock, patch(
        "bot.schedule_key_deletion"
    ) as sched_mock, patch(
        "bot.bot.send_message", new=AsyncMock()) as send_mock, patch(
        "bot.time.time", return_value=now):
        await grant_referral_bonus(5)
        new_exp = 200 + REFERRAL_BONUS_DAYS * 24 * 60 * 60
        upd_mock.assert_awaited_with(5, False, new_exp)
        sched_mock.assert_called_with(11, delay=new_exp - now, user_id=5, is_trial=False)
        send_mock.assert_awaited()
