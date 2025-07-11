import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("BOT_TOKEN", "TEST")

import bot


@pytest.mark.asyncio
@pytest.mark.parametrize("state_name", ["waiting_tariff", "waiting_method"])
async def test_restart_buy_calls_menu_buy(state_name):
    message = SimpleNamespace(text="\U0001f6d2 Купить VPN | \U0001f4c5 Продлить")
    state = SimpleNamespace(clear=AsyncMock())
    with patch("bot.menu_buy", new=AsyncMock()) as menu_mock:
        await bot.restart_buy(message, state)
        state.clear.assert_awaited()
        menu_mock.assert_awaited_with(message, state)
