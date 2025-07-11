import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from bot import notify_expirations_loop

@pytest.mark.asyncio
async def test_notify_expirations_loop_selects_all_keys():
    conn = AsyncMock()
    conn.__aenter__.return_value = conn
    conn.__aexit__.return_value = AsyncMock()
    cursor = AsyncMock()
    conn.execute.return_value = cursor
    cursor.fetchall.return_value = []

    with patch("bot.get_connection", return_value=conn), \
         patch("bot.bot.send_message", new=AsyncMock()), \
         patch("bot.asyncio.sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
        with pytest.raises(asyncio.CancelledError):
            await notify_expirations_loop(interval=0)

    query = conn.execute.await_args.args[0].lower()
    assert "is_trial" not in query
