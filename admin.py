from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import Message

from db import get_all_users, get_users_stats

import time

ADMINS = [124508057]


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


router = Router()


@router.message(Command("users"))
async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("\u26d4\ufe0f \u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430.")
        return
    total, active, trial, paid, expired = await get_users_stats()
    text = (
        f"\u0412\u0441\u0435\u0433\u043e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439: {total}\n"
        f"\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0445: {active}\n"
        f"\u0421 \u043f\u0440\u043e\u0431\u043d\u044b\u043c \u0434\u043e\u0441\u0442\u0443\u043f\u043e\u043c: {trial}\n"
        f"\u0421 \u043f\u043b\u0430\u0442\u043d\u043e\u0439 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u043e\u0439: {paid}\n"
        f"\u0417\u0430\u0432\u0435\u0440\u0448\u0438\u0432\u0448\u0438\u0445 \u043f\u043e\u0434\u043f\u0438\u0441\u043a\u0443: {expired}"
    )
    await message.answer(text)


@router.message(Command("userlist"))
async def cmd_userlist(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("\u26d4\ufe0f \u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430.")
        return
    parts = message.text.split(maxsplit=1)
    page = 1
    if len(parts) > 1:
        try:
            page = max(1, int(parts[1]))
        except ValueError:
            page = 1
    limit = 20
    offset = (page - 1) * limit
    rows = await get_all_users(offset=offset, limit=limit)
    lines = []
    for user_id, username, is_trial, is_paid, created_at, expires_at in rows:
        if expires_at and expires_at < int(time.time()):
            status = "\u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d"
        elif is_paid:
            status = "\u043f\u043b\u0430\u0442\u043d\u044b\u0439"
        elif is_trial:
            status = "\u043f\u0440\u043e\u0431\u043d\u044b\u0439"
        else:
            status = "\u043d\u0435\u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439"
        created = time.strftime("%Y-%m-%d", time.localtime(created_at)) if created_at else "-"
        expires = time.strftime("%Y-%m-%d", time.localtime(expires_at)) if expires_at else "-"
        username = f"@{username}" if username else "-"
        block = (
            f"\U0001f464 {username} | ID: {user_id}\n"
            f"\U0001f511 \u0421\u0442\u0430\u0442\u0443\u0441: {status}\n"
            f"\U0001f4c5 \u0410\u043a\u0442\u0438\u0432\u0430\u0446\u0438\u044f: {created}\n"
            f"\u23f3 \u0418\u0441\u0442\u0435\u043a\u0430\u0435\u0442: {expires}"
        )
        lines.append(block)
    if not lines:
        await message.answer("\u041d\u0435\u0442 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439.")
    else:
        await message.answer("\n\n".join(lines))


__all__ = ["router"]
