"""Tests that missing ``BOT_TOKEN`` raises an error on import."""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # noqa: E402


def test_missing_token_raises_error(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    orig_mod = sys.modules.pop("bot", None)
    with pytest.raises(RuntimeError, match="BOT_TOKEN not configured"):
        importlib.import_module("bot")
    if orig_mod is not None:
        sys.modules["bot"] = orig_mod
