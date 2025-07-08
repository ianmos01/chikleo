"""Shared pytest fixtures for tests."""

import asyncio

import pytest


@pytest.fixture
def task_spy():
    """Return a task list and a replacement for ``asyncio.create_task``."""
    tasks = []
    orig_create_task = asyncio.create_task

    def fake_create_task(coro):
        task = orig_create_task(coro)
        tasks.append(task)
        return task

    return tasks, fake_create_task
