from __future__ import annotations

import datetime
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from db import get_connection

# Telegram user IDs allowed to use admin commands
ADMIN_IDS = [124508057]


# Router with admin handlers
admin_router = Router()
# Backwards compatibility for existing imports
router = admin_router


async def _is_admin(message: Message) -> bool:
    if message.from_user and message.from_user.id in ADMIN_IDS:
        return True
    await message.answer("\u26d4\ufe0f \u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430.")
    return False


@admin_router.message(Command("users"))
async def cmd_users(message: Message) -> None:
    """Show list of all registered users."""
    if not await _is_admin(message):
        return
    async with get_connection() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, registered_at TEXT)"
        )
        cursor = await conn.execute(
            "SELECT user_id, registered_at FROM users ORDER BY registered_at"
        )
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439 \u043d\u0435\u0442.")
        return
    lines = [f"ID: {uid} | \u0417\u0430\u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0438\u0440\u043e\u0432\u0430\u043d: {reg}" for uid, reg in rows]
    await message.answer("\n".join(lines))


@admin_router.message(Command("active_keys"))
async def cmd_active_keys(message: Message) -> None:
    """Show list of active VPN keys."""
    if not await _is_admin(message):
        return
    async with get_connection() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, vpn_id TEXT, expires_at TEXT)"
        )
        cursor = await conn.execute(
            "SELECT user_id, vpn_id, expires_at FROM keys WHERE expires_at > CURRENT_TIMESTAMP"
        )
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u043a\u043b\u044e\u0447\u0438 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b.")
        return
    lines = [f"ID: {uid} | VPN: {vpn} | \u0434\u043e: {exp}" for uid, vpn, exp in rows]
    await message.answer("\n".join(lines))


@admin_router.message(Command("expired_keys"))
async def cmd_expired_keys(message: Message) -> None:
    """Show users with expired VPN keys."""
    if not await _is_admin(message):
        return
    async with get_connection() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, vpn_id TEXT, expires_at TEXT)"
        )
        cursor = await conn.execute(
            "SELECT user_id, vpn_id, expires_at FROM keys WHERE expires_at <= CURRENT_TIMESTAMP"
        )
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("\u041f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d\u043d\u044b\u0445 \u043a\u043b\u044e\u0447\u0435\u0439 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
        return
    lines = [f"ID: {uid} | VPN: {vpn} | {exp}" for uid, vpn, exp in rows]
    await message.answer("\n".join(lines))


@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot) -> None:
    """Broadcast a message to all users."""
    if not await _is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435: /broadcast <\u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435>")
        return
    text = parts[1]
    async with get_connection() as conn:
        cursor = await conn.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
    count = 0
    for (uid,) in rows:
        try:
            await bot.send_message(uid, text)
            count += 1
        except Exception:
            pass
    await message.answer(f"\u041e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e {count} \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0439.")


@admin_router.message(Command("add_user"))
async def cmd_add_user(message: Message) -> None:
    """Add a user to the database manually."""
    if not await _is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435: /add_user <user_id>")
        return
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 ID")
        return
    async with get_connection() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, registered_at TEXT)"
        )
        cursor = await conn.execute(
            "SELECT 1 FROM users WHERE user_id=?",
            (user_id,),
        )
        exists = await cursor.fetchone()
        if exists:
            await message.answer("\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0443\u0436\u0435 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442.")
            return
        now = datetime.datetime.utcnow().isoformat()
        await conn.execute(
            "INSERT INTO users (user_id, registered_at) VALUES (?, ?)",
            (user_id, now),
        )
        await conn.commit()
    await message.answer("\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d.")


@admin_router.message(Command("del_user"))
async def cmd_del_user(message: Message) -> None:
    """Remove a user from the database."""
    if not await _is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435: /del_user <user_id>")
        return
    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 ID")
        return
    async with get_connection() as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, registered_at TEXT)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS keys (user_id INTEGER, vpn_id TEXT, expires_at TEXT)"
        )
        cursor = await conn.execute(
            "SELECT 1 FROM users WHERE user_id=?",
            (user_id,),
        )
        exists = await cursor.fetchone()
        if not exists:
            await message.answer("\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d.")
            return
        await conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        await conn.execute("DELETE FROM keys WHERE user_id=?", (user_id,))
        await conn.commit()
    await message.answer("\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c \u0443\u0434\u0430\u043b\u0451\u043d.")


@admin_router.message(Command("wipe_db"))
async def cmd_wipe_db(message: Message) -> None:
    """Delete all data from the database."""
    if not await _is_admin(message):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or parts[1].lower() != "confirm":
        await message.answer(
            "\u042d\u0442\u043e \u0443\u0434\u0430\u043b\u0438\u0442 \u0432\u0441\u0435 \u0434\u0430\u043d\u043d\u044b\u0435. \u0414\u043b\u044f \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f \u0432\u0432\u0435\u0434\u0438\u0442\u0435 /wipe_db confirm"
        )
        return
    async with get_connection() as conn:
        await conn.execute("DELETE FROM users")
        await conn.execute("DELETE FROM keys")
        await conn.commit()
    await message.answer("\u0411\u0430\u0437\u0430 \u0434\u0430\u043d\u043d\u044b\u0445 \u043e\u0447\u0438\u0449\u0435\u043d\u0430.")


__all__ = ["admin_router", "router"]
