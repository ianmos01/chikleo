import os
import sqlite3
from contextlib import closing

DB_PATH = os.getenv("DB_PATH", "vpn.sqlite")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with closing(get_connection()) as conn:
        conn.execute(
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
        conn.commit()


def add_key(
    user_id: int,
    key_id: int,
    access_url: str,
    expires_at: int,
    is_trial: bool,
) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO vpn_access (user_id, is_trial, key_id,"
            " access_url, expires_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, int(is_trial), key_id, access_url, expires_at),
        )
        conn.commit()


def clear_key(user_id: int, is_trial: bool) -> None:
    with closing(get_connection()) as conn:
        conn.execute(
            "UPDATE vpn_access SET key_id=NULL, access_url=NULL, "
            "expires_at=NULL WHERE user_id=? AND is_trial=?",
            (user_id, int(is_trial)),
        )
        conn.commit()


def get_active_key(user_id: int):
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT access_url, expires_at, is_trial FROM vpn_access "
            "WHERE user_id=? AND key_id IS NOT NULL",
            (user_id,),
        ).fetchone()
        return row


def has_used_trial(user_id: int) -> bool:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT 1 FROM vpn_access WHERE user_id=? AND is_trial=1",
            (user_id,),
        ).fetchone()
        return row is not None
