import os
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "vpn.sqlite")


def get_connection():
    return aiosqlite.connect(DB_PATH)


async def init_db() -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vpn_access (
                user_id INTEGER,
                is_trial INTEGER,
                key_id INTEGER,
                access_url TEXT,
                expires_at INTEGER,
                PRIMARY KEY (user_id, is_trial)
            )
            """
        )
        await conn.commit()


async def add_key(
    user_id: int,
    key_id: int,
    access_url: str,
    expires_at: int,
    is_trial: bool,
) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO vpn_access (user_id, is_trial, key_id,"
            " access_url, expires_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, int(is_trial), key_id, access_url, expires_at),
        )
        await conn.commit()


async def clear_key(user_id: int, is_trial: bool) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE vpn_access SET key_id=NULL, access_url=NULL, "
            "expires_at=NULL WHERE user_id=? AND is_trial=?",
            (user_id, int(is_trial)),
        )
        await conn.commit()


async def get_active_key(user_id: int):
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT access_url, expires_at, is_trial FROM vpn_access "
            "WHERE user_id=? AND key_id IS NOT NULL",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row


async def has_used_trial(user_id: int) -> bool:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM vpn_access WHERE user_id=? AND is_trial=1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row is not None
