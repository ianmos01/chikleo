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
    send_mock.assert_awaited()
    text = send_mock.await_args.args[2]
    assert "url" in text
    assert date_str in text

