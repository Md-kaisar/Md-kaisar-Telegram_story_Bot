"""
SQLite persistence layer for MuseBot.
Handles users, preferences, creation history, and favorites.
Uses a single sync sqlite3 connection guarded by a lock (fine for a small/medium bot);
swap for asyncpg/PostgreSQL later without changing the calling code much.
"""
import sqlite3
import threading
import time
from contextlib import contextmanager

from config import DB_PATH, DEFAULT_LANGUAGE, DEFAULT_STYLE

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_conn = _connect()


@contextmanager
def _cursor():
    with _lock:
        cur = _conn.cursor()
        try:
            yield cur
            _conn.commit()
        finally:
            cur.close()


def init_db():
    with _cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                language TEXT DEFAULT 'en',
                style TEXT DEFAULT 'Nature',
                created_at INTEGER,
                last_seen INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                kind TEXT,
                title TEXT,
                content TEXT,
                mood TEXT,
                image_file_id TEXT,
                created_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                history_id INTEGER,
                created_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(history_id) REFERENCES history(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                day TEXT,
                count INTEGER,
                UNIQUE(user_id, day)
            )
        """)


# ---------- Users ----------

def upsert_user(user_id: int, username: str | None) -> bool:
    """Returns True if this is a brand-new user (first time seen), False if returning."""
    now = int(time.time())
    with _cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE users SET username=?, last_seen=? WHERE user_id=?",
                        (username, now, user_id))
            return False
        cur.execute(
            "INSERT INTO users (user_id, username, language, style, created_at, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, DEFAULT_LANGUAGE, DEFAULT_STYLE, now, now),
        )
        return True


def get_user(user_id: int) -> sqlite3.Row | None:
    with _cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return cur.fetchone()


def set_language(user_id: int, language: str):
    with _cursor() as cur:
        cur.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))


def set_style(user_id: int, style: str):
    with _cursor() as cur:
        cur.execute("UPDATE users SET style=? WHERE user_id=?", (style, user_id))


# ---------- History / Favorites ----------

def add_history(user_id: int, kind: str, title: str, content: str,
                mood: str | None = None, image_file_id: str | None = None) -> int:
    now = int(time.time())
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO history (user_id, kind, title, content, mood, image_file_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, kind, title, content, mood, image_file_id, now),
        )
        return cur.lastrowid


def get_history(user_id: int, limit: int = 10):
    with _cursor() as cur:
        cur.execute(
            "SELECT * FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return cur.fetchall()


def get_history_item(history_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM history WHERE id=?", (history_id,))
        return cur.fetchone()


def add_favorite(user_id: int, history_id: int) -> bool:
    now = int(time.time())
    with _cursor() as cur:
        cur.execute("SELECT id FROM favorites WHERE user_id=? AND history_id=?",
                    (user_id, history_id))
        if cur.fetchone():
            return False
        cur.execute(
            "INSERT INTO favorites (user_id, history_id, created_at) VALUES (?, ?, ?)",
            (user_id, history_id, now),
        )
        return True


def get_favorites(user_id: int, limit: int = 20):
    with _cursor() as cur:
        cur.execute(
            """SELECT h.* FROM favorites f
               JOIN history h ON h.id = f.history_id
               WHERE f.user_id=? ORDER BY f.created_at DESC LIMIT ?""",
            (user_id, limit),
        )
        return cur.fetchall()


def get_stats(user_id: int) -> dict:
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM history WHERE user_id=?", (user_id,))
        total = cur.fetchone()["c"]
        cur.execute(
            "SELECT kind, COUNT(*) AS c FROM history WHERE user_id=? GROUP BY kind",
            (user_id,),
        )
        by_kind = {r["kind"]: r["c"] for r in cur.fetchall()}
        cur.execute(
            """SELECT mood, COUNT(*) AS c FROM history
               WHERE user_id=? AND mood IS NOT NULL
               GROUP BY mood ORDER BY c DESC LIMIT 1""",
            (user_id,),
        )
        top_mood_row = cur.fetchone()
        top_mood = top_mood_row["mood"] if top_mood_row else None
        cur.execute("SELECT COUNT(*) AS c FROM favorites WHERE user_id=?", (user_id,))
        favs = cur.fetchone()["c"]
        return {"total": total, "by_kind": by_kind, "top_mood": top_mood, "favorites": favs}


# ---------- Usage / rate limiting ----------

def get_usage(user_id: int, day: str) -> int:
    with _cursor() as cur:
        cur.execute("SELECT count FROM usage_log WHERE user_id=? AND day=?", (user_id, day))
        row = cur.fetchone()
        return row["count"] if row else 0


def bump_usage_by(user_id: int, day: str, amount: int) -> int:
    with _cursor() as cur:
        cur.execute("SELECT count FROM usage_log WHERE user_id=? AND day=?", (user_id, day))
        row = cur.fetchone()
        if row:
            new_count = row["count"] + amount
            cur.execute(
                "UPDATE usage_log SET count=? WHERE user_id=? AND day=?",
                (new_count, user_id, day),
            )
            return new_count
        cur.execute(
            "INSERT INTO usage_log (user_id, day, count) VALUES (?, ?, ?)",
            (user_id, day, amount),
        )
        return amount


def bump_usage(user_id: int, day: str) -> int:
    return bump_usage_by(user_id, day, 1)
