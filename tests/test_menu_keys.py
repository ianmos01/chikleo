import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import menu_keys


@pytest.mark.asyncio
async def test_menu_keys_shows_expiration():
    message = SimpleNamespace(from_user=SimpleNamespace(id=1), chat=SimpleNamespace(id=2))
    exp = 123
    date_str = time.strftime("%d.%m.%Y", time.localtime(exp))
    with patch("bot.get_active_key", new=AsyncMock(return_value=("url", exp, False))), \
         patch("bot.send_temporary", new=AsyncMock()) as send_mock, \
         patch("bot.time.time", return_value=0):
        await menu_keys(message)
   assert len(send_mock.await_args_list) == 2
    first_text = send_mock.await_args_list[0].args[2]
    second_text = send_mock.await_args_list[1].args[2]
    assert date_str in first_text
    assert "url" == second_text

