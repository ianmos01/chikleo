"""Tests for Outline manager integration."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402
os.environ.setdefault("BOT_TOKEN", "TEST")

from bot import create_outline_key  # noqa: E402


@pytest.mark.asyncio
async def test_create_outline_key_calls_manager():
    os.environ["OUTLINE_API_URL"] = "https://example.com/api"
    with patch("bot.OUTLINE_API_URL", "https://example.com/api"), patch(
        "bot.Manager"
    ) as manager_cls:
        manager = manager_cls.return_value
        manager.new.return_value = {"accessUrl": "url", "id": 11}
        res = await create_outline_key(label="vpn_7")
        manager_cls.assert_called_with(
            apiurl="https://example.com/api", apicrt=""
        )
        manager.new.assert_called_with("vpn_7")
        manager.rename.assert_called_with(11, "vpn_7")
        assert res == {"accessUrl": "url", "id": 11}
