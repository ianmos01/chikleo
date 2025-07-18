import os
import time
import aiosqlite

DB_PATH = os.getenv("DB_PATH", "vpn.sqlite")


def get_connection():
    dirpath = os.path.dirname(DB_PATH)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
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
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                is_trial INTEGER,
                is_paid INTEGER,
                created_at INTEGER,
                expires_at INTEGER
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                user_id INTEGER PRIMARY KEY,
                referrer_id INTEGER
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                user_id INTEGER PRIMARY KEY,
                last_notified_at INTEGER
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
        now_ts = int(time.time())
        await conn.execute(
            """
            INSERT INTO users (user_id, is_trial, is_paid, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                is_trial=excluded.is_trial,
                is_paid=excluded.is_paid,
                created_at=COALESCE(users.created_at, excluded.created_at),
                expires_at=excluded.expires_at
            """,
            (user_id, int(is_trial), int(not is_trial), now_ts, expires_at),
        )
        await conn.commit()


async def clear_key(user_id: int, is_trial: bool) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE vpn_access SET key_id=NULL, access_url=NULL, "
            "expires_at=NULL WHERE user_id=? AND is_trial=?",
            (user_id, int(is_trial)),
        )
        if is_trial:
            await conn.execute(
                "UPDATE users SET is_trial=0, expires_at=NULL WHERE user_id=?",
                (user_id,),
            )
        else:
            await conn.execute(
                "UPDATE users SET is_paid=0, expires_at=NULL WHERE user_id=?",
                (user_id,),
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


async def has_vpn_history(user_id: int) -> bool:
    """Return True if the user ever had VPN access."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM vpn_access WHERE user_id=?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row is not None


async def record_referral(user_id: int, referrer_id: int) -> bool:
    """Save referrer relationship. Return ``True`` if stored."""
    if user_id == referrer_id:
        return False
    if await has_vpn_history(user_id):
        return False
    async with get_connection() as conn:
        try:
            await conn.execute(
                "INSERT INTO referrals (user_id, referrer_id) VALUES (?, ?)",
                (user_id, referrer_id),
            )
            await conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
async def get_key_info(user_id: int):
    """Return key_id, access_url, expires_at, is_trial for the user if any."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT key_id, access_url, expires_at, is_trial FROM vpn_access "
            "WHERE user_id=? AND key_id IS NOT NULL",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row


async def update_expiration(user_id: int, is_trial: bool, expires_at: int) -> None:
    """Update the expiration time for the user's key."""
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE vpn_access SET expires_at=? WHERE user_id=? AND is_trial=?",
            (expires_at, user_id, int(is_trial)),
        )
        if is_trial:
            await conn.execute(
                "UPDATE users SET expires_at=?, is_trial=1, is_paid=0 WHERE user_id=?",
                (expires_at, user_id),
            )
        else:
            await conn.execute(
                "UPDATE users SET expires_at=?, is_trial=0, is_paid=1 WHERE user_id=?",
                (expires_at, user_id),
            )
        await conn.commit()


async def get_last_notification(user_id: int) -> int | None:
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT last_notified_at FROM notifications WHERE user_id=?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        return None


async def set_last_notification(user_id: int, ts: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO notifications (user_id, last_notified_at) VALUES (?, ?)",
            (user_id, ts),
        )
        await conn.commit()


async def save_user(user_id: int, username: str | None) -> None:
    """Ensure the user record exists and update the username."""
    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username, is_trial, is_paid, created_at, expires_at)
            VALUES (?, ?, 0, 0, NULL, NULL)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
            """,
            (user_id, username),
        )
        await conn.commit()


async def get_all_users(offset: int = 0, limit: int = 20):
    """Return a list of users with basic subscription info."""
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT user_id, username, is_trial, is_paid, created_at, expires_at "
            "FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return rows


async def get_users_stats():
    """Return aggregate statistics about users."""
    now = int(time.time())
    async with get_connection() as conn:
        cursor = await conn.execute(
            "SELECT "
            "COUNT(*) as total, "
            "COALESCE(SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END), 0) as active, "
            "COALESCE(SUM(CASE WHEN is_trial=1 AND expires_at > ? THEN 1 ELSE 0 END), 0) as trial, "
            "COALESCE(SUM(CASE WHEN is_paid=1 AND expires_at > ? THEN 1 ELSE 0 END), 0) as paid, "
            "COALESCE(SUM(CASE WHEN expires_at <= ? THEN 1 ELSE 0 END), 0) as expired "
            "FROM users",
            (now, now, now, now),
        )
        row = await cursor.fetchone()
        if row:
            return row
        return (0, 0, 0, 0, 0)
